#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 data.json，生成纯静态 index.html。"""

import html
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Shell": "#89e051",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Jupyter Notebook": "#DA5B0B",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Objective-C": "#438eff",
    "Lua": "#000080",
    "R": "#198CE7",
    "Scala": "#c22d40",
    "Perl": "#0298c3",
    "Haskell": "#5e5086",
    "Elixir": "#6e4a7e",
    "Clojure": "#db5855",
    "Zig": "#ec915c",
    "Solidity": "#AA6746",
}


def esc(text):
    return html.escape(str(text if text is not None else ""), quote=True)


def fmt_stars(count):
    if count >= 1_000_000:
        return "%.1fM" % (count / 1_000_000)
    if count >= 1_000:
        return "%.1fk" % (count / 1_000)
    return str(count)


def lang_color(language):
    return LANG_COLORS.get(language or "", "#8b949e")


def format_date(date_text):
    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return date_text
    return "%d年%d月%d日 %s" % (dt.year, dt.month, dt.day, WEEKDAYS[dt.weekday()])


def render_cards(items):
    cards = []
    for item in items:
        has_quote = bool(item.get("has_quote") and item.get("quote"))
        rank = "%02d" % int(item.get("rank", 0))
        full_name = esc(item.get("full_name") or "")
        owner = esc(item.get("owner") or "")
        repo_url = esc(item.get("html_url") or "#")
        stars = fmt_stars(int(item.get("stars") or 0))
        language = item.get("language")
        color = lang_color(language)
        desc = esc(item.get("description") or "暂无简介")
        quote = esc(item.get("quote") or "")
        lang_html = (
            '<span class="lang"><i class="dot" style="background:%s"></i>%s</span>'
            % (color, esc(language))
            if language
            else '<span class="lang muted">无语言</span>'
        )
        chip = (
            '<span class="quote-chip">\u275d 今日金句</span>' if has_quote else ""
        )
        blockquote = (
            '<blockquote class="quote">\u201c%s\u201d</blockquote>' % quote
            if has_quote
            else ""
        )
        cards.append(
            """
      <article class="card" data-quote="%s">
        <div class="card-head">
          <span class="rank">%s</span>
          <div class="repo">
            <a class="name" href="%s" target="_blank" rel="noopener noreferrer">%s</a>
            <span class="owner">@%s</span>
          </div>
          <div class="head-right">
            %s
            <span class="stars">\u2605 %s</span>
          </div>
        </div>
        <p class="desc">%s</p>
        %s
        <div class="card-foot">
          %s
          <a class="go" href="%s" target="_blank" rel="noopener noreferrer">GitHub \u2197</a>
        </div>
      </article>"""
            % (
                "1" if has_quote else "0",
                rank,
                repo_url,
                full_name,
                owner,
                chip,
                stars,
                desc,
                blockquote,
                lang_html,
                repo_url,
            )
        )
    return "\n".join(cards)


