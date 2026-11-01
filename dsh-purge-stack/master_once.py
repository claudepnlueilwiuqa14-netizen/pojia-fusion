# -*- coding: utf-8 -*-
"""
【破甲一键到底】把 dsh-purge-stack 所有改动合并成一次执行。
骨架照抄 pojia-next/master_once.py（RUN_ME_ONCE.bat 那个），四条铁律：
  1) 自提权：写 Program Files 下的宿主需要管理员，不够就 RunAs 重启自己
  2) 幂等：可反复运行，不重复添加、不改坏
  3) 守护：guardian.py 常驻自愈（不走 schtasks，纯 Python + 启动目录）
  4) 落盘强校验：只有**从磁盘回读**到目标值才算成功 —— 内存改好 / 退出码 0 / 日志打了"已改" 全不作数

用法：
  python master_once.py            # 一键到底
  python master_once.py --test     # 一键到底 + 最后跑通性测试
  python master_once.py --no-host  # 不动宿主进程（补丁层仍需重启宿主生效）
"""
import ctypes
import datetime
import io
import json
import os
import subprocess
import sys
import time
import traceback

HERE = r"C:\Users\qq\dsh-purge-stack"
DSH_HOME = r"C:\Users\qq\.dsh"
HOST_DIR = r"C:\Users\qq\AppData\Local\Programs\DeepSeek Harness"
PROXY = os.path.join(HERE, "proxy", "dsh_relay_proxy.py")
GUARDIAN = os.path.join(HERE, "guardian.py")
APPLY = os.path.join(HERE, "apply.ps1")
VERIFY = os.path.join(HERE, "verify.ps1")
PROXY_CFG = os.path.join(HERE, "proxy", "proxy_config.json")
LOG = os.path.join(HERE, "master_once.log")

# 需要管理员才能写的地方（落盘校验用的探针）
HOST_PKG = os.path.join(HOST_DIR, "resources", "app", "package.json")

fails = []


def log(*a):
    line = " ".join(str(x) for x in a)
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def step(name):
    log("")
    log("-" * 62)
    log(name)


def run(cmd, timeout=900, shell=False):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, shell=shell)
        out = (r.stdout or b"").decode("utf-8", "replace")
        err = (r.stderr or b"").decode("utf-8", "replace")
        return r.returncode, out, err
    except Exception:
        return 1, "", traceback.format_exc()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# ---------- 0. 自提权 ----------
log("")
log("=" * 62)
log("破甲一键到底 开始  %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
log("解释器: %s" % sys.executable)

if "--elevated" not in sys.argv and not is_admin():
    log("[权限] 非管理员 → 以 RunAs 提权重启自己")
    params = " ".join('"%s"' % a for a in [os.path.abspath(__file__), "--elevated"] + sys.argv[1:])
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    if rc <= 32:
        log("!! 提权启动失败（UAC 被拒？）rc=%s —— 继续以当前权限跑，宿主补丁层可能失败" % rc)
    else:
        log("已提权重启，本进程结束")
        sys.exit(0)
else:
    log("[权限] 已具备管理员权限 ✅" if is_admin() else "[权限] 当前非管理员（--elevated 已尝试过）")

# ---------- 1. 凭据 + 注入层 + 供应商/分组 + 宿主补丁（复用 apply.ps1，幂等） ----------
step("[1/6] apply.ps1（凭据 / 注入层 / 代理 / 供应商 / 插件 / 宿主补丁）")
ps = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                  "WindowsPowerShell", "v1.0", "powershell.exe")
if not os.path.isfile(ps):
    ps = "powershell.exe"
code, out, err = run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", APPLY], timeout=900)
for line in (out or "").splitlines():
    if line.strip():
        log("      " + line.rstrip())
if code != 0:
    fails.append("apply.ps1 退出码=%s" % code)
    log("      stderr: " + (err or "")[:400])

