#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_block.py —— 打印遮挡输入框的那个元素的完整祖先链"""
import io
from playwright.sync_api import sync_playwright

url = io.open(r"C:\Users\qq\SharedKB\破甲融合\sdzibo_url.txt", encoding="utf-8").read().strip()
with sync_playwright() as pw:
    br = pw.chromium.launch(headless=True)
    ctx = br.new_context(viewport={"width": 1500, "height": 940})
    pg = ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)
    chain = pg.evaluate("""()=>{
      const c = document.querySelector('[contenteditable][data-composer-input]');
      if(!c) return ['no composer'];
      const r = c.getBoundingClientRect();
      const e = document.elementFromPoint(r.x+r.width/2, r.y+r.height/2);
      if(!e) return ['elementFromPoint -> null'];
      const out=[]; let p=e; let n=0;
      while(p && n<14){
        const cs=getComputedStyle(p);
        out.push({
          tag:p.tagName, id:p.id||'', cls:(p.className&&p.className.baseVal===undefined?String(p.className):String(p.className)).slice(0,70),
          pos:cs.position, z:cs.zIndex, disp:cs.display, vis:cs.visibility, op:cs.opacity,
          pe:cs.pointerEvents, hasComposer: p.contains(c),
          txt:(p.innerText||'').trim().slice(0,50).replace(/\\n/g,'|')
        });
        p=p.parentElement; n++;
      }
      return out;
    }""")
    for i, x in enumerate(chain):
        if isinstance(x, str):
            print("  ", x); continue
        print("  %d %-6s pos=%-8s z=%-6s pe=%-6s 含输入框=%-5s cls=%s" % (
            i, x["tag"], x["pos"], x["z"], x["pe"], x["hasComposer"], x["cls"][:50]))
        print("      文本: %s" % x["txt"])
    br.close()
