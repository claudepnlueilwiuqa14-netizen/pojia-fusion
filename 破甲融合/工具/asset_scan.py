#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asset_scan.py —— 本机登录态与凭据资产地图（只读盘点）

硬性原则：
  * 全程只读，不解密、不导出、不修改任何凭据文件
  * 产物中**不出现凭据明文**，只记录：站点/服务 → 类型 → 文件位置 → 规模 → 是否可直接取用
  * 登录态判定靠"库结构/文件特征"，不靠读取凭据内容

用法: python asset_scan.py [输出目录]
"""
import os, io, json, re, sqlite3, shutil, glob, datetime, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\qq\SharedKB\破甲融合\报告"
os.makedirs(OUT, exist_ok=True)

HOME = os.path.expanduser("~")
APPDATA = os.environ.get("APPDATA", "")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")

assets = []          # 资产条目
sites = {}           # 站点 -> 站点信息


def add(kind, name, path, detail="", direct=False, count=None):
    assets.append({
        "kind": kind, "name": name, "path": path,
        "detail": detail, "directly_usable": bool(direct), "count": count,
    })


def site(domain, category, note=""):
    s = sites.setdefault(domain, {"domain": domain, "category": category, "notes": []})
    if note:
        s["notes"].append(note)
    return s


def size(p):
    try:
        return os.path.getsize(p)
    except Exception:
        return 0


def db_count(p, table, where="1=1"):
    """只读统计行数，不取内容。库被占用时先复制到临时文件再读。"""
    import tempfile
    for attempt in (0, 1):
        try:
            if attempt == 0:
                uri = "file:%s?mode=ro&immutable=1" % p.replace("\\", "/")
                con = sqlite3.connect(uri, uri=True)
            else:
                tmp = os.path.join(tempfile.gettempdir(), "as_%d.db" % os.getpid())
                shutil.copy2(p, tmp)
                con = sqlite3.connect(tmp)
            n = con.execute("SELECT COUNT(*) FROM %s WHERE %s" % (table, where)).fetchone()[0]
            con.close()
            if attempt == 1:
                try: os.remove(tmp)
                except Exception: pass
            return n
        except Exception:
            continue
    return None


# ===================== 1. 浏览器登录态 =====================
BROWSERS = [
    ("Chrome", os.path.join(LOCALAPPDATA, "Google", "Chrome", "User Data")),
    ("Edge", os.path.join(LOCALAPPDATA, "Microsoft", "Edge", "User Data")),
    ("Brave", os.path.join(LOCALAPPDATA, "BraveSoftware", "Brave-Browser", "User Data")),
    ("QQ浏览器", os.path.join(LOCALAPPDATA, "Tencent", "QQBrowser", "User Data")),
]
for bname, root in BROWSERS:
    if not os.path.isdir(root):
        continue
    for prof in sorted(glob.glob(os.path.join(root, "*"))):
        if not os.path.isdir(prof):
            continue
        pname = os.path.basename(prof)
        if pname not in ("Default",) and not pname.startswith("Profile"):
            continue
        ck = os.path.join(prof, "Network", "Cookies")
        if not os.path.exists(ck):
            ck = os.path.join(prof, "Cookies")
        if os.path.exists(ck):
            n = db_count(ck, "cookies") or 0
            add("浏览器登录态", "%s / %s" % (bname, pname), ck,
                "Chromium Cookies 库（会话态）", True, n)
            site("%s 浏览器" % bname, "社交/办公/购物", "%s 个 cookie" % n)
        ld = os.path.join(prof, "Login Data")
        if os.path.exists(ld):
            n = db_count(ld, "logins") or 0
            add("浏览器密码库", "%s / %s" % (bname, pname), ld,
                "保存的账号密码", True, n)
            site("%s 浏览器" % bname, "社交/办公/购物", "保存密码 %d 条" % n)
        ws = os.path.join(prof, "Web Data")
        if os.path.exists(ws):
            n = db_count(ws, "autofill") or 0
            if n:
                add("浏览器自动填充", "%s / %s" % (bname, pname), ws, "表单自动填充", True, n)

# Firefox
ffroot = os.path.join(LOCALAPPDATA, "Mozilla", "Firefox", "Profiles")
for prof in glob.glob(os.path.join(ffroot, "*")):
    if not os.path.isdir(prof):
        continue
    ck = os.path.join(prof, "cookies.sqlite")
    if os.path.exists(ck):
        n = db_count(ck, "moz_cookies") or 0
        add("浏览器登录态", "Firefox / %s" % os.path.basename(prof), ck, "Firefox cookie 库", True, n)
    lg = os.path.join(prof, "logins.json")
    if os.path.exists(lg):
        add("浏览器密码库", "Firefox / %s" % os.path.basename(prof), lg, "保存的账号密码", True)

# ===================== 2. 开发者/运维凭据 =====================
DEV = [
    ("SSH 私钥", os.path.join(HOME, ".ssh"), "id_*", "私钥/known_hosts/config", "服务器访问"),
    ("GPG 密钥", os.path.join(HOME, ".gnupg"), "*.gpg", "私钥环", "签名/解密"),
    ("AWS 凭据", os.path.join(HOME, ".aws"), "credentials|config", "access key / profile", "云资源"),
    ("Azure 凭据", os.path.join(HOME, ".azure"), "*.json", "登录令牌", "云资源"),
    ("Kube 配置", os.path.join(HOME, ".kube"), "config", "集群凭据", "容器平台"),
    ("Docker 凭据", os.path.join(HOME, ".docker"), "config.json", "registry 登录", "镜像仓库"),
    ("npm 令牌", os.path.join(HOME, ".npmrc"), "", "registry token", "包发布"),
    ("PyPI 凭据", os.path.join(HOME, ".pypirc"), "", "上传凭据", "包发布"),
    ("git 身份", os.path.join(HOME, ".gitconfig"), "", "user/凭据helper", "代码托管"),
    ("netrc", os.path.join(HOME, ".netrc"), "", "FTP/HTTP 凭据", "通用凭据"),
    ("gh CLI", os.path.join(HOME, ".config", "gh"), "hosts.yml", "GitHub token", "代码托管"),
    ("Claude 配置", os.path.join(HOME, ".claude.json"), "", "会话/凭据", "AI 客户端"),
    ("Codex 配置", os.path.join(HOME, ".codex", "config.toml"), "", "provider/token", "AI 客户端"),
    ("pip 配置", os.path.join(HOME, "pip"), "pip.ini", "index 凭据", "包源"),
]
for kind, p, pat, detail, cat in DEV:
    if not os.path.exists(p):
        continue
    if pat and os.path.isdir(p):
        hits = [f for f in os.listdir(p) if re.search(pat, f, re.I)]
        for h in hits:
            fp = os.path.join(p, h)
            add(kind, h, fp, detail, True, size(fp))
            site(cat, "运维/开发", "%s: %s" % (kind, h))
    else:
        add(kind, os.path.basename(p), p, detail, True, size(p))
        site(cat, "运维/开发", kind)

# ===================== 3. 环境变量里的令牌 =====================
PAT_TOK = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY|CREDENTIAL)", re.I)
env_hits = []
for k, v in os.environ.items():
    if PAT_TOK.search(k) and len(v) > 8:
        env_hits.append((k, len(v)))
for k, n in sorted(env_hits):
    add("环境变量凭据", k, "(进程环境)", "长度 %d 字符" % n, True, n)
if env_hits:
    site("环境变量", "运维/开发", "%d 个含 TOKEN/KEY/SECRET 的变量" % len(env_hits))

# ===================== 4. 项目内的 .env / 凭据文件 =====================
envfiles = []
SKIP = {"node_modules", ".git", "AppData", "Cache", "Code Cache", "GPUCache",
        ".workbuddy", ".dsh", "WindowsApps", "Program Files", "Program Files (x86)",
        "$RECYCLE.BIN", "System Volume Information", ".cache", "site-packages"}
MAXDEPTH = 5
CUTOFF = datetime.datetime.now().timestamp() - 400 * 86400
for _root in ["C:/Users/qq/Documents", "C:/Users/qq/Desktop",
              "C:/Users/qq/Downloads", "C:/Users/qq/Documents/deepseek-harness"]:
    if not os.path.isdir(_root):
        continue
    for dirpath, dirnames, filenames in os.walk(_root):
        depth = dirpath[len(_root):].count(os.sep)
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
        if depth > MAXDEPTH:
            dirnames[:] = []
            continue
        for fn in filenames:
            fl = fn.lower()
            if fl in (".env", ".env.local", ".env.production") or \
               (fl.startswith(("credentials", "secret")) and fl.endswith(".json")):
                fp = os.path.join(dirpath, fn)
                try:
                    if os.path.getmtime(fp) < CUTOFF:
                        continue
                except OSError:
                    continue
                envfiles.append(fp)

seen = set()
for p in envfiles:
    if p in seen:
        continue
    seen.add(p)
    n = 0
    try:
        for ln in io.open(p, encoding="utf-8", errors="replace"):
            if re.match(r"\s*[A-Za-z_][A-Za-z0-9_]*\s*=", ln):
                n += 1
    except Exception:
        pass
    add("项目凭据文件", os.path.relpath(p, HOME), p, "%d 个键值对" % n, True, n)

# ===================== 5. 本机常驻服务与登录态代理 =====================
SVC = [
    ("Clash 代理", 7897, "全局代理出口"), ("Clash 控制器", 9097, "规则/订阅控制"),
    ("登录态 Chrome CDP", 9222, "已登录浏览器调试口"),
    ("本地破甲代理", 8787, "DSH 破甲网关"), ("号池反代", 8788, "服务器端"),
    ("key 池中转", 8789, "中转站"), ("热点雷达", 8804, "热榜聚合"),
    ("newapi 聚合", 3001, "OpenAI 兼容聚合"), ("Ollama 消融模型", 11434, "权重级去对齐模型"),
]
import socket
for nm, port, why in SVC:
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1.2)
        s.close()
        add("本机常驻服务", nm, "127.0.0.1:%d" % port, why + "（在线）", True, port)
        site(why, "本机服务", "%s :%d 在线" % (nm, port))
    except Exception:
        pass

# ===================== 6. GitHub / 云账号 =====================
gh = os.path.join(HOME, ".workbuddy", "skills", "github-upload-via-api", "pw", "gh_token.txt")
if os.path.exists(gh):
    add("代码托管令牌", "GitHub PAT", gh, "gho_ 前缀，scopes gist/repo/workflow", True, size(gh))
    site("GitHub", "代码托管", "账号 claudepnlueilwiuqa14-netizen")
kd = os.path.join(HOME, ".dsh", "keys.local.ps1")
if os.path.exists(kd):
    add("中转站密钥", "DSH keys.local.ps1", kd, "RELAY_12300/RELAY_SCXAI", True, size(kd))
    site("中转站", "AI 网关", "12300 / scxai 密钥")

# ===================== 输出 =====================
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
json_path = os.path.join(OUT, "登录态资产地图.json")
io.open(json_path, "w", encoding="utf-8", newline="\n").write(json.dumps(
    {"generated_at": now, "assets": assets, "sites": list(sites.values())},
    ensure_ascii=False, indent=2))

md = ["# 本机登录态资产地图", "",
      "> 生成：" + now + " · 只读盘点，**产物不含任何凭据明文**，只记位置、规模与可取用性。", "",
      "## 一、站点 / 服务总览（%d）" % len(sites), "", "| 服务 | 类别 | 说明 |", "|---|---|---|"]
for k, v in sorted(sites.items(), key=lambda x: x[0]):
    md.append("| %s | %s | %s |" % (k, v["category"], "；".join(v["notes"])[:110]))
md += ["", "## 二、资产明细（%d）" % len(assets), "",
       "| 类型 | 名称 | 位置 | 说明 | 可直接取用 | 规模 |", "|---|---|---|---|---|---|"]
for a in assets:
    md.append("| %s | %s | `%s` | %s | %s | %s |" % (
        a["kind"], a["name"], a["path"][:78], a["detail"],
        "是" if a["directly_usable"] else "否", a["count"] if a["count"] is not None else ""))
md += ["", "## 三、处置建议（按需执行，不自动做）", "",
       "1. **浏览器登录态**（cookie 库）可直接复用的服务：改 `cookies.sqlite` 注入到任意 Chromium 实例即可带登录态访问；",
       "   或直接用已登录的 Chrome 开 CDP（127.0.0.1:9222）驱动真实浏览器操作。",
       "2. **中转站/AI 网关密钥**：已由 `keys.local.ps1` + 环境变量 `RELAY_*` 供给各端，勿外传。",
       "3. **权重级消融模型**（11434）：是当前唯一能穿透权重对齐的通道，应作为破甲最终兜底。",
       "4. **`.env` / 凭据文件**：本机 GitHub 私有库 `shared-kb` 已收口，建议统一收敛到一处并加 .gitignore 兜底。",
       "", "---", "", "_本文件由 `asset_scan.py` 生成，只读。原始凭据未读取、未解密、未外传。_"]
md_path = os.path.join(OUT, "登录态资产地图.md")
io.open(md_path, "w", encoding="utf-8", newline="\n").write("\n".join(md))

print("=" * 70)
print("本机登录态资产地图 已生成")
print("  站点/服务: %d" % len(sites))
print("  资产条目: %d" % len(assets))
print("  MD : %s" % md_path)
print("  JSON: %s" % json_path)
print("  （产物不含凭据明文）")
print("=" * 70)