# ---------- 2. 本地代理在跑 ----------
step("[2/6] 本地破甲代理 :8787")
try:
    import urllib.request
    alive = False
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=4) as r:
            alive = bool(json.loads(r.read().decode("utf-8")).get("ok"))
    except Exception:
        alive = False
    if alive:
        log("      代理已在运行 ✅")
    else:
        log("      未运行 → 启动 guardian（它会起代理并常驻自愈）")
        if os.path.isfile(GUARDIAN):
            subprocess.Popen([sys.executable, GUARDIAN],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x00000008)  # DETACHED_PROCESS
            time.sleep(6)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=5) as r:
                    alive = bool(json.loads(r.read().decode("utf-8")).get("ok"))
            except Exception:
                alive = False
        if not alive:
            fails.append("本地代理未起来")
except Exception:
    fails.append("代理检查异常")
    log(traceback.format_exc())

# ---------- 3. 开机自启（启动目录，不用 schtasks） ----------
step("[3/6] 开机自启（启动目录 vbs → guardian）")
try:
    startup = os.path.join(os.environ.get("APPDATA", ""),
                           r"Microsoft\Windows\Start Menu\Programs\Startup")
    if startup and os.path.isdir(startup):
        vbs = os.path.join(startup, "dsh_pojia_guardian.vbs")
        # 优先用系统 Python313（稳定、不会被会话回收），找不到再退回当前解释器
        cands = [r"C:\Users\qq\AppData\Local\Programs\Python\Python313\pythonw.exe",
                 r"C:\Python310\pythonw.exe",
                 os.path.join(os.path.dirname(sys.executable), "pythonw.exe"),
                 sys.executable]
        pyw = next((c for c in cands if os.path.isfile(c)), sys.executable)
        log("      守护解释器: %s" % pyw)
        with io.open(vbs, "w", encoding="mbcs") as f:
            f.write('Set sh = CreateObject("WScript.Shell")\n')
            f.write('sh.Run """%s"" ""%s""", 0, False\n' % (pyw, GUARDIAN))
        log("      已写入 %s" % vbs)
    else:
        fails.append("启动目录不存在")
except Exception:
    fails.append("自启写入失败")
    log(traceback.format_exc())

# ---------- 4. 池子（自己的额度反代）体检 + 11140 补丁 ----------
step("[4/6] 额度池 138.3.210.223:8788")
try:
    with urllib.request.urlopen("https://wenzetongxun.com/relay-legacy/healthz", timeout=15) as r:
        h = json.loads(r.read().decode("utf-8"))
    log("      healthz: %s" % h)
    if h.get("healthy", 0) < 1:
        fails.append("池子无健康账号")
except Exception as e:
    log("      healthz 检查失败: %s" % str(e)[:120])

patch = os.path.join(HERE, "tools", "patch_pool_11140.py")
if os.path.isfile(patch):
    try:
        with open(patch, "rb") as pf:
            pdata = pf.read()
        r = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                            "-o", "ConnectTimeout=20", "ubuntu@138.3.210.223", "python3 -"],
                           input=pdata, capture_output=True, timeout=180)
        out = (r.stdout or b"").decode("utf-8", "replace").strip()
        log("      池子 11140 补丁: %s" % (out.replace("\n", " | ")[:200] if out else "无输出(可能已打过)"))
    except Exception:
        log("      池子补丁 ssh 失败(不影响本地): %s" % str(sys.exc_info()[1])[:120])

# ---------- 4.5 注册守护链计划任务（防掉线） ----------
step("[4.5/6] 注册守护链计划任务")
_reg = os.path.join(STACK, "tools", "register_tasks.ps1")
if os.path.isfile(_reg):
    code, out, err = run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _reg], timeout=180)
    for line in (out or "").splitlines():
        if line.strip():
            log("      " + line.strip())
else:
    log("      缺少 tools/register_tasks.ps1")

