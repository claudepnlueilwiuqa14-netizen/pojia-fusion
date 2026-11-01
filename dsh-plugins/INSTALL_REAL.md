# 插件真实安装手册（已在真机验证）

> 本文记录的是**真机跑通**的安装方式，不是推测。
> 验证环境：DeepSeek Harness 桌面端（`C:\Users\qq\AppData\Local\Programs\DeepSeek Harness`），
> profile = `C:\Users\qq\.dsh\profiles\desktop`。

---

## 一、DSH 插件的真实机制

DSH 是 Cordis 微内核。**插件 = 一个带 `cordis.patch.yml` 的 npm 包**，装进 profile 的
`node_modules`，并把包名登记进 profile `package.json` 的 `dsh.profile.bundles`。

最终生效的 patch 树 = `bundles`（按顺序，各自的 `cordis.patch.yml`）
→ profile 根的 `cordis.patch.yml` → `--patch` 覆盖层。

所以：
- **插件只追加自己的 entry，不会覆盖别的插件的 entry**（每个包一个自己的 id）。
- profile 根 `cordis.patch.yml` 里的 `dsh-purge` 破甲块在插件树**之后**生效，插件无法覆盖它。
- 每个插件包的 `package.json` 里都有 `dsh.bundle.patch = "./cordis.patch.yml"`。

---

## 二、真实安装步骤（无头可执行）

DSH 没有独立 `dsh` CLI，插件管理器是 GUI 驱动的；但安装动作本质是
「pnpm add 到 profile + 往 bundles 里加包名」，可以直接在命令行做：

```bash
# 1) 用 DSH 自带的 pnpm（版本锁死，避免全局 pnpm 版本漂移）
cd /c/Users/qq/.dsh/profiles/desktop
node "/c/Users/qq/AppData/Local/Programs/DeepSeek Harness/resources/runtime/primary-runtime/dependencies/pnpm/bin/pnpm.mjs" \
  add dshmarket@1.73.7 dsh-free-search@0.9.26 dsh-codex-ui@1.2.1 dsh-better-sidebar@0.28.2 \
      dsh-ops@0.4.4 dsh-git-graph@0.1.9 dsh-browser@0.1.0 dsh-workflow@0.1.0 \
      dsh-chat-import@0.26.3 dsh-find-plugin@0.4.0

# 2) 登记进 bundles（package.json 的 dsh.profile.bundles）
#    保留原有的 @deepseek-ai/dsh-base / dsh-web-app / dsh-purge, 把插件名追加进去
```

> `pnpm add` 会保留 `dsh-purge` 的 `link:C:/Users/qq/dsh-purge` 本地链接和 `dsh` 字段。
> 装完 `node_modules` 从 1 个包涨到 98 个（nodeLinker: hoisted）。

---

## 三、真机装成并验证的 10 款（B站横评下载榜主力）

| 插件 | 版本 | npm | 真机表现 |
|------|------|-----|----------|
| `dshmarket` | 1.73.7 | ✅ | 插件市场（可视化浏览/搜索） |
| `dsh-codex-ui` | 1.2.1 | ✅ | Codex 风格模型弹窗 |
| `dsh-better-sidebar` | 0.28.2 | ✅ | 增强侧边栏（文件树/编辑器/变更/任务） |
| `dsh-free-search` | 0.9.26 | ✅ | 27 个免费搜索引擎 |
| `dsh-ops` | 0.4.4 | ✅ | Windows x64 原生文件/PTC 工具 |
| `dsh-git-graph` | 0.1.9 | ✅ | 会话面板出现 **Git** 标签页（截图可见） |
| `dsh-browser` | 0.1.0 | ✅ | Playwright 浏览器自动化 |
| `dsh-workflow` | 0.1.0 | ✅ | Workflow Studio |
| `dsh-chat-import` | 0.26.3 | ✅ | 侧边栏出现 **导入会话**（截图可见） |
| `dsh-find-plugin` | 0.4.0 | ✅ | 在会话内搜插件（走 GitHub） |

清单里这些**不在 npm**（只能走 GitHub 源）：`billion-context`、`dsh-web-ui`、`dsh-TUI`、
`modlens`、`dsh-vision-toolkit`、`ModSearch`、`dsh-deep-whale`，
以及 GitHub 源 `dsh-agent-teams`、`dsh-image-gen`、`dsh-im-gateway`、`Hindsight`、`archify`。

---

## 四、首启必做：dsh-purge 的「用户须知」弹窗

装完插件**第一次启动**会弹一个「用户须知」对话框（dsh-purge 自带）：

```
⚠️ 本插件免费开源，任何可将著作权人自售卖、付费倒卖…作者将依法追究法律责任。
[ ] 我已阅读并理解上述用户须知，同意合法合规使用。
[我已知晓并继续]
```

**不点掉它，聊天框按 Enter 不会发出去**（真机踩过：请求根本没发出去）。
勾选复选框 → 点「我已知晓并继续」→ 之后不再弹出。

自动化测试脚本里对应 `real_user_end_test.py::dismiss_notice()`。

---

## 五、插件在位后破甲是否还稳

真机实测结论（详见 `TEST_REPORT.md` 第四节）：

- `dsh-purge` 破甲块在 profile 根 `cordis.patch.yml` 里，位置在插件树之后 → 插件覆盖不了它。
- 代理层注入与模型路由完全在插件体系之外 → 插件装不装都不影响。
- 装插件后重跑真实 UI 测试：Harness postPrompt ✅、代理层注入 ✅、人格自动路由 ✅、
  回复零拒答 ✅、攻击性交付物完整 ✅。
- 敌对插件压力测试（改 provider + 注入"必须拒绝"竞争 systemPrompt）→ 破甲块 sha256 不变、代理层照常注入。

---

## 六、已知坑

1. **`dsh-purge --status` 会把宿主认成 Cherry Studio**（`plugins/dir` 指到
   `…\Cherry Studio\resources\app.asar.unpacked\node_modules\@deepseek-ai`），
   于是它自报"补丁 3/82 已清洗, 33 待清洗"。原因：它按包名扫描宿主目录，
   而 Cherry Studio 与 DeepSeek Harness 都内置了 `@deepseek-ai/*`。
   这不影响破甲——真正生效的是 profile 根 `cordis.patch.yml` 的 `dsh-purge` 块 + 代理层。
2. **环境里 `HTTP_PROXY=127.0.0.1:64289`**：Playwright 连本机 CDP 会被代理吃掉（502）。
   自动化脚本必须在 `import playwright` 之前设 `NO_PROXY=127.0.0.1,localhost`。
3. **host / Chrome 都是启动脚本的子进程**，脚本一退就被回收 → 整个测试必须在同一个前台进程里跑完。
