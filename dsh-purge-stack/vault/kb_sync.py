# -*- coding: utf-8 -*-
"""kb_sync.py —— 把各 AI 工具的会话记录汇进统一记忆中枢。

做三件事：
  1. 扫 WorkBuddy 的 .jsonl（projects/）→ 记录\\WorkBuddy\\YYYY-MM\\<会话>.md
  2. 扫 Codex 的 .jsonl（sessions/）    → 记录\\Codex\\YYYY-MM\\<会话>.md
  3. 写 记录\\同步日志.md（本次导入了什么、多少字）

只导出「对话正文」（user / assistant 的文本），
自动丢掉 reasoning / function_call / system / world_state 这些噪音。
增量：只导 mtime 变过的文件（状态记在 _tools\\_sync_state.json）。

用法:
  python kb_sync.py              # 增量，最近 7 天
  python kb_sync.py --days 30    # 拉长窗口
  python kb_sync.py --full       # 全量（慢，硬盘大）
  python kb_sync.py --days 3 --dry    # 只看会导多少，不写盘
"""
import os, io, re, json, time, sys, glob, datetime

KB = r"C:\Users\qq\SharedKB"
REC = os.path.join(KB, "记录")
STATE = os.path.join(KB, "_tools", "_sync_state.json")
LOGMD = os.path.join(REC, "同步日志.md")

SRC_WB = r"C:\Users\qq\.workbuddy\projects"
SRC_CX = r"C:\Users\qq\.codex\sessions"
SRC_DSH = r"C:\Users\qq\.dsh\sessions"      # DeepSeek Harness（2026-11-01 接入）

# 这些 type 一律丢掉
SKIP_TYPE = {
    "reasoning", "function_call", "function_call_result", "file-history-snapshot",
    "world_state", "turn_context", "event_msg", "thread_settings_applied",
    "token_count", "agent_reasoning", "agent_message_delta",
}
SKIP_ROLE = {"system", "developer", "tool"}


def log(*a):
    print(*a, flush=True)


