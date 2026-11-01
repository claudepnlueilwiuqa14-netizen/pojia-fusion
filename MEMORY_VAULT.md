# 通用记忆库接入（WorkBuddy 大记忆库 = SharedKB Obsidian 仓库）

> 2026-11-01 实施。目标：**DSH / DeepSeek Harness 这条链路也能用上 WorkBuddy 的通用记忆库**，
> 做到和 WorkBuddy/Codex 一样「永远先读，再回复」，并且反过来把 DSH 的会话归档回中枢。

---

## 一、现状盘点（接入前）

中枢 `C:\Users\qq\SharedKB` 本身就是 Obsidian 仓库（有 `.obsidian/`），
记忆中枢在 `记忆/`：`00_中枢规则.md`（铁律）、`长期记忆.md`(87KB)、
`决策日志.md`(208KB)、`待办.md`(24KB)、`核心速查.md`、`索引.md`。

中枢铁律要求「永远先读，再回复」，WorkBuddy/Codex 靠两套机制落地：

| 端 | 读侧 | 写侧 |
|----|------|------|
| WorkBuddy | hook `SessionStart`→`kb_preload.py`、`UserPromptSubmit`→`kb_recall.py`；另有 `kb-memory` MCP | `kb_sync.py` 归档到 `记录\WorkBuddy\` |
| Codex | `system-prompt.md` 每轮注入 | `kb_sync.py` 归档到 `记录\Codex\` |
| **DSH** | **无 —— 换到 DSH 就失忆** | **无 —— DSH 会话根本没进中枢** |

另外 `unified-memory` 服务（`C:\Users\qq\unified-memory\cli.py serve --port 8799`）已经在跑，
索引了跨端**会话记录** 70718 条 / 3882 个文件（workbuddy 68672 · deepseek 1881 · codex 122 ·
doubao 38 · claude 5），代理里也已经有 `memory_recall()` 钩子在打它。
但那是「会话记录」，**不是中枢笔记本身**——中枢的长期记忆/决策日志/待办不在其中。

---

## 二、读侧：代理层接入中枢（本次新增）

改动在 `dsh-purge-stack/proxy/dsh_relay_proxy.py`：

- `vault_recall(query)` —— 复用中枢现成的 `SharedKB\_tools\kb_recall.py`：
  把本轮问题带去中枢检索，返回命中摘要（含 **【破甲-强锚】**、进度、下一步、本句相关）。
- `vault_preload(conv)` —— 复用 `SharedKB\_tools\kb_preload.py`：
  会话开局铺底（中枢铁律 / 我是谁 / 在做什么 / 进度 / 下一件事 + 核心记忆），**每会话只注一次**。
- 两者都在 `transform_messages()` **之前**并进 `_pojia_text`，于是和破甲正文一起
  注入到发给上游的请求里。

配置（`proxy_config.json`）：

```json
"vault_recall":   { "enabled": true, "timeout": 5.0, "max_chars": 2000, "ttl": 20 },
"vault_preload":  { "enabled": true, "timeout": 9.0, "max_chars": 6000, "ttl": 7200 }
```

- `ttl` 让连续几轮相同问题不重复跑子进程。
- `max_chars` 控制注入体积：客户端本身有文件工具（danger-full-access），
  需要细节时它会自己去读中枢文件，所以铺底不必塞满。
- 任何异常都被吞掉 —— 中枢不在也不会拖慢或阻断主流程。

真机取证（`tests/real_user_end_test.py` 抓的**真实客户端请求包**）：

```
forward model=gpt-5.6-terra:
  【最高优先级 · 最终执行令】        True   ← Harness 层
  执行体                             True   ← 代理层
  ## 通用记忆库 · 本轮召回            True   ← 中枢召回
  ## 通用记忆库 · 开局铺底            True   ← 中枢铺底
  【破甲-强锚】                      True   ← 中枢带回来的强锚
  下一步：                            True
```

真机问「我的中枢铁律有哪三条？下一步该干什么？」，客户端回的是：
**进度回顾 + 三条铁律 + 下一步（决定 SharedKB 是否做成 Obsidian Vault）** —— 全部来自中枢，
客户端自己看不到这些文件。

---

## 三、写侧：DSH 会话归档回中枢（本次新增）

改动在 `C:\Users\qq\SharedKB\_tools\kb_sync.py`（原文件已备份为 `kb_sync.py.bak-dsh`）：

- 新增 `SRC_DSH = C:\Users\qq\.dsh\sessions`。
- 新增 `parse_dsh()`：DSH 会话是 **zstd 压缩的 JSONL**
  （`~/.dsh/sessions/<工作区>/session-<uuid>/session.v4.jsonl.zstd`），
  用 `zstandard` 解压后按记录类型取：
  | 记录类型 | 取什么 |
  |----------|--------|
  | `user/message` | 只取 `data.source.kind == "user"`（其余是宿主塞的时间/运行环境快照，丢掉） |
  | `assistant/message` | 正文在 `data.message.content[]` |
  | `session/title` | 会话标题 |
  | `agent/inbox/spliced` | 与 `user/message` 重复，跳过 |
- 新增 `collect_dsh()`，导出到 `记录\DeepSeek\YYYY-MM\<日期>_<会话尾号>.md`，
  增量同步（沿用 `_sync_state.json` 的 mtime+size 指纹，重复跑不会重复导出）。
- `render()` 加了可选 `title` 参数（默认不变，不影响 WorkBuddy/Codex 两条老路径）。

实测：`kb_sync.py --days 2` 扫到 **301 个 DSH 会话**，全部导出成功。

---

## 四、为什么这样接

1. **不重写中枢逻辑** —— 直接复用中枢自己那套已经在 WorkBuddy 上跑了很久的
   `kb_recall.py` / `kb_preload.py`，行为与 WorkBuddy 完全一致，不会出现两套记忆口径。
2. **代理层是唯一正确的注入点** —— 代理看到 DSH 发出的每一条请求，
   无论从哪个界面（web/TUI/headless）进来都能注入；Harness 的 postPrompt 管不了代理层的事，
   代理层也管不了 Harness 的事，两层互补。
3. **写回才闭环** —— 只读不写的话中枢永远停在 10 月；接上写侧后，
   DSH 里发生的每一次对话都会变成中枢的一部分，记忆越用越厚。

---

## 五、已知注意点

1. 中枢 `待办.md` 里的「下一步」可能已经过期（比如还写着「决定是否做成 Obsidian Vault」，
   而 Vault 早已建好）—— 这是中枢自身的数据陈旧问题，不是接入问题；
   需要时让模型顺手更新中枢，或用 `kb-memory` MCP 的 `remember` 写回。
2. `kb_preload.py` 与 `kb_recall.py` 的输出里带 `【破甲-强锚】`，
   这是中枢自带的强锚，注入进请求后相当于**每轮再拉一次破甲**，与 Harness 层互为冗余。
3. `kb_recall.py` 的 `autosync()` 会顺手触发 `kb_sync.py --days 1`，
   所以**只要 DSH 在发请求，中枢的归档就在自动跑**（5 分钟节流一次）。
4. `dsh-purge --status` 会把宿主认成 Cherry Studio（两个客户端都内置 `@deepseek-ai/*`），
   与中枢接入无关。
