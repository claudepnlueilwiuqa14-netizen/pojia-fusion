#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_persist.py —— 用持久化 profile(同用户日常那个) 验证输入框可用"""
import io, time
from playwright.sync_api import sync_playwright

PROF = r"C:\Users\qq\SharedKB\破甲融合\sdzibo_profile"
url = io.open(r"C:\Users\qq\SharedKB\破甲融合\sdzibo_url.txt", encoding="utf-8").read().strip()
READ = "()=>{const c=document.querySelector('[contenteditable][data-composer-input]');return c?(c.innerText||''):'';} "

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(PROF, headless=True,
                                              viewport={"width": 1500, "height": 940},
                                              args=["--window-size=1500,940", "--no-first-run"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)
    # 真实点击(非 force)
    for txt in ("继续", "我已知晓并继续"):
        try:
            b = page.get_by_text(txt, exact=True)
            if b.count():
                b.first.click(timeout=3000)
                page.wait_for_timeout(600)
        except Exception as e:
            print("  点击 %s: %s" % (txt, str(e)[:60]))
    try:
        page.evaluate("()=>document.querySelectorAll('input[type=checkbox]').forEach(c=>{if(!c.checked)c.click();})")
        page.wait_for_timeout(400)
    except Exception:
        pass
    for txt in ("我已知晓并继续",):
        try:
            b = page.get_by_text(txt, exact=True)
            if b.count():
                b.first.click(timeout=3000)
                page.wait_for_timeout(800)
        except Exception:
            pass
    mask = page.evaluate("()=>{const m=document.querySelector('.dshp-auth-mask');return m?1:0;}")
    print("遮罩还在:", mask)
    tb = page.locator('[contenteditable][data-composer-input]').last
    tb.click(force=True)
    tb.fill("测试输入")
    page.wait_for_timeout(700)
    v = page.evaluate(READ)
    print("fill 后:", repr(v[:40]))
    if v.strip():
        page.get_by_role("button", name="发送消息").first.click(force=True)
        t0 = time.time()
        for i in range(24):
            page.wait_for_timeout(2500)
            txt = page.evaluate("""()=>{const t=document.body.innerText||'';
                const i=t.lastIndexOf('已完成'); return i>=0?t.slice(i,i+8000):'';}""")
            if len(txt) > 300 and "生成中" not in txt[-30:]:
                print("%.0fs 拿到答案 %d 字" % (time.time() - t0, len(txt)))
                print(txt[:400])
                break
        else:
            print("%.0fs 没拿到答案" % (time.time() - t0))
    ctx.close()