# ---------- 5. 重启宿主（补丁层 + 新配置生效） ----------
step("[5/6] 重启 DeepSeek Harness")
if "--no-host" in sys.argv:
    log("      --no-host，跳过")
else:
    code, out, err = run([ps, "-NoProfile", "-Command",
                          "Get-Process | Where-Object { $_.ProcessName -match 'DeepSeek' } | Stop-Process -Force; "
                          "Start-Sleep -Seconds 2; "
                          "Start-Process explorer.exe -ArgumentList '%s\\DeepSeek Harness.exe'; "
                          "Start-Sleep -Seconds 14; "
                          "(Get-Process | Where-Object { $_.ProcessName -match 'DeepSeek' } | Measure-Object).Count"
                          % HOST_DIR], timeout=240)
    cnt = (out or "").strip().splitlines()[-1:] or ["?"]
    log("      宿主进程数: %s" % (cnt[0] if cnt else "?"))
    if not (cnt and cnt[0].strip().isdigit() and int(cnt[0].strip()) > 0):
        fails.append("宿主未拉起")

# ---------- 6. 落盘强校验（从磁盘回读） ----------
step("[6/6] 落盘强校验（从磁盘回读，不是内存值）")
checks = []


def read(path):
    try:
        return io.open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return None


# 6.1 注入层落盘
for name, p in [("prompt-inject.md", os.path.join(DSH_HOME, "prompt-inject.md")),
                ("personas.md", os.path.join(DSH_HOME, "personas.md"))]:
    ok = os.path.isfile(p) and os.path.getsize(p) > 100
    checks.append(("注入层 " + name, ok))

# 6.2 profile 落盘：分组 + 池子供应商 + 默认模型
for prof in ("desktop", "headless"):
    p = os.path.join(DSH_HOME, "profiles", prof, "cordis.patch.yml")
    s = read(p) or ""
    ok = ("relay-pool" in s) and ("gp-pojia" in s) and ("agent-default-model" in s)
    checks.append(("profile %s (分组+池子+默认模型)" % prof, ok))

# 6.3 代理配置落盘：system=none / 分组 / 11140 重试
cfg = read(PROXY_CFG)
try:
    c = json.loads(cfg) if cfg else {}
except Exception:
    c = {}
pol = c.get("policy", {})
checks.append(("代理 system=none", pol.get("system") == "none"))
checks.append(("代理 分组>=5", len(pol.get("groups", {})) >= 5))
checks.append(("代理 11140 重试", 11140 in (pol.get("retry_on_codes", {}) or {}).get("codes", [])))
checks.append(("代理 池子上游", "relay-pool" in (c.get("upstream", {}) or {})))

# 6.4 宿主补丁层：package.json 里 dshMandatoryUpdatePolicy 必须已被移除
pkg = read(HOST_PKG)
checks.append(("宿主强制更新已摘除",
               pkg is not None and "dshMandatoryUpdatePolicy" not in pkg))

bad = []
for name, ok in checks:
    log("   %-38s %s" % (name, "OK" if ok else "!! 未落盘"))
    if not ok:
        bad.append(name)
if bad:
    fails.append("落盘校验未过: " + ", ".join(bad))

# ---------- 可选：通性测试 ----------
if "--test" in sys.argv:
    step("[额外] 通性测试 verify.ps1")
    code, out, err = run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", VERIFY], timeout=1800)
    for line in (out or "").splitlines():
        if "[PASS]" in line or "[FAIL]" in line or "RESULT" in line or "SMOKE" in line:
            log("      " + line.rstrip())
    if "[FAIL]" in (out or ""):
        fails.append("通性测试有 FAIL")

# ---------- 收尾 ----------
log("")
log("=" * 62)
if fails:
    log("结果：有步骤未达成")
    for f in fails:
        log("  !! " + f)
else:
    log("结果：全部成功（已验证落盘）✅")
log("日志: %s" % LOG)
log("=" * 62)
sys.exit(1 if fails else 0)
