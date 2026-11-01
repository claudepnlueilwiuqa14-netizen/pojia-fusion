#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bagua_icon.py —— 生成 SDzibo 八卦图标(PNG + ICO + favicon data URI)"""
import io, math, os, base64
from PIL import Image, ImageDraw

OUT = r"C:\Users\qq\SharedKB\破甲融合\assets"
os.makedirs(OUT, exist_ok=True)

S = 1024          # 主尺寸
BG = (13, 15, 19) # --g0
FG = (231, 234, 240)  # --g9
AC = (75, 123, 245)   # --ac

img = Image.new("RGBA", (S, S), BG + (255,))
d = ImageDraw.Draw(img)


def yin_yang(cx, cy, r, fg, bg):
    """太极图: 两个鱼形 + 两个点"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill=bg)
    # S 形
    r2 = r / 2
    d.ellipse([cx - r2, cy - r, cx + r2, cy], fill=bg)
    d.ellipse([cx - r2, cy, cx + r2, cy + r], fill=fg)
    # 两个眼
    dr = r / 9
    d.ellipse([cx - dr, cy - r / 2 - dr, cx + dr, cy - r / 2 + dr], fill=fg)
    d.ellipse([cx - dr, cy + r / 2 - dr, cx + dr, cy + r / 2 + dr], fill=bg)


# 外环: 八个卦符(用三爻线表示, 断/实)
R_OUT = S * 0.44
r_yang = S * 0.20
cx = cy = S / 2

# 八卦爻名与二进制(1=实线, 0=断线)
TRIGRAMS = [
    ("乾", "111"), ("兑", "110"), ("离", "101"), ("震", "100"),
    ("巽", "011"), ("坎", "010"), ("艮", "001"), ("坤", "000"),
]
line_w = S * 0.055          # 线宽(厚)
seg_w = S * 0.042          # 单段宽
gap = S * 0.012
tr = S * 0.205             # 卦符外接半径
bar_len = tr * 0.86

for i, (name, bits) in enumerate(TRIGRAMS):
    ang = -math.pi / 2 + i * (2 * math.pi / 8)
    bx = cx + R_OUT * math.cos(ang)
    by = cy + R_OUT * math.sin(ang)
    rot = ang + math.pi / 2
    ca, sa = math.cos(rot), math.sin(rot)
    for row in range(3):                      # 三爻
        yoff = (row - 1) * (line_w + gap)
        if bits[2 - row] == "1":              # 实线
            L, T = -bar_len / 2, bar_len / 2
            pts = [(bx + x * ca - yoff * sa, by + x * sa + yoff * ca)
                   for x in (L, T)]
            d.line(pts, fill=FG, width=int(line_w))
        else:                                 # 断线
            L, T = -bar_len / 2, -bar_len / 2 + bar_len * 0.44
            for x0, x1 in ((L, T), (T + bar_len * 0.12, bar_len / 2)):
                pts = [(bx + x * ca - yoff * sa, by + x * sa + yoff * ca)
                       for x in (x0, x1)]
                d.line(pts, fill=FG, width=int(line_w))

# 内圈太极
yin_yang(cx, cy, r_yang, FG, BG)

# 外边框环
d.ellipse([cx - R_OUT - S * 0.075, cy - R_OUT - S * 0.075,
           cx + R_OUT + S * 0.075, cy + R_OUT + S * 0.075], outline=AC, width=int(S * 0.012))
d.ellipse([cx - R_OUT + S * 0.015, cy - R_OUT + S * 0.015,
           cx + R_OUT - S * 0.015, cy + R_OUT - S * 0.015], outline=AC, width=int(S * 0.006))

png = os.path.join(OUT, "sdzibo_bagua.png")
img.save(png)
ico = os.path.join(OUT, "sdzibo_bagua.ico")
img.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
buf = io.BytesIO()
img.resize((64, 64), Image.LANCZOS).save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode()
open(os.path.join(OUT, "sdzibo_favicon_b64.txt"), "w").write(b64)
print("PNG :", png, os.path.getsize(png), "字节")
print("ICO :", ico, os.path.getsize(ico), "字节")
print("favicon b64 长度:", len(b64))