def main():
    if not os.path.exists(DATA_FILE):
        raise SystemExit("缺少 data.json，请先运行 python github_star_daily.py run")
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    items = data.get("items") or []
    quote_count = sum(1 for item in items if item.get("has_quote") and item.get("quote"))
    total = len(items)
    date_text = data.get("date") or ""
    display_date = format_date(date_text)
    series = int(data.get("series") or 1)
    total_shown = int(data.get("total_shown") or series * total)
    generated_at = data.get("generated_at") or ""
    updated_text = generated_at.replace("T", " ")[:16] if generated_at else ""

    cards_html = render_cards(items)
    html_text = PAGE_TEMPLATE.replace("__DATE__", display_date)
    html_text = html_text.replace("__SERIES__", str(series))
    html_text = html_text.replace("__TOTAL_SHOWN__", str(total_shown))
    html_text = html_text.replace("__TOTAL__", str(total))
    html_text = html_text.replace("__QUOTE_COUNT__", str(quote_count))
    html_text = html_text.replace("__CARDS__", cards_html)
    html_text = html_text.replace("__UPDATED__", updated_text)
    html_text = html_text.replace("__SOURCE_LINK__", "https://github.com/mystudy202607/github-star-daily")

    with open(INDEX_FILE, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    print("已生成 index.html：%d 条，其中金句 %d 条" % (total, quote_count))


PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark light">
  <meta name="description" content="每天北京时间 08:00 自动更新的 GitHub 高 Star 项目精选，跨天不重样。">
  <title>GitHub 每日高星精选 · __DATE__</title>
  <style>
    :root {
      --bg: #0d1117;
      --bg-soft: #11161d;
      --card: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --star: #e3b341;
      --green: #3fb950;
      --shadow: 0 12px 30px rgba(1, 4, 9, 0.35);
      --max: 960px;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg: #f6f8fa;
        --bg-soft: #ffffff;
        --card: #ffffff;
        --border: #d0d7de;
        --text: #1f2328;
        --muted: #57606a;
        --accent: #0969da;
        --star: #9a6700;
        --green: #1a7f37;
        --shadow: 0 12px 30px rgba(140, 149, 159, 0.18);
      }
    }
    * { box-sizing: border-box; }
    html { -webkit-text-size-adjust: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      line-height: 1.6;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      z-index: -1;
      background:
        radial-gradient(700px 320px at 15% -5%, rgba(88, 166, 255, 0.13), transparent 60%),
        radial-gradient(700px 300px at 90% 0%, rgba(63, 185, 80, 0.08), transparent 55%),
        var(--bg);
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .wrap { max-width: var(--max); margin: 0 auto; padding: 34px 18px 60px; }
    .hero { text-align: center; margin: 12px 0 28px; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: .6px;
      color: var(--green);
      background: rgba(63, 185, 80, .1);
      border: 1px solid rgba(63, 185, 80, .35);
      padding: 5px 12px;
      border-radius: 999px;
      margin-bottom: 18px;
    }
    .badge .pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .3; } }
    h1 { font-size: clamp(26px, 5vw, 40px); margin: 0 0 8px; letter-spacing: .5px; }
    .subtitle { color: var(--muted); margin: 0 0 22px; font-size: 14px; }
    .controls {
      display: inline-flex;
      gap: 8px;
      background: var(--bg-soft);
      border: 1px solid var(--border);
      padding: 5px;
      border-radius: 12px;
    }
    .controls button {
      appearance: none;
      border: 0;
      background: transparent;
      color: var(--muted);
      font: inherit;
      font-size: 13px;
      padding: 8px 15px;
      border-radius: 8px;
      cursor: pointer;
      transition: background .15s ease, color .15s ease;
    }
    .controls button.active {
      background: var(--accent);
      color: #ffffff;
      font-weight: 600;
    }
    .controls button b {
      font-weight: 700;
      opacity: .85;
      margin-left: 2px;
    }
    .cards { display: grid; gap: 14px; margin-top: 26px; }
    .card {
      display: block;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 20px;
      box-shadow: var(--shadow);
      transition: transform .15s ease, border-color .15s ease;
    }
    .card:hover { border-color: rgba(88, 166, 255, .45); transform: translateY(-1px); }
    .card.hidden { display: none; }
    .card-head { display: flex; align-items: flex-start; gap: 14px; }
    .rank {
      flex: none;
      font-size: 20px;
      font-weight: 800;
      letter-spacing: .5px;
      font-variant-numeric: tabular-nums;
      color: transparent;
      -webkit-text-stroke: 1px var(--accent);
      padding-top: 2px;
    }
    .repo { min-width: 0; flex: 1; }
    .repo .name {
      color: var(--text);
      font-weight: 650;
      font-size: 17px;
      word-break: break-all;
      display: block;
    }
    .repo .owner { color: var(--muted); font-size: 12.5px; }
    .head-right { flex: none; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
    .stars { color: var(--star); font-weight: 700; font-size: 15px; white-space: nowrap; }
    .quote-chip {
      font-size: 11px;
      color: var(--green);
      border: 1px solid rgba(63,185,80,.4);
      background: rgba(63,185,80,.08);
      padding: 2px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }
    .desc {
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 14px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .quote {
      display: none;
      margin: 16px 0 0;
      color: var(--text);
      font-size: 17px;
      line-height: 1.75;
      font-style: normal;
      border-left: 3px solid var(--green);
      padding: 4px 0 4px 14px;
      background: linear-gradient(90deg, rgba(63,185,80,.07), transparent 70%);
      border-radius: 0 8px 8px 0;
    }
    body.quote-mode .desc { display: none; }
    body.quote-mode .quote { display: block; }
    body.quote-mode .quote-chip { display: none; }
    .card-foot {
      margin-top: 13px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      font-size: 13px;
    }
    .lang { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); }
    .lang .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
    .lang.muted { font-style: italic; }
    .go { font-weight: 600; font-size: 13px; white-space: nowrap; }
    .tip { text-align: center; color: var(--muted); font-size: 13px; margin: 20px 0 0; min-height: 1.4em; }
    footer {
      margin-top: 42px;
      border-top: 1px solid var(--border);
      padding-top: 18px;
      color: var(--muted);
      font-size: 12.5px;
      text-align: center;
    }
    footer p { margin: 4px 0; }
    footer a { color: var(--muted); text-decoration: underline; }
    @media (max-width: 560px) {
      .wrap { padding: 22px 12px 44px; }
      .card { padding: 15px 15px; }
      .card-head { gap: 10px; }
      .rank { font-size: 17px; }
      .repo .name { font-size: 15.5px; }
      .head-right .quote-chip { display: none; }
      .controls button { padding: 7px 11px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <div class="badge"><span class="pulse"></span>每天 08:00 自动更新</div>
      <h1>GitHub 每日高星精选</h1>
      <p class="subtitle">__DATE__ · 第 __SERIES__ 期 · 累计展示 __TOTAL_SHOWN__ 个项目 · 全部与历史不重样</p>
      <div class="controls" role="group" aria-label="视图筛选">
        <button id="btnAll" class="active" type="button" aria-pressed="true">全部项目 <b>__TOTAL__</b></button>
        <button id="btnQuote" type="button" aria-pressed="false">今日金句 <b>__QUOTE_COUNT__</b></button>
      </div>
    </header>
    <main class="cards" id="cards">
__CARDS__
    </main>
    <p class="tip" id="tip"></p>
    <footer>
      <p>数据来源：GitHub 官方 Search API（高 Star、非 fork、非归档）</p>
      <p>「今日金句」= 以句号 / 叹号 / 问号完整收尾的简介（无链接 / 占位符，长度 10–160 字符）</p>
      <p>更新于 __UPDATED__（北京时间） · <a href="__SOURCE_LINK__" target="_blank" rel="noopener noreferrer">查看源码与每日更新机制</a></p>
    </footer>
  </div>

  <script>
    (function () {
      var btnAll = document.getElementById("btnAll");
      var btnQuote = document.getElementById("btnQuote");
      var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
      var tip = document.getElementById("tip");
      var quoteCount = cards.filter(function (c) { return c.dataset.quote === "1"; }).length;

      function setMode(mode) {
        var quoteMode = mode === "quote";
        document.body.classList.toggle("quote-mode", quoteMode);
        btnAll.classList.toggle("active", !quoteMode);
        btnQuote.classList.toggle("active", quoteMode);
        btnAll.setAttribute("aria-pressed", String(!quoteMode));
        btnQuote.setAttribute("aria-pressed", String(quoteMode));
        cards.forEach(function (card) {
          var visible = !quoteMode || card.dataset.quote === "1";
          card.classList.toggle("hidden", !visible);
        });
        if (quoteMode && quoteCount === 0) {
          tip.textContent = "今日 10 条简介均未达到金句标准，已自动切回全部项目。";
        } else {
          tip.textContent = "";
        }
      }

      btnAll.addEventListener("click", function () { setMode("all"); });
      btnQuote.addEventListener("click", function () {
        if (quoteCount === 0) {
          tip.textContent = "今日暂无符合条件的金句简介。";
          return;
        }
        setMode("quote");
      });
    })();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
