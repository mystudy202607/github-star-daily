#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub 每日高星精选：候选池刷新、每日抽选与历史去重。"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POOL_FILE = os.path.join(BASE_DIR, "pool.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
BUILD_PAGE = os.path.join(BASE_DIR, "build_page.py")
LOG_FILE = os.path.join(BASE_DIR, "update.log")

CN_TZ = timezone(timedelta(hours=8))
SEARCH_URL = "https://api.github.com/search/repositories"
PER_PAGE = 100
MAX_PAGES_PER_BAND = 10
PICKS_PER_DAY = 10
REFRESH_AFTER_DAYS = 7
REFRESH_IF_UNSEEN_BELOW = 120
REQUEST_DELAY = 2.2
MAX_ATTEMPTS = 3

# (lower, upper) star 区间；None 表示上不封顶
STAR_BANDS = [
    (20000, None),
    (5000, 20000),
    (2000, 5000),
    (800, 2000),
]

_URL_RE = re.compile(r"(?:https?|ftp)://[^\s]+|www\.[^\s]+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")
_PLACEHOLDER_RE = re.compile(
    r"\b(tbd|todo|coming soon|under construction|lorem ipsum|your project( here)?|placeholder)\b",
    re.IGNORECASE,
)
_NOISE_STARTS = ("[", "**", "#", "`", "* ", "- ", "!", "@", ">", "<", "|", "```", "![")


def log(msg):
    line = "[%s] %s" % (datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def github_token():
    for name in ("STAR_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        "缺少 GitHub Token：请在本地执行 $env:STAR_TOKEN=(gh auth token)，"
        "或在工作流环境传入 secrets.GITHUB_TOKEN。"
    )


def api_get(url, token):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "github-star-daily")
    if token:
        req.add_header("Authorization", "Bearer %s" % token)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if exc.code in (403, 429):
                retry_after = exc.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else 15.0 * attempt
                log("GitHub 限流（HTTP %s），等待 %.0f 秒后重试..." % (exc.code, wait))
                time.sleep(min(wait, 90.0))
                continue
            if exc.code == 401:
                raise RuntimeError("GitHub Token 无效或没有权限。")
            if exc.code == 422:
                raise RuntimeError("搜索语法错误：%s" % body[:200])
            raise RuntimeError("GitHub API HTTP %s: %s" % (exc.code, body[:300]))
        except urllib.error.URLError as exc:
            log("网络错误：%s，%d 秒后重试..." % (exc.reason, 10 * attempt))
            time.sleep(10 * attempt)
    raise RuntimeError("请求多次失败：%s" % url)


def make_quote(raw):
    """判断简介是否为可用“金句”，是则返回清洗后的文本，否则返回 None。

    金句标准：无链接/占位符/符号噪音、长度 10–160 字符、以句号/叹号/问号
    完整收尾；多句简介取第一句完整句。
    """
    if not raw or not isinstance(raw, str):
        return None
    text = _URL_RE.sub(" ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" \t\r\n-–—_:;，。；：*#`~'\"()[]{}<>")
    if len(text) < 10 or len(text) > 160:
        return None
    lower = text.lower()
    if _PLACEHOLDER_RE.search(lower) and len(text) < 80:
        return None
    for noise in _NOISE_STARTS:
        if lower.startswith(noise) or text.startswith(noise):
            return None
    sentences = _SENT_SPLIT_RE.split(text)
    for sentence in sentences:
        sentence = sentence.strip()
        if 10 <= len(sentence) <= 160:
            return sentence
    if not text[-1:] in ".!?。！？":
        return None
    return text if 10 <= len(text) <= 160 else None


def normalize_repo(item):
    owner = item.get("owner") or {}
    return {
        "full_name": item.get("full_name") or "",
        "html_url": item.get("html_url") or "",
        "owner": owner.get("login") or "",
        "name": item.get("name") or "",
        "description": item.get("description"),
        "stars": int(item.get("stargazers_count") or 0),
        "language": item.get("language"),
    }


def refresh_pool(token):
    """跨 Star 区间抓取高星项目并合并进候选池。"""
    log("开始刷新候选池...")
    old = load_json(POOL_FILE, {"repos": []})
    merged = {
        repo["full_name"]: repo
        for repo in old.get("repos", [])
        if repo.get("full_name")
    }

    for low, high in STAR_BANDS:
        qualifier = "stars:>%d" % low if high is None else "stars:%d..%d" % (low, high)
        query = "%s fork:false archived:false" % qualifier
        for page_no in range(1, MAX_PAGES_PER_BAND + 1):
            time.sleep(REQUEST_DELAY)
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": PER_PAGE,
                    "page": page_no,
                }
            )
            payload = api_get(SEARCH_URL + "?" + params, token)
            items = payload.get("items") or []
            if not items:
                break
            for item in items:
                if item.get("fork") or item.get("archived"):
                    continue
                full_name = item.get("full_name")
                if full_name:
                    merged[full_name] = normalize_repo(item)
            if len(items) < PER_PAGE:
                break
        log("区间 %s：候选池累计 %d 个" % (qualifier, len(merged)))

    repos = sorted(merged.values(), key=lambda r: (-r["stars"], r["full_name"]))
    pool = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "GitHub Search API (stars, fork:false, archived:false)",
        "count": len(repos),
        "repos": repos,
    }
    save_json(POOL_FILE, pool)
    log("候选池刷新完成：%d 个唯一项目" % len(repos))
    return pool


