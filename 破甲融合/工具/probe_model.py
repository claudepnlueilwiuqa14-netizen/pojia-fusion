#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_model.py —— 找出 DSH 前端的模型选择器, 并验证切换到 gp-pojia"""
import io, time
from playwright.sync_api import sync_playwright

PROF = r"C:\Users\qq\SharedKB\破甲融合\sdzibo_profile"
url = io.open(r"C:\Users\qq\SharedKB\破甲融合\sdzibo_url.txt", encoding="utf-8").read().strip()

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(PROF, headless=True,
                                              viewport={"width": 1500, "height": 940})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)
    # 关弹窗
    for txt in ("继续", "我已知晓并继续"):
        try:
            b = page.get_by_text(txt, exact=True)
            if b.count():
                b.first.click(timeout=2500); page.wait_for_timeout(500)
        except Exception:
            pass
    page.evaluate("()=>document.querySelectorAll('input[type=checkbox]').forEach(c=>{if(!c.checked)c.click();})")
    page.wait_for_timeout(400)
    try:
        b = page.get_by_text("我已知晓并继续", exact=True)
        if b.count():
            b.first.click(timeout=2500); page.wait_for_timeout(800)
    except Exception:
        pass

    # 找所有可能与模型有关的可点元素
    cand = page.evaluate("""()=>{
      const V=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};
      const out=[];
      document.querySelectorAll('button,[role=button],[role=combobox],[role=radio],[role=menuitem],[data-state]').forEach(e=>{
        if(!V(e)) return;
        const t=(e.innerText||e.getAttribute('aria-label')||e.getAttribute('data-testid')||'').trim().slice(0,40);
        const cls=String(e.className||'').slice(0,50);
        if(t||cls) out.push({tag:e.tagName, t:t, cls:cls, role:e.getAttribute('role')||'', ds:e.getAttribute('data-state')||''});
      });
      return out;
    }""")
    print("=== 可点元素(前 45) ===")
    for c in cand[:45]:
        print("  %-8s role=%-9s state=%-8s t=%-22s cls=%s" % (c["tag"], c["role"], c["ds"], c["t"][:22], c["cls"][:40]))
    print("\n=== 页面里出现的模型名 ===")
    txt = page.evaluate("()=>document.body.innerText||''")
    import re
    for m in sorted(set(re.findall(r"(gp-[a-z]+|ds-[a-z0-9.\-]+|hy\d|pool-[a-z0-9\-]+|step-5-preview|deepseek-[a-z0-9.\-]+)", txt))):
        print("   ", m)
    ctx.close()
