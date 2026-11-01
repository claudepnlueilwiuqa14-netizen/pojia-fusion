#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_switch.py —— 找到模型下拉并切到 gp-pojia"""
import io, re
from playwright.sync_api import sync_playwright

PROF = r"C:\Users\qq\SharedKB\破甲融合\sdzibo_profile"
url = io.open(r"C:\Users\qq\SharedKB\破甲融合\sdzibo_url.txt", encoding="utf-8").read().strip()

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(PROF, headless=True,
                                              viewport={"width": 1500, "height": 940})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)
    # 关弹窗
    for txt in ("继续", "我已知晓并继续"):
        try:
            b = pg.get_by_text(txt, exact=True)
            if b.count():
                b.first.click(timeout=2500); pg.wait_for_timeout(500)
        except Exception:
            pass
    pg.evaluate("()=>document.querySelectorAll('input[type=checkbox]').forEach(c=>{if(!c.checked)c.click();})")
    pg.wait_for_timeout(400)
    try:
        b = pg.get_by_text("我已知晓并继续", exact=True)
        if b.count():
            b.first.click(timeout=2500); pg.wait_for_timeout(800)
    except Exception:
        pass

    def model_now():
        return pg.evaluate("""()=>{
            const bs=Array.from(document.querySelectorAll('button[class*="trigger"]'));
            return bs.map(b=>(b.innerText||'').trim()).filter(t=>t&&t.length<40);
        }""")

    print("当前 trigger 列表:", model_now())
    # 点开模型下拉
    opened = False
    for sel in ['button[class*="_9r0rkG_trigger"]', 'button[class*="trigger"]']:
        loc = pg.locator(sel)
        n = loc.count()
        for i in range(n):
            try:
                t = (loc.nth(i).inner_text() or "").strip()
                if re.search(r"(deepseek|gp-|hy3|pool-|step-5|flash|pro)", t):
                    loc.nth(i).click(timeout=3000)
                    opened = True
                    print("已点开模型下拉:", t)
                    break
            except Exception:
                continue
        if opened:
            break
    pg.wait_for_timeout(1200)
    if not opened:
        print("没找到模型 trigger")
    # dump 下拉里的可见选项
    opts = pg.evaluate("""()=>{
        const V=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};
        const out=[];
        document.querySelectorAll('li,[role=option],[role=menuitem],[role=radio],button,div,span').forEach(e=>{
            if(!V(e)) return;
            const t=(e.innerText||'').trim();
            if(t && t.length<26 && /gp-|hy3|ds-|pool-|step-|deepseek/i.test(t)) out.push({t:t, tag:e.tagName, cls:String(e.className||'').slice(0,40)});
        });
        return Array.from(new Map(out.map(o=>[o.t+o.tag,o])).values()).slice(0,30);
    }""")
    print("下拉里可见的模型项:")
    for o in opts:
        print("   %-24s %-6s %s" % (o["t"][:24], o["tag"], o["cls"][:34]))
    # 点 gp-pojia
    done = False
    for sel in ['li', '[role=option]', '[role=menuitem]', '[role=radio]', 'button', 'div', 'span']:
        loc = pg.locator(sel).filter(has_text=re.compile(r"^\s*gp-pojia\s*$"))
        if loc.count():
            try:
                loc.first.click(timeout=3000)
                pg.wait_for_timeout(1500)
                done = True
                print("已点击 gp-pojia")
                break
            except Exception as e:
                print("点击失败:", str(e)[:60])
    pg.wait_for_timeout(800)
    print("切换后 trigger:", model_now())
    print("页面含 gp-pojia:", pg.evaluate("()=> (document.body.innerText||'').includes('gp-pojia')"))
    ctx.close()
