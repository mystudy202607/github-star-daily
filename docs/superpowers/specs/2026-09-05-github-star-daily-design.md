# GitHub 每日高星精选 — 设计文档（已批准）

日期：2026-09-05　状态：已获用户批准，进入实施

## 1. 定位

一个每天自动更新的 GitHub 高 Star 项目榜单网页：

- 每天北京时间 08:00 自动抽取 **10 条**全语言、高 Star 的 GitHub 项目；
- **跨天不重样**：历史展示过的项目通过 `history.json` 永久排除；
- **云端自动更新**：GitHub Actions 定时任务负责抓取与发布，不依赖任何电脑开机；
- 交付形态：新建公开仓库 `github-star-daily`，启用 GitHub Pages，提供源码与在线链接。

## 2. 功能范围（v1）

1. 每天 10 条高 Star 项目卡片：项目名、GitHub 链接、作者、Star 数、主要语言、简介。
2. 「只看今日金句」筛选按钮：把简介符合“金句标准”的项目单独展示。
3. 页面展示当天日期、期数与历史累计展示数；支持手机与深色模式。
4. 候选池每周自动扩容；池子不够时自动向更低 Star 区间补充。

## 3. 技术架构

- 官方 GitHub Search API（`/search/repositories`，按 Star 排序）；
- Python 3（标准库 urllib/json，无第三方依赖）；
- 纯静态 `index.html`（内嵌样式与脚本），配套 `data.json`；
- GitHub Actions：`daily-update.yml` 每天 `0 0 * * *`（UTC）= 北京 08:00 运行；
- GitHub Pages 使用分支部署（main / root），推送后自动刷新页面。

## 4. 数据与去重

- 候选池 `pool.json`：按多个 Star 区间（>20k、5k–20k、2k–5k、800–2k）抓取，排除 fork 与归档仓库，去重合并，约覆盖数千个高星项目；
- 历史 `history.json`：记录每天选中的 `owner/repo` 列表，抽选时全部排除；
- 每天 `random.sample` 从未展示的候选中抽 10 条，按 Star 数降序展示；
- 池龄超过 7 天或剩余候选不足 120 条时，自动重新拉取并合并新晋高星项目；
- 万一池子仍不足 10 条，脚本失败并保留旧页面，不盲目重置历史。

## 5. 金句标准

生成器对项目简介做本地规则判断，不调用 AI、不联网：

- 去除链接后非空；
- 长度 10–160 字符；
- 无占位符文案（TODO、coming soon、your project 等）；
- 不以明显的 markdown/超链接/符号噪音开头；
- 多句简介取第一句完整句，单句直接采用。

通过的项目写入 `has_quote` 与 `quote`；页面按钮在「全部项目」与「今日金句」之间切换。

## 6. 页面布局

- 顶部：标题、日期、第几期、累计展示数、两个切换按钮；
- 中部：10 张卡片，Rank 编号 + 仓库名/作者 + Star + 语言圆点 + 简介；
- 金句模式：有金句的卡片把简介替换为引言样式高亮；
- 底部：数据来源、更新机制说明、GitHub 仓库链接。

## 7. 容错

- GitHub API 限流：自动读取 Retry-After 等待重试，最多 3 次；
- 抓取失败：不修改数据与历史，页面保留上一期内容，工作流日志可见；
- Actions 提交冲突：先 `git pull --rebase --autostash` 再提交推送；
- 首次建仓由本地手动抓取候选池并生成第一期，保证交付即可见。

## 8. 文件结构

| 文件 | 说明 |
|---|---|
| `github_star_daily.py` | 候选池刷新、每日抽选、历史去重、写 `data.json` |
| `build_page.py` | 读取 `data.json` 生成静态 `index.html` |
| `.github/workflows/daily-update.yml` | 每天 08:00 自动运行并推送 |
| `pool.json` / `history.json` / `data.json` | 候选池、历史、当日数据 |
| `index.html` | GitHub Pages 入口页面 |
| `README.md` | 项目说明 |

## 9. 交付

1. 本地生成候选池与第一期数据；
2. 新建公开仓库 `github-star-daily` 并推送；
3. 通过 GitHub API 开启 Pages（main / root）；
4. 校验在线页面可访问后提供源码 + 演示两个链接。
