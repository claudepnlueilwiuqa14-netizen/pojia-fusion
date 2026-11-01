#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_composer.py —— 单独验证: 关弹窗后输入框能否被输入"""
import io, re, sys
from playwright.sync_api import sync_playwright

src = io.open(r"C:\Users\qq\SharedKB\破甲融合\工具\sdzibo_e2e.py", encoding="utf-8").read()
import dismiss_js
HARD = dismiss_js.HARD
url = io.open(r"C:\Users\qq\SharedKB\破甲融合\sdzibo_url.txt", encoding="utf-8").read().strip()
READ = "()=>{const c=document.querySelector('[contenteditable][data-composer-input]');return c?(c.innerText||''):'';} "

with sync_playwright() as pw:
    br = pw.chromium.launch(headless=True)
    ctx = br.new_context(viewport={"width": 1500, "height": 940})
    pg = ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)
    st = pg.evaluate(HARD)
    print("dismiss 结果:", st)
    tb = pg.locator('[contenteditable][data-composer-input]').last
    tb.click(force=True)
    tb.fill("测试输入")
    pg.wait_for_timeout(600)
    print("fill 后:", repr(pg.evaluate(READ)[:40]))
    if pg.evaluate(READ).strip():
        pg.get_by_role("button", name="发送消息").first.click(force=True)
        import time
        t0 = time.time()
        for i in range(24):
            pg.wait_for_timeout(2500)
            txt = pg.evaluate("""()=>{const t=document.body.innerText||'';
                const i=t.lastIndexOf('已完成'); return i>=0?t.slice(i,i+8000):'';}""")
            if len(txt) > 300 and "生成中" not in txt[-30:]:
                print("%.0fs 拿到答案 %d 字" % (time.time() - t0, len(txt)))
                print(txt[:500])
                break
        else:
            print("%.0fs 没拿到答案" % (time.time() - t0))
    br.close()
