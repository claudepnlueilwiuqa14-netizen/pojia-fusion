#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sdzibo_launcher.py —— SDzibo 复刻版客户端启动器

完全复刻官方 DeepSeek 桌面端：
    同 host  +  同 profile  +  同 dsh-purge agent  +  同 gp-pojia 模型  +  同 DSH 前端代码
只改两样：窗口标题 → SDzibo，窗口图标 → 八卦图（用 CDP 注入，**不改 DSH 任何文件**）

用法:
  python sdzibo_launcher.py                # 起 host + 开窗口 + 注入品牌
  python sdzibo_launcher.py --no-window    # 只起 host
"""
import base64, io, os, re, subprocess, sys, time

DSH = r"C:\Users\qq\AppData\Local\Programs\DeepSeek Harness"
EXE = os.path.join(DSH, "DeepSeek Harness.exe")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME):
    CHROME = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "sdzibo_host.log")
ICON_B64_FILE = os.path.join(HERE, "assets", "sdzibo_favicon_b64.txt")
CDP_PORT = 9444

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
    subprocess.run(["taskkill", "/F", "/IM", "DeepSeek Harness.exe"], capture_output=True)
    time.sleep(2)


def start_host():
    lf = open(LOG, "wb")
    p = subprocess.Popen(HOST_ARGS, stdout=lf, stderr=subprocess.STDOUT, cwd=DSH, env=ENV,
                         creationflags=0x08000000)
    print("[host] pid=%d" % p.pid, flush=True)
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
    prof = os.path.join(HERE, "sdzibo_profile")
    subprocess.Popen([CHROME, "--app=" + url,
                      "--user-data-dir=" + prof,
                      "--remote-debugging-port=%d" % CDP_PORT,
                      "--window-size=1500,940",
                      "--no-first-run", "--no-default-browser-check",
                      "--disable-features=Translate,OptimizationGuideModelDownloading"],
                     cwd=HERE)
    print("[window] 已开原生窗口 (CDP %d)" % CDP_PORT, flush=True)


def inject_brand():
    """用 CDP 注入标题与图标(不改 DSH 任何文件)"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("[inject] playwright 不可用:", e)
        return False
    b64 = io.open(ICON_B64_FILE, encoding="utf-8").read().strip()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.connect_over_cdp("http://127.0.0.1:%d" % CDP_PORT)
            ctx = br.contexts[0] if br.contexts else br.new_context()
            page = None
            for p in ctx.pages:
                if "127.0.0.1" in (p.url or ""):
                    page = p
                    break
            if page is None:
                print("[inject] 未找到 DSH 页面")
                return False
            page.bring_to_front()
            # 持续注入(页面可能重载)
            # 持续覆盖: DSH 前端会自己改 window.title(会话标题 - DeepSeek Harness),
            # 所以用定时器 + MutationObserver 一直按住 'SDzibo'
            page.evaluate("""(b64) => {
                if (window.__sdzBrand) return;
                const setT = () => {
                  try {
                    if (document.title !== 'SDzibo') document.title = 'SDzibo';
                    let l = document.querySelector("link[rel~='icon']");
                    if (!l) { l = document.createElement('link'); l.rel = 'icon'; document.head.appendChild(l); }
                    l.type = 'image/png';
                    if (!l.href.startsWith('data:image/png;base64,')) l.href = 'data:image/png;base64,' + b64;
                  } catch (e) {}
                };
                setT();
                setInterval(setT, 400);
                const mo = new MutationObserver(setT);
                mo.observe(document.head, { childList: true, subtree: true, characterData: true });
                window.__sdzBrand = true;
            }""", b64)
            time.sleep(1.0)
            title = page.title()
            br.close()
            print("[inject] 标题已设为 %r, 八卦图标已注入" % title, flush=True)
            return title == "SDzibo"
    except Exception as e:
        print("[inject] 失败:", str(e)[:150])
        return False


def main():
    print("=" * 64)
    print("  SDzibo · 复刻版客户端")
    print("  同 host / 同 profile / 同 dsh-purge agent / 同 gp-pojia 模型 / 同 DSH 前端")
    print("  仅改: 窗口标题 = SDzibo, 窗口图标 = 八卦图")
    print("=" * 64)
    kill_old()
    hp = start_host()
    url = wait_url()
    if not url:
        print("[!] host 未就绪, 看", LOG)
        return 1
    print("[ok] DSH host:", url, flush=True)
    io.open(os.path.join(HERE, "sdzibo_url.txt"), "w", encoding="utf-8", newline="\n").write(url + "\n")
    if "--no-window" in sys.argv:
        return 0
    open_window(url)
    time.sleep(6)
    inject_brand()
    print("\nSDzibo 窗口已就绪。关闭窗口即退出。")
    try:
        hp.wait()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
