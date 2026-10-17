#!/usr/bin/env python3
"""画「大肥鱼」的 2D 立绘（q 版）：水手服 + 鲸尾 + 蓝发。

为什么用代码画：不用等画师、改配色/姿势随时重来，版权干净（自己画的）。
这一版对应 docs/character/mascot-sheet.md 的「方案 A · 水手服」。

用法：python make-mascot-2d.py [--out 路径.png] [--size 1200]
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HAIR_DARK = (52, 96, 196)
HAIR_MID = (76, 128, 226)
HAIR_LIGHT = (122, 176, 246)
SKIN = (255, 232, 220)
SKIN_SHADOW = (246, 208, 196)
WHITE = (246, 250, 255)
NAVY = (38, 58, 104)
NAVY_DARK = (26, 40, 74)
ACCENT = (110, 230, 235)
BLUSH = (255, 148, 168)
EYE_DARK = (30, 46, 92)
OUTLINE = (24, 34, 60)
BG = (10, 14, 24)


def ellipse(d, box, fill, outline=None, width=0):
    d.ellipse(box, fill=fill, outline=outline, width=width)


def polygon(d, pts, fill):
    d.polygon(pts, fill=fill)


def draw_tail(d, cx, cy, s):
    """鲸尾：从裙摆后下方伸出，两片尾鳍，末端有荧光纹路。"""
    base = (cx + 40 * s, cy + 250 * s)
    # 尾柄
    d.polygon([base, (base[0] + 60 * s, base[1] + 30 * s), (base[0] + 70 * s, base[1] + 10 * s),
               (base[0] + 20 * s, base[1] - 18 * s)], fill=HAIR_DARK)
    # 尾鳍
    tip = (base[0] + 130 * s, base[1] + 8 * s)
    d.polygon([(base[0] + 60 * s, base[1] + 26 * s), tip, (base[0] + 82 * s, base[1] - 26 * s)], fill=HAIR_MID)
    d.polygon([(base[0] + 60 * s, base[1] + 6 * s), (base[0] + 118 * s, base[1] + 40 * s),
               (base[0] + 64 * s, base[1] + 44 * s)], fill=HAIR_MID)
    # 荧光纹路
    for i in range(3):
        yy = base[1] + 6 * s + i * 7 * s
        d.line([(base[0] + 30 * s, yy), (base[0] + 96 * s, yy + 6 * s)], fill=ACCENT, width=max(1, int(2 * s)))


def draw_hair_back(d, cx, cy, s):
    # 后发（在身体后面）
    d.polygon([
        (cx - 150 * s, cy - 20 * s), (cx - 130 * s, cy + 170 * s), (cx - 60 * s, cy + 210 * s),
        (cx + 60 * s, cy + 210 * s), (cx + 130 * s, cy + 170 * s), (cx + 150 * s, cy - 20 * s),
        (cx + 120 * s, cy - 150 * s), (cx - 120 * s, cy - 150 * s),
    ], fill=HAIR_DARK)


def draw_body(d, cx, cy, s):
    # 脖子
    d.rectangle([cx - 22 * s, cy + 30 * s, cx + 22 * s, cy + 72 * s], fill=SKIN_SHADOW)
    # 上衣（水手服：白底 + 深蓝领）
    d.polygon([(cx - 96 * s, cy + 70 * s), (cx + 96 * s, cy + 70 * s),
               (cx + 104 * s, cy + 196 * s), (cx - 104 * s, cy + 196 * s)], fill=WHITE)
    # 水手领
    d.polygon([(cx - 96 * s, cy + 70 * s), (cx - 60 * s, cy + 150 * s), (cx, cy + 118 * s),
               (cx + 60 * s, cy + 150 * s), (cx + 96 * s, cy + 70 * s), (cx, cy + 96 * s)], fill=NAVY)
    # 领结（鲸鱼领结：深蓝 + 一点荧光）
    d.polygon([(cx - 26 * s, cy + 118 * s), (cx, cy + 132 * s), (cx - 26 * s, cy + 146 * s)], fill=NAVY_DARK)
    d.polygon([(cx + 26 * s, cy + 118 * s), (cx, cy + 132 * s), (cx + 26 * s, cy + 146 * s)], fill=NAVY_DARK)
    ellipse(d, [cx - 8 * s, cy + 124 * s, cx + 8 * s, cy + 140 * s], ACCENT)
    # 袖子
    d.polygon([(cx - 104 * s, cy + 84 * s), (cx - 140 * s, cy + 150 * s), (cx - 104 * s, cy + 168 * s),
               (cx - 86 * s, cy + 110 * s)], fill=WHITE)
    d.polygon([(cx + 104 * s, cy + 84 * s), (cx + 140 * s, cy + 150 * s), (cx + 104 * s, cy + 168 * s),
               (cx + 86 * s, cy + 110 * s)], fill=WHITE)
    # 袖口深蓝条
    d.polygon([(cx - 140 * s, cy + 150 * s), (cx - 104 * s, cy + 168 * s), (cx - 110 * s, cy + 180 * s),
               (cx - 146 * s, cy + 160 * s)], fill=NAVY)
    d.polygon([(cx + 140 * s, cy + 150 * s), (cx + 104 * s, cy + 168 * s), (cx + 110 * s, cy + 180 * s),
               (cx + 146 * s, cy + 160 * s)], fill=NAVY)
    # 手
    ellipse(d, [cx - 152 * s, cy + 148 * s, cx - 118 * s, cy + 184 * s], SKIN)
    ellipse(d, [cx + 118 * s, cy + 148 * s, cx + 152 * s, cy + 184 * s], SKIN)


def draw_skirt(d, cx, cy, s):
    top_y = cy + 196 * s
    bot_y = cy + 288 * s
    d.polygon([(cx - 104 * s, top_y), (cx + 104 * s, top_y),
               (cx + 142 * s, bot_y), (cx - 142 * s, bot_y)], fill=NAVY)
    # 褶
    for i in range(-3, 4):
        x0 = cx + i * 26 * s
        d.line([(x0, top_y + 6 * s), (x0 * 1.25, bot_y)], fill=NAVY_DARK, width=max(1, int(2 * s)))
    # 裙摆白线
    d.line([(cx - 140 * s, bot_y - 6 * s), (cx + 140 * s, bot_y - 6 * s)], fill=WHITE, width=max(2, int(3 * s)))


def draw_legs(d, cx, cy, s):
    # 白袜腿
    for dx in (-46, 46):
        d.polygon([(cx + dx * s - 20 * s, cy + 288 * s), (cx + dx * s + 20 * s, cy + 288 * s),
                   (cx + dx * s + 16 * s, cy + 372 * s), (cx + dx * s - 16 * s, cy + 372 * s)], fill=WHITE)
        # 鞋
        ellipse(d, [cx + dx * s - 26 * s, cy + 366 * s, cx + dx * s + 30 * s, cy + 396 * s], NAVY_DARK)


def draw_head(d, cx, cy, s):
    # 脸
    ellipse(d, [cx - 118 * s, cy - 118 * s, cx + 118 * s, cy + 128 * s], SKIN)
    # 刘海
    d.polygon([(cx - 120 * s, cy - 40 * s), (cx - 100 * s, cy - 130 * s), (cx - 30 * s, cy - 104 * s),
               (cx + 10 * s, cy - 138 * s), (cx + 70 * s, cy - 108 * s), (cx + 118 * s, cy - 128 * s),
               (cx + 120 * s, cy - 30 * s), (cx + 60 * s, cy - 10 * s), (cx + 20 * s, cy - 40 * s),
               (cx - 30 * s, cy - 6 * s), (cx - 80 * s, cy - 34 * s)], fill=HAIR_MID)
    # 侧发
    d.polygon([(cx - 120 * s, cy - 60 * s), (cx - 150 * s, cy + 100 * s), (cx - 112 * s, cy + 90 * s)],
              fill=HAIR_DARK)
    d.polygon([(cx + 120 * s, cy - 60 * s), (cx + 150 * s, cy + 100 * s), (cx + 112 * s, cy + 90 * s)],
              fill=HAIR_DARK)
    # 呆毛
    d.arc([cx - 20 * s, cy - 200 * s, cx + 40 * s, cy - 120 * s], 200, 20, fill=HAIR_LIGHT, width=int(6 * s))
    # 眼睛
    for dx, w, h in ((-52, 34, 44), (52, 34, 44)):
        ellipse(d, [cx + (dx - w / 2) * s, cy - 24 * s, cx + (dx + w / 2) * s, cy + (h - 24) * s], EYE_DARK)
        # 高光
        ellipse(d, [cx + (dx + 4) * s, cy - 18 * s, cx + (dx + 14) * s, cy - 6 * s], WHITE)
        ellipse(d, [cx + (dx - 12) * s, cy + 4 * s, cx + (dx - 4) * s, cy + 12 * s], (170, 210, 255))
    # 腮红
    ellipse(d, [cx - 96 * s, cy + 34 * s, cx - 56 * s, cy + 62 * s], BLUSH)
    ellipse(d, [cx + 56 * s, cy + 34 * s, cx + 96 * s, cy + 62 * s], BLUSH)
    # 嘴
    d.arc([cx - 14 * s, cy + 52 * s, cx + 14 * s, cy + 78 * s], 20, 160, fill=(190, 90, 100), width=int(4 * s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.expanduser("~"), "Videos", "大肥鱼作品",
                                                  "大肥鱼-水手服立绘.png"))
    ap.add_argument("--size", type=int, default=1400)
    ap.add_argument("--transparent", action="store_true")
    args = ap.parse_args()

    W = H = args.size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if args.transparent else BG + (255,))
    d = ImageDraw.Draw(img)
    s = args.size / 1000.0
    cx, cy = W * 0.5, H * 0.42

    if not args.transparent:
        # 背景光晕
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([cx - 400 * s, cy - 300 * s, cx + 400 * s, cy + 500 * s], fill=(40, 90, 180, 70))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(80)))
        d = ImageDraw.Draw(img)

    draw_hair_back(d, cx, cy, s)
    draw_tail(d, cx, cy, s)
    draw_legs(d, cx, cy, s)
    draw_body(d, cx, cy, s)
    draw_skirt(d, cx, cy, s)
    draw_head(d, cx, cy, s)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    img.save(args.out)
    print("已生成:", args.out, f"({os.path.getsize(args.out)} 字节, {W}x{H})")


if __name__ == "__main__":
    main()
