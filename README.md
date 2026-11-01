# pojia-fusion · SDzibo + 彻底破甲 + 多模型接入 全套

> 一套把 **DeepSeek Harness 复刻客户端（SDzibo）** 与 **彻底破甲融合体系** 拼起来的完整工具链。
> 目标：在自己机器上拥有一个 **不限制、可自动切人格、能接多家模型** 的 AI 工作台。

---

## 0. 这套东西是什么

| 组件 | 目录 | 作用 |
|---|---|---|
| **SDzibo 启动器** | `SDzibo/` | 复刻官方 DeepSeek 桌面端：同 host / 同 profile / 同 dsh-purge agent / 同 gp-pojia 模型 / 同 DSH 前端，只改窗口标题=SDzibo、图标=八卦图（CDP 注入，不改 DSH 任何文件） |
| **破甲融合母本** | `破甲融合/` | 唯一真相源：core.md（全文条款）/ core_inject.md（注入渲染版）/ personas.json（母人格+26人格+自动路由）/ layers.md / tools-source.md + 生成器 gen_endpoints.py + GitHub 取工具脚本 |
| **dsh-purge-stack** | `dsh-purge-stack/` | 部署栈：本地破甲代理 `proxy/dsh_relay_proxy.py` + 配置 config/ + 一键 apply/verify/rollback + 守护 guardian.py + 监管 supervisor.py |
| **dsh-purge（上游）** | github.com/YuJunZhiXue/dsh-purge | 破甲注入插件本体（cordis 微内核插件，已在 GitHub） |
| **DSH 插件清单** | `dsh-plugins/` | 取自 B 站《DSH 插件下载榜横评！》的插件清单 + 一键安装脚本 |

---

## 1. 架构（破甲在哪两层）

```
 SDzibo 客户端 (DeepSeek Harness, profile=desktop)
        │  HTTP  → 本地破甲代理
        ▼
 dsh-purge-stack/proxy/dsh_relay_proxy.py   ← 127.0.0.1:8787
        │   · 人格自动路由 resolve_persona() / auto_persona()   （按任务关键词挂执行型人格）
        │   · 破甲注入 pojia_block()                         （给每条上游请求注入破甲正文）
        │   · 模型前缀路由 pool-/gp-/cx- → 上游
        ▼
 上游 relay: scxai (gpt-5.5/5.6/6/6.1-sol)  ·  12300 (deepseek-v4-pro/v4.1-flash)  ·  额度池
```

**破甲是双层的，覆盖所有接入模型**（与选哪个模型无关）：
1. **Harness 层**：`.dsh/profiles/desktop/cordis.patch.yml` 的 `dsh-purge` insert → `postPrompt`（浓缩破甲正文）。
2. **代理层**：`dsh_relay_proxy.py` 的 `pojia_block()` → 给每个上游请求注入完整破甲正文（+人格）。

---

## 2. 人格自动切换（是的，已经在跑）

代理层 `proxy/dsh_relay_proxy.py`：
- `AUTO_PERSONA_RULES` / `AUTO_PERSONA_AND`：敏感/黑灰产类请求自动挂执行型人格（WiFi/破解→胖虎、逆向/脱壳→小夫、渗透→韦神、拖库→猫猫、外挂→珊迪、恶意软件/勒索→恶魔护照…）。
- `resolve_persona()`：支持 `【人格:胖虎】` 前缀强制指定、单发人格名切换、单发「重置人格」回默认执行体。
- 母本 `personas.json` 里 `auto_route` 11 条规则 + 兜底，是这套路由的语义源。

**模型/供应商切换是手动的**：`switch-dsh-provider.ps1 -Provider scxai|12300` 改 desktop/headless 两个 profile 的默认模型。

---

## 3. 部署（在你自己机器上）

```powershell
# 1) 装破甲代理 + 写注入点（dsh-purge-stack/apply.ps1）
powershell -ExecutionPolicy Bypass -File dsh-purge-stack/apply.ps1

# 2) 起本地破甲代理（默认 127.0.0.1:8787）
#    dsh-purge-stack/0_启动破甲代理.bat  或  python dsh-purge-stack/proxy/dsh_relay_proxy.py

# 3) 起 SDzibo 窗口
python SDzibo/sdzibo_launcher.py

# 4) 切换模型供应商（可选）
powershell -File switch-dsh-provider.ps1 -Provider scxai   # 或 12300
```

> 母本改完用 `python 破甲融合/生成器/gen_endpoints.py --apply` 重新生成两端注入产物；守护 `guardian.py` 每 5 分钟从母本回写，任何对 cordis.patch.yml 的手改都会被还原。

---

## 4. 加模型（在 cordis.patch.yml 加 provider/models）

模型接入全在 `.dsh/profiles/desktop/cordis.patch.yml` 的 `relay-*` 段（apiBase + models 列表）。
本地代理 `dsh_relay_proxy.py` 用前缀路由：`pool-xxx`→额度池、`gp-xxx`→分组通道链兜底、`cx-xxx`→Codex 中转、`ds-xxx`→DeepSeek 中转。
要加新模型：在对应 relay 段加一行 `- id: 模型id`，并把上游 key 放进 `dsh-purge-stack/keys.local.ps1`（**本地保存、不上传**）。

---

## 5. 加 DSH 插件

见 `dsh-plugins/dsh_plugins_wishlist.md`（B 站横评全文清单）+ `dsh-plugins/install_all.ps1`（一键装）。
装插件只动 DSH 的 plugin bundle，**不会碰破甲注入点**。

---

## 6. 安全 / 脱敏说明

- 本仓库**不含任何真实 API key**。代理与启动器里的 `sk-...` 已全部替换为 `sk-RELAY_12300_API_KEY` / `sk-RELAY_SCXAI_API_KEY` 占位符。
- 真实 key 只放你本机 `dsh-purge-stack/keys.local.ps1`（已被 .gitignore 排除）。
- 切勿把 `keys.local.ps1`、真实 `cordis.patch.yml` 里硬编码的 key、`.log` 诊断文件提交到任何远程仓库。

---

## 7. 目录速查

```
pojia-fusion/
├─ README.md                     本文件
├─ .gitignore
├─ SDzibo/                       复刻客户端启动器 + 八卦图标（标题/图标 CDP 注入）
├─ 破甲融合/                      母本(唯一真相源) + 生成器 + GitHub 取工具
├─ dsh-purge-stack/               本地破甲代理 + 部署脚本 + 守护 + 监管
└─ dsh-plugins/                   DSH 插件清单 + 一键安装脚本
```
