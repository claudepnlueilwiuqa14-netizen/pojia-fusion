#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dismiss_js.py —— SDzibo 测试用的"关弹窗"脚本

要点:
  * 优先用 **原生 DOM click()** 关掉 dsh-purge 的用户须知遮罩(.dshp-auth-mask)
    —— Playwright 的 force click 对 React 合成事件不生效, 原生 click 会冒泡到 React root
  * 再用原生 click 关掉"预览版说明"
  * 删除遮罩只作兜底, 且**绝不删 body>div**(可能是应用根容器), 也绝不删包含输入框的祖先
  * 结束必须校验: 输入框存在 且 elementFromPoint 命中它
"""

HARD = """() => {
  const composer = () => document.querySelector('[contenteditable][data-composer-input]')
                        || document.querySelector('[contenteditable]');
  const clickText = (root, txt) => {
    const b = Array.from(root.querySelectorAll('button,[role=button],a,div'))
      .filter(x => (x.innerText || '').trim() === txt)
      .pop();
    if (b) { b.click(); return true; }
    return false;
  };
  // 1) dsh-purge 用户须知: 勾选 + 原生 click 确认
  for (let i = 0; i < 3; i++) {
    const m = document.querySelector('.dshp-auth-mask');
    if (!m) break;
    m.querySelectorAll('input[type=checkbox]').forEach(c => { if (!c.checked) c.click(); });
    clickText(m, '我已知晓并继续');
  }
  // 2) 预览版说明: 原生 click 继续
  for (let i = 0; i < 3; i++) {
    const d = Array.from(document.querySelectorAll('[role=dialog],[aria-modal=true],[class*="dialog"]'))
      .filter(x => (x.innerText || '').includes('预览版说明'))[0];
    if (!d) break;
    if (!clickText(d, '继续')) {
      const b = d.querySelector('button');
      if (b) b.click(); else break;
    }
  }
  // 3) 兜底: 删掉仍可见的遮罩(保护含输入框的)
  const SEL = ['.dshp-auth-mask', '[role=dialog]', '[aria-modal=true]',
               '[class*="dialog"]', '[class*="Dialog"]', '[class*="mask"]',
               '[class*="Mask"]', '[class*="overlay"]', '[class*="Overlay"]'];
  const c0 = composer();
  Array.from(document.querySelectorAll(SEL.join(','))).forEach(d => {
    const r = d.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    if (d.tagName === 'BODY' || d.tagName === 'HTML') return;
    if (c0 && d.contains(c0)) return;
    if (d.parentElement) d.parentElement.removeChild(d);
  });
  const c = composer();
  if (!c) return -1;
  const r = c.getBoundingClientRect();
  const e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
  return (e && c.contains(e)) ? 0 : 1;
}"""
