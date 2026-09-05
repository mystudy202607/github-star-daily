# GitHub 每日高星精选

每天北京时间 **08:00** 自动从 GitHub 高 Star 候选池中抽取 **10 个项目**，
展示为一张跨天不重样的榜单网页，全程云端自动更新。

- 📦 源码仓库：<https://github.com/mystudy202607/github-star-daily>
- 🚀 在线演示：<https://mystudy202607.github.io/github-star-daily/>

## 功能

- **每天 10 条**：全语言、高 Star、非 fork、非归档项目，按 Star 数排序展示；
- **跨天不重样**：历史记录永久排除已展示项目；
- **每天 08:00 自动更新**：GitHub Actions 定时运行，不依赖电脑开机；
- **候选池自动扩容**：跨多个 Star 区间抓取，约每 7 天自动合并一次新晋高星项目；
- **今日金句筛选**：可一键切换只看“以句号/叹号/问号完整收尾”的简介；
- 深色 GitHub 风格、手机自适应、纯静态页面。

## 自动更新机制

`.github/workflows/daily-update.yml` 每天执行：

```text
cron: 0 0 * * *   # UTC 00:00 = 北京时间 08:00
```

每次运行流程：

1. 读取 `pool.json` 候选池；若超过 7 天未刷新或剩余候选不足，自动调用
   GitHub Search API 按 Star 区间扩容；
2. 从未展示过的候选中随机抽取 10 条；
3. 排除历史后写入 `history.json`，生成当日 `data.json`；
4. 用 `build_page.py` 生成静态 `index.html`；
5. `git commit` 并推送到 `main`，GitHub Pages 自动发布新页面。

## 本地运行

```powershell
# 1. 手动刷新候选池（约 1–2 分钟，需要 Token）
$env:STAR_TOKEN = (gh auth token)
python github_star_daily.py refresh

# 2. 抽选今天 10 条并生成网页
python github_star_daily.py run

# 预览明天但不写文件（验证去重）
python github_star_daily.py run --date 2026-09-06 --dry-run
```

也可以直接在仓库 Actions 页面点击 **Run workflow** 手动触发一次更新。

## 文件结构

| 文件 | 说明 |
|---|---|
| `index.html` | GitHub Pages 入口（纯静态网页） |
| `data.json` | 当天榜单数据 |
| `pool.json` | 高星候选池（GitHub Search API 抓取） |
| `history.json` | 每日展示历史（用于跨天去重） |
| `github_star_daily.py` | 候选池刷新 + 每日抽选 + 历史去重 |
| `build_page.py` | 读取 `data.json` 生成静态 `index.html` |
| `update.log` | 每日运行日志 |
| `.github/workflows/daily-update.yml` | 每天 08:00 自动更新工作流 |
| `docs/superpowers/specs/` | 设计文档 |

## 数据口径与“金句”标准

- 候选池：Star 区间 `>20k`、`5k–20k`、`2k–5k`、`800–2k`，排除 fork 与归档仓库，
  首次建仓时本地抓取到 **4000 个唯一项目**，之后每周自动补充新晋项目；
- 历史去重：`history.json` 累积全部展示记录，抽选时全部排除；
- 金句：无链接/占位符/符号噪音、长度 10–160 字符、以 `.` `!` `?` 或中文
  对应标点完整收尾的简介；多句简介取第一句完整句。

## 说明

- 数据来自 GitHub 官方公开 Search API，页面仅供学习交流；
- 若某天抓取或更新失败，页面会保留上一期内容，`Actions` 日志可查原因；
- GitHub Pages 首次部署后需要约 1–2 分钟生效。
