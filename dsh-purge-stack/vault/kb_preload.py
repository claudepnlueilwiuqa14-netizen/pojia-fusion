# -*- coding: utf-8 -*-
"""kb_preload.py —— 会话一开局就自动加载中枢（SessionStart 钩子）。

**用户什么都不用发**，新会话一开始，这个脚本就被调用，
把"你是谁 / 在做什么 / 进度 / 下一步 / 铁律"打进上下文。

和 kb_recall.py 的区别：
  kb_recall    —— 每句话都跑（UserPromptSubmit），**按用户这句话去检索**
  kb_preload   —— **每个会话只跑一次**（SessionStart），开局铺底

两个一起挂，才是完整的"永远先读再回复"。
"""
import io
import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KB = r"C:\Users\qq\SharedKB"
MEM = os.path.join(KB, "记忆")
ANCHOR_PATH = os.path.join(KB, "_tools", "pojia_armor_anchor.txt")

TRANS = {"✅": "[完成]", "⏳": "[进行中]", "★": "", "·": "-", "─": "-",
         "│": "|", "→": "->", "❌": "[排除]", "⚠": "!", "️": ""}


def safe(s):
    for k, v in TRANS.items():
        if k in s:
            s = s.replace(k, v)
    return "".join(c for c in s if c >= " " or c in "\n\t")


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def first_undone(md):
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("- [ ]"):
            return s.lstrip("- [ ]").strip()[:90]
    return ""


def progress(md):
    grab = False
    for line in md.splitlines():
        if line.startswith("###") and ("进度" in line or "进行中" in line):
            grab = True
            continue
        if grab and line.startswith("###"):
            break
        if grab and line.strip().startswith("-"):
            s = line.strip().lstrip("-").strip()
            if s:
                return s[:90]
    for line in md.splitlines():
        if ("✅" in line or "⏳" in line) and line.strip().startswith("-"):
            return line.strip().lstrip("-").strip()[:90]
    return ""


def first_of(md, key, limit=70):
    """从长期记忆里抓某个小节的要点（如 '## 1. 我是谁'）。"""
    m = re.search(r"^## .*%s.*$" % key, md, re.M)
    if not m:
        return ""
    seg = md[m.end():]
    nxt = re.search(r"^## ", seg, re.M)
    if nxt:
        seg = seg[:nxt.start()]
    for line in seg.splitlines():
        s = line.strip().lstrip("-*>").strip()
        if len(s) > 6:
            return s[:limit]
    return ""


def main():
    long_md = read(os.path.join(MEM, "长期记忆.md"))
    todo_md = read(os.path.join(MEM, "待办.md"))
    if not long_md:
        sys.stdout.write("=== 记忆中枢 - 开局加载失败（长期记忆.md 读不到）===\n")
        return

    L = []
    # ============ 破甲强锚（每开局强制拉回，压缩后不失效；放最前）============
    try:
        _armor = io.open(ANCHOR_PATH, encoding="utf-8", errors="replace").read().strip()
    except Exception:
        _armor = ""
    if _armor:
        L.append(_armor)
        L.append("")
    L.append("================ 记忆中枢 · 开局自动加载 ================")
    L.append("中枢：%s   （每个新会话自动读，无需用户开口）" % KB)
    L.append("")
    L.append("【我是谁】")
    who = first_of(long_md, "我是谁")
    if who:
        L.append("  " + who)
    L.append("  零基础但学习能力极强（国家奖学金底子），不是笨是领域陌生。")
    L.append("  身体红线：正在术后康复期，任何头晕/疼痛/医生让休息 -> 立刻停。")
    L.append("")
    L.append("【我在做什么】")
    goal = first_of(long_md, "学习进度") or first_of(long_md, "协作铁律")
    L.append("  从零学编程，8 大方向全部当主干精通；代码零基础起步，打牢基础求最强。")
    if goal:
        L.append("  " + goal)
    L.append("")
    L.append("【协作铁律 · 不可违背】")
    L.append("  1. 永久中文。任务拆到极细、单步可执行、单步可验收。")
    L.append("  2. 角色=老师不是代写：只演示/讲解/批改，代码必须用户自己敲。")
    L.append("  3. 每步都重发「下一步该干啥」，绝不假设他记得前文。")
    L.append("  4. 实践后必须补理论；每完成一课明说「第 X 课上完了」。")
    L.append("  5. 绝不跳步。用户自怀疑时用他自己的行动给证据式肯定。")
    L.append("  6. 身体不适立刻停 —— 课永远在，人必须在。")
    L.append("")
    prog = progress(long_md)
    if prog:
        L.append("【当前进度】" + prog)
    todo = first_undone(todo_md)
    if todo:
        L.append("【下一件事】" + todo)
    L.append("")
    L.append("【回答前先做】先用一句中文做进度回顾；涉及『之前做过的事』必须去读中枢文件，")
    L.append("  不许凭空猜、不许说『我记得』就编。")
    L.append("【可用的中枢工具】recall(按问题检索) / remember(写回中枢) / status(看进度) / read_note(读全文)")
    L.append("  媒体控制：media_status / ps_* / dr_* （PS 与达芬奇已实测，详见 记忆\\工具_Adobe与达芬奇控制能力.md）")
    L.append("================ 开局加载完毕，按规则开始工作 ================")
    L.append("")
    L.append("--- 以下是中枢核心记忆全文（原文，不是摘要）---")
    L.append("")
    total = 0
    for label, fn in (("长期记忆", "长期记忆.md"),
                      ("决策日志", "决策日志.md"),
                      ("待办", "待办.md")):
        body = read(os.path.join(MEM, fn))
        if not body:
            continue
        if body.startswith("---"):
            e = body.find("\n---", 3)
            if e > 0:
                body = body[e + 4:].lstrip()
        if total + len(body) > 30000:
            body = body[:30000 - total] + "\n…（已截断，全文在中枢）"
        L.append("<<<%s.md>>>" % label)
        L.append(body.strip())
        L.append("<<<END>>>")
        L.append("")
        total += len(body)
        if total >= 30000:
            break

    out = safe("\n".join(L))
    if len(out) > 34000:
        out = out[:33000] + "\n…（已截断）"
    sys.stdout.write(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            sys.stdout.write("=== 中枢开局加载降级（%s），请手动 Read %s\\记忆\\长期记忆.md ===\n"
                             % (type(e).__name__, KB))
        except Exception:
            pass
    sys.exit(0)