def load_pool():
    return load_json(POOL_FILE, {"generated_at": None, "repos": []})


def load_history():
    data = load_json(HISTORY_FILE, {"entries": []})
    if not isinstance(data.get("entries"), list):
        data["entries"] = []
    return data


def seen_names(history):
    seen = set()
    for entry in history.get("entries", []):
        for name in entry.get("repos", []) or []:
            seen.add(name)
    return seen


def pool_needs_refresh(pool, seen, force=False):
    if force:
        return True
    generated_at = pool.get("generated_at")
    if not generated_at:
        return True
    try:
        created = datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        age_days = (datetime.now(timezone.utc) - created).total_seconds() / 86400.0
    except (TypeError, ValueError):
        return True
    if age_days >= REFRESH_AFTER_DAYS:
        return True
    remaining = [r for r in pool.get("repos", []) if r.get("full_name") not in seen]
    return len(remaining) < REFRESH_IF_UNSEEN_BELOW


def today_cn():
    return datetime.now(CN_TZ).strftime("%Y-%m-%d")


def cmd_refresh(args):
    token = github_token()
    refresh_pool(token)


def cmd_run(args):
    history = load_history()
    seen = seen_names(history)
    pool = load_pool()

    if pool_needs_refresh(pool, seen, force=args.force_refresh):
        token = github_token()
        pool = refresh_pool(token)

    unseen = [r for r in pool.get("repos", []) if r.get("full_name") not in seen]
    if len(unseen) < PICKS_PER_DAY:
        token = github_token()
        log("候选不足 %d 条，强制扩容一次..." % PICKS_PER_DAY)
        pool = refresh_pool(token)
        seen = seen_names(history)
        unseen = [r for r in pool.get("repos", []) if r.get("full_name") not in seen]
    if len(unseen) < PICKS_PER_DAY:
        raise RuntimeError(
            "可用候选仅剩 %d 条，无法满足每天 %d 条；已保留旧数据不重置历史。"
            % (len(unseen), PICKS_PER_DAY)
        )

    date = args.date or today_cn()
    chosen = random.SystemRandom().sample(unseen, PICKS_PER_DAY)
    chosen.sort(key=lambda r: r["stars"], reverse=True)
    log(
        "抽选 %s：%s"
        % (date, ", ".join(repo["full_name"] for repo in chosen))
    )

    if args.dry_run:
        print("dry-run 完成，未写入任何文件。")
        return

    items = []
    for rank, repo in enumerate(chosen, 1):
        quote = make_quote(repo.get("description"))
        items.append(
            {
                "rank": rank,
                "full_name": repo["full_name"],
                "name": repo.get("name"),
                "owner": repo.get("owner"),
                "html_url": repo.get("html_url"),
                "description": repo.get("description"),
                "stars": repo.get("stars", 0),
                "language": repo.get("language"),
                "has_quote": bool(quote),
                "quote": quote,
            }
        )

    history["entries"] = [
        entry for entry in history.get("entries", []) if entry.get("date") != date
    ]
    history["entries"].append(
        {"date": date, "repos": [item["full_name"] for item in items]}
    )
    history["entries"].sort(key=lambda entry: entry.get("date", ""))
    series = len(history["entries"])

    data = {
        "date": date,
        "series": series,
        "total_shown": series * PICKS_PER_DAY,
        "generated_at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
        "timezone": "Asia/Shanghai",
        "items": items,
    }
    save_json(DATA_FILE, data)
    save_json(HISTORY_FILE, history)
    log("已保存 data.json（第 %d 期，累计 %d 条）" % (series, data["total_shown"]))

    subprocess.run([sys.executable, BUILD_PAGE], cwd=BASE_DIR, check=True)
    log("index.html 已重新生成")


def main():
    parser = argparse.ArgumentParser(description="GitHub 每日高星精选")
    subparsers = parser.add_subparsers(dest="command")

    parser_refresh = subparsers.add_parser(
        "refresh", help="强制刷新候选池（跨 Star 区间抓取并合并）"
    )
    parser_refresh.set_defaults(func=cmd_refresh)

    parser_run = subparsers.add_parser("run", help="抽选今日 10 条并生成网页")
    parser_run.add_argument("--date", help="指定日期 YYYY-MM-DD（默认今天北京时间）")
    parser_run.add_argument("--dry-run", action="store_true", help="只预览不写文件")
    parser_run.add_argument("--force-refresh", action="store_true", help="先强制刷新候选池")
    parser_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