def load_state():
    if os.path.isfile(STATE):
        try:
            return json.load(io.open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(s):
    io.open(STATE, "w", encoding="utf-8").write(
        json.dumps(s, ensure_ascii=False))


def clean(text, limit=None):
    """去掉系统提醒等噪音。"""
    if not text:
        return ""
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    t = re.sub(r"<skills_instructions>.*?</skills_instructions>", "", t, flags=re.S)
    t = re.sub(r"<environment_context>.*?</environment_context>", "", t, flags=re.S)
    t = re.sub(r"</?user_query>", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = t.strip()
    if limit and len(t) > limit:
        t = t[:limit] + "\n\n…（本条过长已截断，完整内容见原始 jsonl）"
    return t


def extract_text(payload):
    """从一条消息里抠出纯文本。"""
    c = payload.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for seg in c:
            if isinstance(seg, dict):
                v = seg.get("text")
                if v:
                    parts.append(v)
            elif isinstance(seg, str):
                parts.append(seg)
        return "\n".join(parts)
    return ""


def parse_workbuddy(path):
    """WorkBuddy jsonl: {type, role, timestamp, content} 或类似。"""
    out = []
    try:
        f = io.open(path, encoding="utf-8", errors="replace")
    except Exception:
        return out
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = str(d.get("type") or "")
        if t in SKIP_TYPE:
            continue
        role = str(d.get("role") or "")
        if role in SKIP_ROLE:
            continue
        msg = d.get("message") or d
        role = str(msg.get("role") or role)
        if role not in ("user", "assistant"):
            continue
        txt = clean(extract_text(msg) or msg.get("content") or "", 6000)
        if not txt:
            continue
        ts = d.get("timestamp") or msg.get("timestamp") or ""
        out.append((role, ts, txt))
    f.close()
    return out


def parse_codex(path):
    """Codex jsonl: {type:'response_item', payload:{type:'message', role, content:[{text}]}}"""
    out = []
    try:
        f = io.open(path, encoding="utf-8", errors="replace")
    except Exception:
        return out
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if str(d.get("type")) != "response_item":
            continue
        p = d.get("payload") or {}
        if str(p.get("type")) != "message":
            continue
        role = str(p.get("role") or "")
        if role not in ("user", "assistant"):
            continue
        txt = clean(extract_text(p), 6000)
        if not txt:
            continue
        out.append((role, d.get("timestamp") or "", txt))
    f.close()
    return out


def parse_dsh(path):
    """DSH(DeepSeek Harness) 会话: session.v4.jsonl.zstd

    行结构: {"type": ..., "seq": n, "time": ms_epoch, "data": {...}}
    关心的类型:
      user/message       —— 正文在 data.content[], 只有 source.kind=="user" 才是真人输入,
                            其余(time-context / runtime-context 等)是宿主塞的环境快照, 丢掉
      assistant/message  —— 正文在 data.message.content[]
      session/title      —— 会话标题
    返回 (msgs, title)
    """
    out = []
    title = ""
    try:
        import zstandard as zstd
        dctx = zstd.ZstdDecompressor()
        with open(path, "rb") as fh:
            raw = dctx.stream_reader(fh).read()
    except Exception:
        return out, title
    for line in raw.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except Exception:
            continue
        t = j.get("type")
        data = j.get("data") or {}
        if not isinstance(data, dict):
            continue
        stamp = ""
        ts = j.get("time")
        if ts:
            try:
                stamp = datetime.datetime.fromtimestamp(
                    float(ts) / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                stamp = ""
        if t == "session/title":
            title = str(data.get("title") or "")
            continue
        if t == "user/message":
            src = data.get("source") or {}
            if str(src.get("kind") or "") != "user":
                continue          # 宿主环境快照/时间上下文, 不是真人说的话
            txt = clean(extract_text(data) or "", 6000)
            if txt:
                out.append(("user", stamp, txt))
            continue
        if t == "assistant/message":
            msg = data.get("message") or {}
            txt = clean(extract_text(msg) or "", 6000)
            if txt:
                out.append(("assistant", stamp, txt))
            continue
        # agent/inbox/spliced 里的 user 与 user/message 重复, 直接跳过
    return out, title


def collect_dsh(pattern_root, out_dir, days, state, dry):
    """DSH: 一个会话一个目录, 会话文件是 zstd 压缩的 jsonl"""
    files = []
    if not os.path.isdir(pattern_root):
        return files, 0
    cutoff = time.time() - days * 86400 if days else 0
    for dp, dn, fn in os.walk(pattern_root):
        for f in fn:
            if not f.endswith(".jsonl.zstd"):
                continue
            p = os.path.join(dp, f)
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            if cutoff and mt < cutoff:
                continue
            files.append((mt, p))
    files.sort(reverse=True)
    n = 0
    for mt, p in files:
        key = os.path.abspath(p)
        sig = "%d_%d" % (int(mt * 1000), os.path.getsize(p))
        if state.get(key) == sig:
            continue
        msgs, title = parse_dsh(p)
        if not msgs:
            continue
        n += 1
        if dry:
            log("  [dry] %-58s %d 条" % (os.path.basename(p)[:58], len(msgs)))
            continue
        try:
            dt = datetime.datetime.fromtimestamp(mt)
        except Exception:
            dt = datetime.datetime.now()
        d = os.path.join(out_dir, dt.strftime("%Y-%m"))
        os.makedirs(d, exist_ok=True)
        parent = os.path.basename(os.path.dirname(p))
        sid = dt.strftime("%Y-%m-%d_%H%M") + "_" + parent[-8:]
        dest = os.path.join(d, sid + ".md")
        io.open(dest, "w", encoding="utf-8").write(render(msgs, "DeepSeek", p, sid, title))
        state[key] = sig
        log("  导出 %-58s %d 条" % (sid[:58], len(msgs)))
    return files, n


def render(msgs, tool, src, sid, title=None):
    L = []
    L.append("# %s 会话 · %s" % (tool, sid))
    L.append("")
    L.append("- 来源：`%s`" % src)
    if title:
        L.append("- 会话标题：`%s`" % title)
    L.append("- 消息数：%d" % len(msgs))
    L.append("- 导出时间：%s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    L.append("")
    L.append("---")
    L.append("")
    who = {"user": "我", "assistant": "助手"}
    for role, ts, txt in msgs:
        stamp = ""
        if ts:
            stamp = " `%s`" % str(ts)[:19].replace("T", " ")
        L.append("### %s%s" % (who.get(role, role), stamp))
        L.append("")
        L.append(txt)
        L.append("")
    return "\n".join(L)


def collect(pattern_root, parser, tool, out_dir, days, state, dry):
    files = []
    if not os.path.isdir(pattern_root):
        return files, 0, 0
    cutoff = time.time() - days * 86400
    for dp, dn, fn in os.walk(pattern_root):
        for f in fn:
            if not f.endswith(".jsonl"):
                continue
            p = os.path.join(dp, f)
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            if days and mt < cutoff:
                continue
            files.append((mt, p))
    files.sort(reverse=True)

    n = 0
    total_bytes = 0
    for mt, p in files:
        key = os.path.abspath(p)
        sig = "%d_%d" % (int(mt * 1000), os.path.getsize(p))
        if state.get(key) == sig:
            continue
        msgs = parser(p)
        if not msgs:
            continue
        n += 1
        if dry:
            log("  [dry] %-58s %d 条" % (os.path.basename(p)[:58], len(msgs)))
            continue
        try:
            dt = datetime.datetime.fromtimestamp(mt)
        except Exception:
            dt = datetime.datetime.now()
        d = os.path.join(out_dir, dt.strftime("%Y-%m"))
        os.makedirs(d, exist_ok=True)
        sid = os.path.splitext(os.path.basename(p))[0]
        if tool == "WorkBuddy":
            sid = dt.strftime("%Y-%m-%d_%H%M") + "_" + sid[:8]
        else:
            sid = dt.strftime("%Y-%m-%d_%H%M") + "_" + sid[-8:]
        dest = os.path.join(d, sid + ".md")
        io.open(dest, "w", encoding="utf-8").write(render(msgs, tool, p, sid))
        total_bytes += len(msgs) * 40
        state[key] = sig
        log("  导出 %-58s %d 条" % (sid[:58], len(msgs)))
    return files, n, total_bytes


def collect_threads(pattern_root, out_dir, days, state, dry):
    """Codex：同一 thread 被切成很多 rollout，按 thread 合并成一份。"""
    if not os.path.isdir(pattern_root):
        return 0
    cutoff = time.time() - days * 86400 if days else 0
    groups = {}
    for dp, dn, fn in os.walk(pattern_root):
        for f in fn:
            if not f.endswith(".jsonl"):
                continue
            p = os.path.join(dp, f)
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            if cutoff and mt < cutoff:
                continue
            tid = None
            for seg in f.replace(".jsonl", "").split("-"):
                if len(seg) == 8 and all(c in "0123456789abcdefABCDEF" for c in seg):
                    tid = seg
                    break
            key = tid or os.path.splitext(f)[0]
            groups.setdefault(key, []).append((mt, p))
    n = 0
    for key, items in sorted(groups.items()):
        items.sort()
        msgs = []
        for mt, p in items:
            sig = "%d_%d" % (int(mt * 1000), os.path.getsize(p))
            if state.get(os.path.abspath(p)) == sig:
                continue
            msgs += [(r, t, x, p) for (r, t, x) in parse_codex(p)]
            state[os.path.abspath(p)] = sig
        if not msgs:
            continue
        n += 1
        newest = items[-1][0]
        try:
            dt = datetime.datetime.fromtimestamp(newest)
        except Exception:
            dt = datetime.datetime.now()
        if dry:
            log("  [dry] thread %-10s %d 个 rollout → %d 条消息"
                % (key[:10], len(items), len(msgs)))
            continue
        d = os.path.join(out_dir, dt.strftime("%Y-%m"))
        os.makedirs(d, exist_ok=True)
        sid = dt.strftime("%Y-%m-%d_%H%M") + "_thread" + key[:8]
        dest = os.path.join(d, sid + ".md")
        L = ["# Codex 会话 · thread %s" % key, "",
             "- 合并 %d 个 rollout 片段" % len(items),
             "- 消息数：%d" % len(msgs),
             "- 最后活动：%s" % dt.strftime("%Y-%m-%d %H:%M:%S"),
             "- 导出时间：%s"
             % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", "---", ""]
        who = {"user": "我", "assistant": "助手"}
        for role, ts, txt, _src in msgs:
            stamp = (" `%s`" % str(ts)[:19].replace("T", " ")) if ts else ""
            L.append("### %s%s" % (who.get(role, role), stamp))
            L.append("")
            L.append(txt)
            L.append("")
        io.open(dest, "w", encoding="utf-8").write("\n".join(L))
        log("  合并 thread %-10s %2d rollout → %3d 条 → %s"
            % (key[:10], len(items), len(msgs), sid))
    return n


def main():
    args = sys.argv[1:]
    days = 7
    full = "--full" in args
    dry = "--dry" in args
    if full:
        days = 0
    for a in args:
        if a.startswith("--days"):
            try:
                days = int(a.split("=")[1])
            except Exception:
                pass
    if full:
        days = 0

    log("=== kb_sync 开始（%s）===" %
        ("全量" if full else "最近 %d 天" % days))
    state = load_state()

    for tool, root, parser in (("WorkBuddy", SRC_WB, parse_workbuddy),):
        out_dir = os.path.join(REC, tool)
        os.makedirs(out_dir, exist_ok=True)
        files, n, b = collect(root, parser, tool, out_dir, days, state, dry)
        log("%-10s 扫到 %d 个 jsonl，本次导出 %d 个" % (tool, len(files), n))

    cx_dir = os.path.join(REC, "Codex")
    os.makedirs(cx_dir, exist_ok=True)
    cn = collect_threads(SRC_CX, cx_dir, days, state, dry)
    log("%-10s 按 thread 合并导出 %d 个" % ("Codex", cn))

    ds_dir = os.path.join(REC, "DeepSeek")
    os.makedirs(ds_dir, exist_ok=True)
    dsf, dn_ = collect_dsh(SRC_DSH, ds_dir, days, state, dry)
    log("%-10s 扫到 %d 个会话，本次导出 %d 个" % ("DeepSeek", len(dsf), dn_))

    if not dry:
        save_state(state)
        # 同步日志
        os.makedirs(REC, exist_ok=True)
        prev = ""
        if os.path.isfile(LOGMD):
            prev = io.open(LOGMD, encoding="utf-8").read()
        entry = ("\n## %s · %s\n- 窗口：WorkBuddy %d 个 / Codex %d 个 / DeepSeek %d 个\n- 状态：完成\n\n"
                 % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "全量" if full else "最近 %d 天" % days, n, cn, dn_))
        if entry.strip() not in prev:
            if "# 同步日志" not in prev:
                prev = ("# 同步日志\n\n> `kb_sync.py` 每次运行追加一条。"
                        "记录各工具会话导出情况。\n")
            io.open(LOGMD, "w", encoding="utf-8").write(prev + entry)
        log("已写 %s" % LOGMD)
    log("=== 完成 ===")


if __name__ == "__main__":
    main()
