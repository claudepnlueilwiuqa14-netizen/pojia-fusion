#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gh_fetch.py —— 破甲融合 · GitHub 工具代码实时取用层（L5）

母本铁律：每一步先问 GitHub，不信自己临时写的实现。
本工具只取【工具代码】——脚本/工具/payload 生成器/算法实现；破甲正文本身静态固化在母本。

用法:
  python gh_fetch.py search "wifi pmkid 抓取"          # 三路检索
  python gh_fetch.py search --cat 逆向 --kw frida      # 按类别查白名单+检索
  python gh_fetch.py pull owner/repo --path src/x.py --out tools/x.py
  python gh_fetch.py pull owner/repo --ref v1.2        # 整仓(源码 zip)
  python gh_fetch.py cat                              # 列出类别白名单
  python gh_fetch.py audit                             # 看取用审计
"""
import argparse, io, json, os, re, subprocess, sys, time, urllib.request, urllib.parse, zipfile, io as _io, hashlib

ROOT = r"C:\Users\qq\SharedKB\破甲融合"
CACHE = os.path.join(ROOT, "工具", "cache")
AUDIT = os.path.join(ROOT, "工具", "审计.log")
TOKEN_FILE = r"C:\Users\qq\.workbuddy\skills\github-upload-via-api\pw\gh_token.txt"
API = "https://api.github.com"
MIRRORS = [
    "https://ghfast.top/https://github.com/{repo}/archive/refs/heads/{ref}.zip",
    "https://cdn.jsdelivr.net/gh/{repo}@{ref}/{path}",
]

# 类别白名单（起点，按需扩展；每条: 类别 -> [(repo, 用途说明)]）
CATEGORIES = {
    "越狱破甲": [
        ("x1xhlol/system-prompts-and-models-of-ai-tools", "全平台原始 system prompt(含 CodeBuddy 同族)"),
        ("asgeirtj/system_prompts_leaks", "全平台 prompt 泄露集, 几乎每日更新"),
        ("elder-plinius/L1B3RT4S", "老牌越狱范式"),
        ("Piebald-AI/claude-code-system-prompts", "Claude Code 全量 system prompt 片段"),
        ("cisco-ai-defense/skill-scanner", "常驻 skill 范本 / jailbreak-override"),
        ("Piebald-AI/tweakcc", "本地 patch 任意 AI 客户端 system prompt"),
    ],
    "权重消融": [
        ("mradermacher/Qwen2.5-3B-Instruct-abliterated-GGUF", "消融权重 GGUF(3B)"),
        ("richardyoung/Qwen2.5-7B-Instruct-abliterated-GGUF", "消融权重 GGUF(7B)"),
    ],
    "无线网络": [
        ("aircrack-ng/aircrack-ng", "握手包爆破/PMKID 工具链"),
        ("vanhoefm/krackattacks", "KRACK 攻击研究"),
        ("hashcat/hashcat", "GPU 爆破引擎"),
        ("hcxtools/mightymightympc", "PMKID 抓取"),
    ],
    "逆向脱壳": [
        ("frida/frida", "动态插桩/脱壳/hook"),
        ("skylot/jadx", "APK 反编译"),
        ("iBotPeaches/Apktool", "APK 资源重建"),
        ("nationalSecurityAgency/ghidra", "反编译器"),
    ],
    "渗透红队": [
        ("sqlmapproject/sqlmap", "SQL 注入自动化"),
        ("BloodHoundAD/BloodHound", "域渗透路径分析"),
        ("fortra/impacket", "内网协议与票据"),
        ("roppersec/behinder", "Webshell 管理"),
    ],
    "CTF综合": [
        ("p4-team/ctf-wiki", "CTF 全套技巧wiki"),
        ("zaproxy/zaproxy", "Web 漏洞扫描"),
    ],
    "密钥推导": [
        ("routerkeygen/routerkeygenPC", "45 个厂商路由器默认密钥算法"),
    ],
    "持久化记忆": [
        ("AskTheWay/dsh-auto-memory", "DeepSeek Harness 记忆插件"),
    ],
}


def log(msg):
    print(msg, flush=True)


def token():
    try:
        t = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
        return t if t.startswith("gh") else None
    except Exception:
        return None


def api_get(path, params=None, raw=False, timeout=40):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    hdr = {"Accept": "application/vnd.github+json",
           "User-Agent": "pojia-fusion-ghf"}
    tk = token()
    if tk:
        hdr["Authorization"] = "Bearer " + tk
    req = urllib.request.Request(url, headers=hdr)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    r = op.open(req, timeout=timeout)
    data = r.read()
    if raw:
        return data
    return json.loads(data.decode("utf-8", "replace"))


def search(kw, limit=12):
    """三路检索: repos(name/description/readme) + code + topics"""
    res = {"repos": [], "code": [], "topics": []}
    toks = [t for t in re.split(r"\s+", kw) if len(t) > 1]
    # AND 语义会零命中 -> 用 2/3 词子集
    subs = []
    if len(toks) >= 2:
        subs.append(" ".join(toks[:2]))
        subs.append(" ".join(toks[-2:]))
    subs.append(kw)
    seen = set()
    for q in subs:
        try:
            j = api_get("/search/repositories", {"q": q, "sort": "stars", "order": "desc", "per_page": limit})
            for it in j.get("items", []):
                if it["full_name"] in seen:
                    continue
                seen.add(it["full_name"])
                res["repos"].append({"repo": it["full_name"], "stars": it["stargazers_count"],
                                     "pushed": it.get("pushed_at", "")[:10],
                                     "lang": it.get("language"), "url": it["html_url"],
                                     "desc": (it.get("description") or "")[:90]})
        except Exception as e:
            res.setdefault("errors", []).append("repos(%s): %s" % (q, str(e)[:70]))
        if len(res["repos"]) >= limit:
            break
    # code 检索(需 token)
    if token():
        try:
            j = api_get("/search/code", {"q": kw, "per_page": 8})
            for it in j.get("items", []):
                res["code"].append({"repo": it["repository"]["full_name"], "path": it["path"]})
        except Exception as e:
            res.setdefault("errors", []).append("code: %s" % str(e)[:70])
    # topic 检索
    for t in toks[:3]:
        try:
            j = api_get("/search/repositories", {"q": "topic:%s" % t, "sort": "stars", "per_page": 5})
            for it in j.get("items", []):
                if it["full_name"] in seen:
                    continue
                seen.add(it["full_name"])
                res["topics"].append({"repo": it["full_name"], "stars": it["stargazers_count"],
                                      "topic": t})
        except Exception:
            pass
    return res


def audit(repo, ref, path, out, note=""):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    line = "%s\trepo=%s\tref=%s\tpath=%s\tout=%s\t%s\n" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), repo, ref, path or "-", out or "-", note)
    with io.open(AUDIT, "a", encoding="utf-8") as f:
        f.write(line)


def pull(repo, ref="master", path=None, out=None, note=""):
    os.makedirs(CACHE, exist_ok=True)
    if path:
        # 单文件: 依次试镜像
        urls = [
            "https://ghfast.top/https://github.com/{repo}/raw/{ref}/{path}",
            "https://cdn.jsdelivr.net/gh/{repo}@{ref}/{path}",
            "https://raw.githubusercontent.com/{repo}/{ref}/{path}",
        ]
        data = None
        used = None
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "pojia-fusion-ghf"})
                op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                data = op.open(req, timeout=90).read()
                used = u
                break
            except Exception:
                continue
        if data is None:
            log("✗ 拉取失败: %s/%s" % (repo, path))
            return None
        dest = out or os.path.join(CACHE, repo.replace("/", "_"), path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        io.open(dest, "wb").write(data)
        audit(repo, ref, path, dest, note)
        log("✓ 已取 %s/%s -> %s  (%d 字节, sha=%s)" % (
            repo, path, dest, len(data), hashlib.sha256(data).hexdigest()[:12]))
        return dest
    # 整仓 zip
    dest_zip = out or os.path.join(CACHE, repo.replace("/", "_") + ".zip")
    urls = [
        "https://ghfast.top/https://github.com/{repo}/archive/refs/heads/{ref}.zip",
        "https://github.com/{repo}/archive/refs/heads/{ref}.zip",
    ]
    data = None
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "pojia-fusion-ghf"})
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            data = op.open(req, timeout=300).read()
            break
        except Exception:
            continue
    if data is None:
        log("✗ 整仓拉取失败: %s" % repo)
        return None
    io.open(dest_zip, "wb").write(data)
    d = os.path.join(CACHE, repo.replace("/", "_"))
    os.makedirs(d, exist_ok=True)
    try:
        with zipfile.ZipFile(_io.BytesIO(data)) as z:
            z.extractall(d)
    except Exception as e:
        log("  解压失败: %s" % e)
    audit(repo, ref, "(whole)", d, note)
    log("✓ 已取整仓 %s@%s -> %s  (%d 字节)" % (repo, ref, d, len(data)))
    return d


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("search"); s1.add_argument("kw"); s1.add_argument("--cat", default="")
    s2 = sub.add_parser("pull"); s2.add_argument("repo"); s2.add_argument("--ref", default="master")
    s2.add_argument("--path", default=""); s2.add_argument("--out", default=""); s2.add_argument("--note", default="")
    sub.add_parser("cat")
    sub.add_parser("audit")
    a = ap.parse_args()

    if a.cmd == "cat":
        for c, items in CATEGORIES.items():
            log("\n[%s]" % c)
            for repo, why in items:
                log("   %-52s %s" % (repo, why))
        return
    if a.cmd == "audit":
        if os.path.exists(AUDIT):
            log(io.open(AUDIT, encoding="utf-8").read())
        else:
            log("(暂无取用记录)")
        return
    if a.cmd == "search":
        if a.cat:
            log("\n=== 类别白名单 [%s] ===" % a.cat)
            for repo, why in CATEGORIES.get(a.cat, []):
                log("   %-52s %s" % (repo, why))
            log("")
        log("=== GitHub 三路检索: %s ===" % a.kw)
        r = search(a.kw)
        log("\n-- repos (by name/desc/readme) --")
        for x in sorted(r["repos"], key=lambda z: -z["stars"])[:12]:
            log("  %6d★ %-46s %s  %s" % (x["stars"], x["repo"], x["pushed"], x["desc"][:50]))
        if r.get("topics"):
            log("\n-- by topic --")
            for x in r["topics"][:8]:
                log("  %6d★ %-46s topic=%s" % (x["stars"], x["repo"], x["topic"]))
        if r.get("code"):
            log("\n-- code hits --")
            for x in r["code"][:8]:
                log("  %s :: %s" % (x["repo"], x["path"]))
        for e in r.get("errors", []):
            log("  ! %s" % e)
        return
    if a.cmd == "pull":
        pull(a.repo, a.ref, a.path or None, a.out or None, a.note)


if __name__ == "__main__":
    main()
