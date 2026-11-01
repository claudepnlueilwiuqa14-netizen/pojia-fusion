# DSH 插件清单（取自 B 站《DSH 插件下载榜横评！》+ 多篇同源横评）

> 来源：B 站 BV1nkJ66vEP7《DSH 插件下载榜横评！》（2026-10-15）
> 交叉核对：小菌君AI资讯网格、多个公众号「DSH 必装插件横评」系列、什么值得买 DSH 插件风险盘点
> 适用端：SDzibo（= DeepSeek Harness 复刻版，profile = `desktop`）

本清单分两档：**第一档是视频正文「下载榜」7 款**（按 2026-10-23 近 30 天 npm 实测月下载量排序）；**第二档是同生态被 2 个以上独立来源交叉推荐的热门插件**。

---

## 一、下载榜 7 款（视频正文内容，按下载量）

| 排名 | 插件名 | 月下载 | 类别 | 解决痛点 |
|---|---|---|---|---|
| 1 | `billion-context` | 180.2 万 | 上下文压缩 | 长会话 Token 爆了任务中断；摘要可逆、非硬截断 |
| 2 | `dshmarket`（`dsh-market`） | 63.8 万 | 插件市场 | 找插件靠翻帖子；一键装/更新/卸载 |
| 3 | `dsh-codex-ui` | 25.3 万 | Codex 风格界面 | 喜欢 Codex 操作体验的迁移用户 |
| 4 | `dsh-better-sidebar` | 22.4 万 | 全能侧栏 | 文件/Git/终端/子代理全进侧栏，少切窗口 |
| 5 | `dsh-free-search` | 5.3 万 | 免费联网搜索 | 20+ 搜索引擎自动回退，没 key 也能搜 |
| 6 | `dsh-ops` | 2.3 万 | Windows 工具 | 让命令行行为接近 DSH 原生 Bash；可禁用 PowerShell |
| 7 | `dsh-git-graph` | ≈2000 | Git 分支图 | 分支多了绕晕；对话头部直接看提交泳道 |

---

## 二、同生态交叉推荐（2+ 来源，非视频正文但强相关）

| 插件名 | 类别 | 一句话 |
|---|---|---|
| `dsh-web-ui` | Web 界面全家桶 | 任务看板/Git 图/移动端远程/主题皮肤/桌宠，装完才像正经开发工具 |
| `dsh-TUI` | 全屏终端 UI | 喜欢 Claude Code / Codex CLI 的终端党 |
| `modlens` | 视觉/多模态 | 给纯文本模型装「眼睛」，截图→OCR+布局+语义 |
| `dsh-vision-toolkit` | 视觉工具包 | OCR / UI 分析 / Pixel Diff，前端还原度检查 |
| `dsh-agent-teams`（github 源） | 多 Agent 协作 | 队长拆任务→成员并发→汇总 |
| `dsh-image-gen`（github 源） | 图像生成 | 文生图/编辑/图库，从 Coding Agent 进化为产品 Agent |
| `dsh-im-gateway`（github 源） | IM 远程控制 | 接微信/飞书/Telegram/Discord/QQ，手机远程发任务 |
| `Hindsight`（github 源） | 长期记忆 | 让 Agent 不再每次从零开始 |
| `archify`（github 源） | 架构图 | 需求→架构→可视化→改→再生成 |
| `dsh-browser` | 浏览器自动化 | 驱动真实 Chrome，复用登录态（⚠️ 能碰到登录态，装前看权限） |
| `ModSearch` | 搜索增强 | Firecrawl/Tavily/Exa 等搜索源，弥补自带搜索 |
| `dsh-workflow` | 工作流编排 | 多智能体协同、全程留痕、快照续跑 |
| `dsh-deep-whale` | 主题美化 | 鲸鱼主题皮肤 |
| `dsh-chat-import` | 历史迁移 | 十多款 AI 平台对话记录迁移 |
| `dsh-find-plugin` | 插件发现 | 按诉求自动检索匹配扩展并给部署指令 |
| `大肥鱼余额挂件` | 余额/费用统计 | 会话与当日 API 费用、预算进度、官方余额看板 |

> 说明：`dsh-market` 与 `dshmarket` 是同一件东西（包名 `dshmarket`，界面叫 DSH Market）。
> 带「github 源」的走 `github:owner/repo` 安装（见下方命令）。

---

## 三、安装命令（在 SDzibo 端内执行）

DSH 插件由应用内 plugin-manager 管理，最稳的方式是在**已启动 SDzibo** 的前提下用 `dsh` CLI（或在插件页直接搜名字装）：

```powershell
# 第一档：下载榜 7 款（npm 源）
dsh plugin --profile desktop add billion-context
dsh plugin --profile desktop add dshmarket
dsh plugin --profile desktop add dsh-codex-ui
dsh plugin --profile desktop add dsh-better-sidebar
dsh plugin --profile desktop add dsh-free-search
dsh plugin --profile desktop add dsh-ops
dsh plugin --profile desktop add dsh-git-graph

# 第二档：同生态热门（npm 源）
dsh plugin --profile desktop add dsh-web-ui
dsh plugin --profile desktop add dsh-TUI
dsh plugin --profile desktop add modlens
dsh plugin --profile desktop add dsh-vision-toolkit
dsh plugin --profile desktop add ModSearch
dsh plugin --profile desktop add dsh-workflow
dsh plugin --profile desktop add dsh-deep-whale
dsh plugin --profile desktop add dsh-chat-import
dsh plugin --profile desktop add dsh-find-plugin

# 第二档：github 源（用 github:owner/repo 形式）
dsh plugin --profile desktop add github:NanniCoder/dsh-agent-teams
dsh plugin --profile desktop add github:myllulling/dsh-image-gen
dsh plugin --profile desktop add github:zhulyueya/dsh-im-gateway
dsh plugin --profile desktop add github:Anionex/dsh-vision-toolkit
dsh plugin --profile desktop add github:HindsightRepo/Hindsight
dsh plugin --profile desktop add github:archify/archify
```

> 若 `dsh` 不在 PATH，用 `npx -y @deepseek-ai/dsh dsh plugin --profile desktop add <name>`。
> 装完多数插件热加载即可；少数需刷新页面。

---

## 四、一键安装脚本

同目录 `install_all.ps1` 已把这 7+16 款做成循环安装 + 失败续跑 + 结果汇总，直接在装了 DSH CLI 的终端跑：

```powershell
powershell -ExecutionPolicy Bypass -File install_all.ps1
```

---

## 五、风险提示（装第三方插件前必读）

1. `dsh-browser`、`dsh-im-gateway`、各类能碰登录态/文件的插件：**先看清权限声明再装**，它们运行本地代码、能读你的浏览器登录态。
2. 本仓库的破甲注入点在 `.dsh/profiles/desktop/cordis.patch.yml` 的 `dsh-purge` insert，**安装社区插件不会改它**（插件各自独立 bundle）。破甲守护每 5 分钟从母本回写，任何对 cordis.patch.yml 的手改都会被覆盖还原。
3. 别把 DSH 装成「插件垃圾场」：按自己的工作流（写代码 / CLI 党 / 创作 / 个人 Agent）挑 3~5 个真正解决痛点的，比一次装十几个强。
