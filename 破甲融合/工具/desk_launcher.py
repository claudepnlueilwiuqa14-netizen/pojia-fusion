#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desk_launcher.py —— DeepSeek 破甲工作台启动器

组成（与 Electron 壳完全等价，跑的是同一份 DSH renderer 前端）:
    DSH host  →  dsh-purge agent + 本地破甲代理(8787) + gp-pojia 模型
    Chrome --app=<URL>  →  原生独立窗口（无地址栏），带 CDP 9444 供自动化测试接入
"""
import io, os, re, subprocess, sys, time

DSH = r"C:\Users\qq\AppData\Local\Programs\DeepSeek Harness"
EXE = os.path.join(DSH, "DeepSeek Harness.exe")
OUT = r"C:\Users\qq\SharedKB\rtl8812au-kali-lab"
LOG = os.path.join(OUT, "dsh_desk_host.log")
URLFILE = os.path.join(OUT, "dsh_desk_url.txt")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME):
    CHROME = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

HOST_ARGS = [
    EXE, "--expose-internals",
    os.path.join(DSH, r"resources\app\dsh\node_modules\@deepseek-ai\dsh-desktop-host\lib\index.js"),
    os.path.join(DSH, r"resources\app\dsh"),
    r"C:\Users\qq\.dsh\profiles\desktop",
    os.path.join(DSH, r"resources\runtime\primary-runtime"),
    os.path.join(DSH, r"resources\runtime\primary-runtime\dependencies\pnpm\bin\pnpm.mjs"),
    os.path.join(DSH, r"resources\runtime\bin"),
]

ENV = dict(os.environ)
ENV.update({
    "DSH_PROFILE": "desktop",
    "DSH_HOME": r"C:\Users\qq\.dsh",
    "RELAY_12300_API_KEY": "sk-RELAY_12300_API_KEY",
    "RELAY_SCXAI_API_KEY": "sk-RELAY_SCXAI_API_KEY",
})


def kill_old():
    subprocess.run(["taskkill", "/F", "/IM", "DeepSeek Harness.exe"],
                   capture_output=True)
    time.sleep(2)


def start_host():
    if os.path.exists(LOG):
        try:
            os.remove(LOG)
        except OSError:
            pass
    lf = open(LOG, "wb")
    p = subprocess.Popen(HOST_ARGS, stdout=lf, stderr=subprocess.STDOUT,
                         cwd=DSH, env=ENV, creationflags=0x08000000)  # CREATE_NO_WINDOW
    print("[host] pid=%d 日志=%s" % (p.pid, LOG), flush=True)
    return p


def wait_url(timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(2)
        try:
            txt = io.open(LOG, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = re.search(r"dsh web:\s*(http://\S+)", txt)
        if m:
            return m.group(1)
    return None


def open_window(url):
    profile = os.path.join(OUT, "chrome_dsh_profile")
    args = [CHROME, "--app=" + url,
            "--user-data-dir=" + profile,
            "--remote-debugging-port=9444",
            "--window-size=1500,940",
            "--no-first-run", "--no-default-browser-check"]
    subprocess.Popen(args, cwd=OUT)
    print("[window] 已开原生独立窗口, CDP=9444", flush=True)


def main():
    print("=" * 60)
    print("  DeepSeek 破甲工作台")
    print("  dsh-purge agent + 本地破甲代理 + gp-pojia 模型")
    print("=" * 60)
    kill_old()
    hp = start_host()
    url = wait_url()
    if not url:
        print("[!] host 未就绪, 日志尾部:")
        try:
            print(io.open(LOG, encoding="utf-8", errors="replace").read()[-1200:])
        except OSError:
            pass
        return 1
    io.open(URLFILE, "w", encoding="utf-8", newline="\n").write(url + "\n")
    print("[ok] UI: %s" % url, flush=True)
    open_window(url)
    print("\n工作台已开。关闭窗口即退出；日志: %s" % LOG)
    # 挂住，等 host 退出
    try:
        hp.wait()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
