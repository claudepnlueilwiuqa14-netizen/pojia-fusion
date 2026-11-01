# -*- coding: utf-8 -*-
"""
破甲 supervisor —— 代理的"看门狗的看门狗"

为什么需要它（2026-10-31 实测出来的掉线根因）：
  1. 代理进程崩了/被杀，guardian 要等 20s 才发现在拉起 —— 这 20s 内 DeepSeek 全部请求 502
  2. guardian 自己也会被会话回收（它是别人拉起的子进程），guardian 一死就彻底没人管了
  3. 崩溃现场没有任何日志，查不到是异常退出还是被人杀了

所以拆成两层：
  supervisor  = 盯着代理，崩了 1 秒内重启，并记录退出码/退出原因（写 proxy\crash.log）
  guardian    = 盯着 supervisor 的心跳；supervisor 不在了，用 explorer 把它拉起来（脱离会话）
  启动目录 vbs = 开机自启（用户会话里，谁都不依赖）

用法：
  python supervisor.py            # 前台跑（调试）
  python supervisor.py --once     # 只检查一次代理在不在，不常驻
"""
import json
import os
import subprocess
import sys
import time
import traceback
import urllib.request

HERE = r"C:\Users\qq\dsh-purge-stack"
PROXY = os.path.join(HERE, "proxy", "dsh_relay_proxy.py")
HEART = os.path.join(HERE, "proxy", "supervisor_heartbeat.json")
CRASH = os.path.join(HERE, "proxy", "crash.log")
LOG = os.path.join(HERE, "supervisor.log")
PORT = 8787

RESTART_BACKOFF = 2.0      # 代理崩了多久重启
HEARTBEAT_INTERVAL = 10    # 心跳写盘间隔
MAX_FAST_RESTARTS = 20     # 短时间内重启这么多次说明配置有问题，退避拉长


def log(*a):
    line = time.strftime("[%m-%d %H:%M:%S] ") + " ".join(str(x) for x in a)
    for p in (LOG, CRASH):
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def proxy_alive(timeout=3):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % PORT, timeout=timeout) as r:
            return bool(json.loads(r.read().decode("utf-8")).get("ok"))
    except Exception:
        return False


def write_heartbeat(proc, restarts):
    data = {
        "ts": time.time(),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "supervisor_pid": os.getpid(),
        "proxy_pid": proc.pid if proc and proc.poll() is None else None,
        "restarts": restarts,
    }
    tmp = HEART + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, HEART)
    except Exception:
        pass


_MUTEX = None


def acquire_singleton(name="Local\\PoJiaProxySupervisor_v1"):
    """单实例锁：Windows 命名互斥体。

    为什么必须有：计划任务每分钟触发一次 + 手动启动 + 开机自启，
    没有锁就会同时跑几十个 supervisor，它们互相 spawn 代理，
    代理又因为"端口已被占用"正常退出，supervisor 把它当成崩溃再重启 ——
    于是出现几十个 supervisor 和一条崩溃日志洪水（2026-10-31 实测）。
    """
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


def pythonw():
    pw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if os.path.isfile(pw):
        return pw
    return sys.executable


def spawn_proxy():
    """起一个代理子进程。用 pythonw（无窗口）且把输出重定向到文件，崩了能查。"""
    out = open(os.path.join(HERE, "proxy", "proxy_stdout.log"), "a", encoding="utf-8", buffering=1)
    err = open(os.path.join(HERE, "proxy", "proxy_stderr.log"), "a", encoding="utf-8", buffering=1)
    p = subprocess.Popen([pythonw(), PROXY], stdout=out, stderr=err,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log("proxy spawned pid=%s" % p.pid)
    return p


def main():
    if not acquire_singleton():
        log("已有 supervisor 在跑，本次退出（单实例锁）")
        return
    log("supervisor start pid=%s (single-instance ok)" % os.getpid())
    restarts = 0
    fast = 0
    proc = None
    last_beat = 0.0
    try:
        while True:
            try:
                # ---- 代理存活判定 ----
                if proc is None or proc.poll() is not None:
                    if proc is not None:
                        rc = proc.returncode
                        # rc==0 且 端口有人服务 = "已经有别的代理实例在跑"，不是崩溃
                        if rc == 0 and proxy_alive():
                            log("proxy 子进程正常退出(rc=0)，检测到已有代理实例在服务 -> 不重启")
                            proc = None
                            time.sleep(10)
                            continue
                        log("!! proxy EXITED rc=%s -> restart in %.1fs" % (rc, RESTART_BACKOFF))
                        try:
                            with open(CRASH, "a", encoding="utf-8") as f:
                                f.write("---- %s proxy 退出 rc=%s ----\n" %
                                        (time.strftime("%Y-%m-%d %H:%M:%S"), rc))
                        except Exception:
                            pass
                    time.sleep(RESTART_BACKOFF)
                    proc = spawn_proxy()
                    restarts += 1
                    fast += 1
                    if fast > MAX_FAST_RESTARTS:
                        time.sleep(min(60, RESTART_BACKOFF * fast))
                elif not proxy_alive():
                    # 进程在但 HTTP 不通（卡死/半死）—— 杀掉重起
                    log("!! proxy alive-but-not-serving -> kill & restart")
                    try:
                        proc.terminate()
                        time.sleep(1.5)
                        if proc.poll() is None:
                            proc.kill()
                    except Exception:
                        pass
                    proc = None
                    continue

                if fast > 0 and proxy_alive():
                    fast = 0

                now = time.time()
                if now - last_beat >= HEARTBEAT_INTERVAL:
                    last_beat = now
                    write_heartbeat(proc, restarts)
            except Exception:
                log("loop EXC " + traceback.format_exc()[:400])
            time.sleep(3)
    except KeyboardInterrupt:
        log("supervisor exit by KeyboardInterrupt")
    except Exception:
        log("supervisor FATAL " + traceback.format_exc()[:800])


if __name__ == "__main__":
    if "--once" in sys.argv:
        print("proxy_alive=%s" % proxy_alive())
        sys.exit(0)
    main()
