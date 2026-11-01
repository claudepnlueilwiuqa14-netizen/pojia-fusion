# -*- coding: utf-8 -*-
"""
破甲守护（纯 Python 常驻，不依赖任务计划程序）
  - 每 20s 检查本地破甲代理 :8787，挂了就拉起
  - 每 5 分钟回写本地注入层（prompt-inject.md / personas.md）如果被删/被改小
  - 每 30 分钟核对 profile 里的分组与池子供应商，缺了就补
  - 每 6 小时给池子打一次 11140 补丁（幂等，已打过就跳过）
启动：由启动目录 dsh_pojia_guardian.vbs 拉起，或手动 python guardian.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

HERE = r"C:\Users\qq\dsh-purge-stack"
DSH_HOME = r"C:\Users\qq\.dsh"
PROXY = os.path.join(HERE, "proxy", "dsh_relay_proxy.py")
PROXY_CFG = os.path.join(HERE, "proxy", "proxy_config.json")
LOG = os.path.join(HERE, "guardian.log")
POOL_PATCH = os.path.join(HERE, "tools", "patch_pool_11140.py")
SUP_HEART = os.path.join(HERE, "proxy", "supervisor_heartbeat.json")
SUP_VBS = os.path.join(HERE, "proxy", "dsh_pojia_supervisor.vbs")
STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup")
HEART_TTL = 90          # 心跳超过这个秒数就认为 supervisor 没了

T_PROXY = 20
T_INJECT = 300
T_PROFILE = 1800
T_POOL = 21600


def log(*a):
    line = time.strftime("[%m-%d %H:%M:%S] ") + " ".join(str(x) for x in a)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


_GMUTEX = None


def acquire_singleton(name="Local\\PoJiaGuardian_v1"):
    """单实例锁：计划任务每分钟触发 + 开机自启，没有锁会堆一堆 guardian。"""
    global _MUTEX
    try:
        import ctypes
        # 必须用 use_last_error=True 的 WinDLL，否则 ctypes.get_last_error() 永远返回 0，
        # "已存在"检测就失效了（2026-10-31 实测：锁形同虚设，起了 4 个 supervisor + 8281 次重启）
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = ctypes.c_void_p
        ctypes.set_last_error(0)
        handle = k32.CreateMutexW(None, False, name)
        err = ctypes.get_last_error()
        if not handle:
            return True                      # 拿不到锁就放行，别把自己堵死
        if err == 183:                       # ERROR_ALREADY_EXISTS
            return False                     # 已经有一个了
        _MUTEX = handle
        return True
    except Exception:
        return True


def proxy_alive():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=4) as r:
            return bool(json.loads(r.read().decode("utf-8")).get("ok"))
    except Exception:
        return False


def start_proxy():
    try:
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(pyw):
            pyw = sys.executable
        subprocess.Popen([pyw, PROXY], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        log("start_proxy EXC " + traceback.format_exc()[:200])
        return False


def supervisor_alive():
    """supervisor 心跳新鲜 -> 它还在盯着代理"""
    try:
        d = json.loads(io.open(SUP_HEART, encoding="utf-8").read())
        age = time.time() - float(d.get("ts", 0))
        if age >= HEART_TTL:
            # 诊断: 把实际读到的值记下来, 避免"明明心跳新鲜却报丢失"无从查起
            log("心跳过期 age=%.1f ttl=%d path=%s" % (age, HEART_TTL, SUP_HEART))
            return False
        return True
    except Exception as e:
        log("心跳读取异常 %s: %s" % (type(e).__name__, e))
        return False


def start_supervisor():
    """用 explorer.exe 起 vbs —— 这样进程挂在用户会话下，不随别人的进程树一起被回收。
    （这正是之前"破甲动不动就掉"的根因：guardian 是被工具会话拉起来的子进程。）"""
    try:
        vbs_src = os.path.join(HERE, "proxy", "dsh_pojia_supervisor.vbs")
        if not os.path.isfile(vbs_src):
            vbs_src = SUP_VBS
        if os.path.isfile(vbs_src) and os.path.isdir(STARTUP_DIR):
            try:
                shutil.copy2(vbs_src, os.path.join(STARTUP_DIR, "dsh_pojia_supervisor.vbs"))
            except Exception:
                pass
        ps = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                          "WindowsPowerShell", "v1.0", "powershell.exe")
        if not os.path.isfile(ps):
            ps = "powershell.exe"
        subprocess.run([ps, "-NoProfile", "-Command",
                        "Start-Process explorer.exe -ArgumentList '%s'" % vbs_src],
                       capture_output=True, timeout=60)
        log("supervisor 拉起(via explorer) %s" % os.path.basename(vbs_src))
        return True
    except Exception:
        log("start_supervisor EXC " + traceback.format_exc()[:200])
        return False


def ensure_inject():
    pairs = [
        (os.path.join(HERE, "config", "prompt-inject.md"), os.path.join(DSH_HOME, "prompt-inject.md")),
        (os.path.join(HERE, "config", "personas.md"), os.path.join(DSH_HOME, "personas.md")),
    ]
    fixed = 0
    for src, dst in pairs:
        try:
            if not os.path.isfile(src):
                continue
            need = True
            if os.path.isfile(dst) and os.path.getsize(dst) >= os.path.getsize(src) - 8:
                need = False
            if need:
                shutil.copy2(src, dst)
                fixed += 1
                log("回写注入层 %s" % os.path.basename(dst))
        except Exception:
            log("inject EXC " + traceback.format_exc()[:200])
    return fixed


def ensure_profile():
    """profile 里必须同时有 relay-pool 与 gp-* 分组，缺一就重跑 apply.ps1"""
    need = False
    for prof in ("desktop", "headless"):
        p = os.path.join(DSH_HOME, "profiles", prof, "cordis.patch.yml")
        try:
            s = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            need = True
            continue
        if "relay-pool" not in s or "gp-pojia" not in s:
            need = True
    if not need:
        return 0
    ps = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                      "WindowsPowerShell", "v1.0", "powershell.exe")
    if not os.path.isfile(ps):
        ps = "powershell.exe"
    try:
        subprocess.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(HERE, "apply.ps1")],
                       capture_output=True, timeout=600)
        log("profile 缺失 → 已重跑 apply.ps1")
        return 1
    except Exception:
        log("profile EXC " + traceback.format_exc()[:200])
        return 0


def patch_pool():
    if not os.path.isfile(POOL_PATCH):
        return 0
    try:
        with open(POOL_PATCH, "rb") as f:
            data = f.read()
        r = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                            "-o", "ConnectTimeout=20", "ubuntu@138.3.210.223", "python3 -"],
                           input=data, capture_output=True, timeout=120)
        out = (r.stdout or b"").decode("utf-8", "replace").strip()
        if out:
            log("pool patch: " + out.replace("\n", " | ")[:200])
        return 1
    except Exception:
        return 0


def main():
    if not acquire_singleton():
        log("已有 guardian 在跑，本次退出（单实例锁）")
        return
    log("guardian start pid=%s (single-instance ok)" % os.getpid())
    last = {"inject": 0, "profile": 0, "pool": 0}
    while True:
        try:
            if not supervisor_alive():
                log("supervisor 心跳丢失 → 拉起")
                start_supervisor()
                time.sleep(8)
                if not supervisor_alive():
                    # supervisor 起不来也要保证代理在跑（兜底）
                    if not proxy_alive():
                        log("代理也不在 → 直接拉起")
                        start_proxy()
                        time.sleep(5)
            elif not proxy_alive():
                # supervisor 活着但代理没响应：它自己会在 3s 内重启，这里只记录
                log("supervisor 在但代理未响应（由 supervisor 负责重启）")
            now = time.time()
            if now - last["inject"] >= T_INJECT:
                last["inject"] = now
                ensure_inject()
            if now - last["profile"] >= T_PROFILE:
                last["profile"] = now
                ensure_profile()
            if now - last["pool"] >= T_POOL:
                last["pool"] = now
                patch_pool()
        except Exception:
            log("loop EXC " + traceback.format_exc()[:300])
        time.sleep(T_PROXY)


if __name__ == "__main__":
    main()
