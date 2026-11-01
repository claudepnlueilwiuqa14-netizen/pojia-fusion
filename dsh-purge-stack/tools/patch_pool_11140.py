# -*- coding: utf-8 -*-
"""在服务器上给 pojia-pool 打补丁:
   1) 11140(账号被限制) 判定为 retriable -> 自动换下一个号, 而不是直接把错误甩给调用方
   2) 被限制的号进 6 小时冷却, 后续优先走健康号
   3) 幂等: 已打过就不重复打
"""
import io, os, re, shutil, time, sys

P = "/opt/pojia-pool/pool_server_srv.js"
BAK = P + ".bak.11140." + time.strftime("%Y%m%d-%H%M%S")

src = io.open(P, encoding="utf-8").read()

if "code === 11140" in src:
    print("ALREADY_PATCHED")
    sys.exit(0)

OLD = "const retriable = rateLimited || st >= 500 || code === 11102 || /频率|额度|超出|rate limit|too many/i.test(body);"
NEW = ("const banned = code === 11140;\n"
       "        if (banned) { cooldown.set(acc.uid, Date.now() + 6 * 3600 * 1000); }\n"
       "        const retriable = rateLimited || banned || st >= 500 || code === 11102 || /频率|额度|超出|rate limit|too many/i.test(body);")

if OLD not in src:
    # 宽松匹配: 只认前半段, 保留原表达式尾部
    m = re.search(r"[ \t]*const retriable = rateLimited \|\| st >= 500.*?;\n", src)
    if not m:
        print("PATCH_ANCHOR_NOT_FOUND")
        sys.exit(2)
    line = m.group(0)
    indent = re.match(r"[ \t]*", line).group(0)
    old_line = line.strip()
    new_line = ("const banned = code === 11140;\n"
                + indent + "if (banned) { cooldown.set(acc.uid, Date.now() + 6 * 3600 * 1000); }\n"
                + indent + old_line.replace("= rateLimited ||", "= rateLimited || banned ||"))
    src = src.replace(line, new_line + "\n")
    print("PATCHED_FUZZY")
else:
    src = src.replace(OLD, NEW)
    print("PATCHED_EXACT")

shutil.copy2(P, BAK)
io.open(P, "w", encoding="utf-8").write(src)
print("BACKUP:", BAK)

# 语法检查
r = os.popen("/usr/local/bin/node --check " + P + " 2>&1").read().strip()
print("SYNTAX:", r if r else "OK")
sys.exit(0 if not r else 3)
