#!/usr/bin/env python3
"""画「大肥鱼」的 2D 立绘（q 版水手服）—— 第二版，带描边 / 发丝 / 表情差分。

用法：
    python make-mascot-2d.py --out 图.png                    # 默认开心
    python make-mascot-2d.py --expr happy|confused|proud|shy|tired
    python make-mascot-2d.py --all --dir 输出目录             # 一次出全套
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFilter

HAIR_DARK = (46, 86, 176)
HAIR_MID = (72, 124, 222)
HAIR_LIGHT = (128, 182, 248)
SKIN = (255, 233, 221)
SKIN_SHADOW = (244, 206, 194)
WHITE = (247, 250, 255)
NAVY = (38, 58, 104)
NAVY_DARK = (24, 38, 70)
ACCENT = (110, 230, 235)
BLUSH = (255, 146, 168)
EYE_DARK = (32, 48, 96)
INK = (20, 28, 52)
BG = (10, 14, 24)


def poly(d, pts, fill, outline=INK, w=4):
    d.polygon(pts, fill=fill)
    if outline and w:
        d.line(pts + [pts[0]], fill=outline, width=w, joint='curve')


def bit(d, box, fill, outline=INK, w=4):
    d.ellipse(box, fill=fill)
    if outline and w:
        d.ellipse(box, outline=outline, width=w)


def draw_tail(d, cx, cy, s):
    """鲸尾：从裙后伸出，向右上扬，末端分叉 + 荧光数据纹路。"""
    x0, y0 = cx + 20 * s, cy + 250 * s
    body = [(x0, y0), (x0 + 70 * s, y0 - 18 * s), (x0 + 120 * s, y0 - 76 * s),
            (x0 + 150 * s, y0 - 30 * s), (x0 + 108 * s, y0 + 22 * s), (x0 + 96 * s, y0 + 60 * s),
            (x0 + 30 * s, y0 + 40 * s)]
    poly(d, body, HAIR_MID, INK, max(2, int(3 * s)))
    # 尾鳍分叉
    poly(d, [(x0 + 120 * s, y0 - 76 * s), (x0 + 178 * s, y0 - 96 * s), (x0 + 150 * s, y0 - 30 * s)],
         HAIR_DARK, INK, max(2, int(3 * s)))
    poly(d, [(x0 + 108 * s, y0 + 22 * s), (x0 + 170 * s, y0 + 40 * s), (x0 + 96 * s, y0 + 60 * s)],
         HAIR_DARK, INK, max(2, int(3 * s)))
    # 荧光纹路（数据流）
    for i in range(3):
        yy = y0 - 4 * s + i * 16 * s
        d.line([(x0 + 24 * s, yy), (x0 + 106 * s, yy - 6 * s)], fill=ACCENT, width=max(2, int(2 * s)))


def draw_hair_back(d, cx, cy, s):
    poly(d, [
        (cx - 152 * s, cy - 30 * s), (cx - 140 * s, cy + 150 * s), (cx - 96 * s, cy + 210 * s),
        (cx - 40 * s, cy + 230 * s), (cx + 40 * s, cy + 230 * s), (cx + 96 * s, cy + 210 * s),
        (cx + 140 * s, cy + 150 * s), (cx + 152 * s, cy - 30 * s), (cx + 126 * s, cy - 140 * s),
        (cx - 126 * s, cy - 140 * s),
    ], HAIR_DARK, INK, max(2, int(4 * s)))


def draw_body(d, cx, cy, s):
    poly(d, [(cx - 24 * s, cy + 40 * s), (cx + 24 * s, cy + 40 * s),
             (cx + 24 * s, cy + 86 * s), (cx - 24 * s, cy + 86 * s)], SKIN_SHADOW, INK, max(2, int(3 * s)))
    # 上衣
    poly(d, [(cx - 98 * s, cy + 76 * s), (cx + 98 * s, cy + 76 * s), (cx + 106 * s, cy + 198 * s),
             (cx - 106 * s, cy + 198 * s)], WHITE, INK, max(2, int(4 * s)))
    # 水手领
    poly(d, [(cx - 98 * s, cy + 76 * s), (cx - 56 * s, cy + 156 * s), (cx, cy + 120 * s),
             (cx + 56 * s, cy + 156 * s), (cx + 98 * s, cy + 76 * s), (cx, cy + 100 * s)], NAVY, INK, max(2, int(3 * s)))
    # 白边（水手领的细白条）
    d.line([(cx - 56 * s, cy + 156 * s), (cx, cy + 120 * s), (cx + 56 * s, cy + 156 * s)],
           fill=WHITE, width=max(2, int(3 * s)))
    # 鲸鱼领结
    poly(d, [(cx - 30 * s, cy + 120 * s), (cx, cy + 136 * s), (cx - 30 * s, cy + 152 * s)], NAVY_DARK, INK, max(2, int(2 * s)))
    poly(d, [(cx + 30 * s, cy + 120 * s), (cx, cy + 136 * s), (cx + 30 * s, cy + 152 * s)], NAVY_DARK, INK, max(2, int(2 * s)))
    bit(d, [cx - 9 * s, cy + 127 * s, cx + 9 * s, cy + 145 * s], ACCENT, INK, max(2, int(2 * s)))
    # 袖子
    poly(d, [(cx - 100 * s, cy + 88 * s), (cx - 136 * s, cy + 152 * s), (cx - 100 * s, cy + 172 * s),
             (cx - 84 * s, cy + 112 * s)], WHITE, INK, max(2, int(3 * s)))
    poly(d, [(cx + 100 * s, cy + 88 * s), (cx + 136 * s, cy + 152 * s), (cx + 100 * s, cy + 172 * s),
             (cx + 84 * s, cy + 112 * s)], WHITE, INK, max(2, int(3 * s)))
    # 袖口条
    poly(d, [(cx - 136 * s, cy + 152 * s), (cx - 100 * s, cy + 172 * s), (cx - 106 * s, cy + 184 * s),
             (cx - 142 * s, cy + 163 * s)], NAVY, INK, max(2, int(2 * s)))
    poly(d, [(cx + 136 * s, cy + 152 * s), (cx + 100 * s, cy + 172 * s), (cx + 106 * s, cy + 184 * s),
             (cx + 142 * s, cy + 163 * s)], NAVY, INK, max(2, int(2 * s)))
    # 手（带手指暗示）
    for side in (-1, 1):
        hx = cx + side * 130 * s
        bit(d, [hx - 22 * s, cy + 168 * s, hx + 22 * s, cy + 204 * s], SKIN, INK, max(2, int(3 * s)))
        for k in (-6, 2, 10):
            d.line([(hx + k * s, cy + 190 * s), (hx + k * s, cy + 200 * s)], fill=SKIN_SHADOW, width=max(1, int(2 * s)))


def draw_skirt(d, cx, cy, s):
    top_y, bot_y = cy + 198 * s, cy + 292 * s
    poly(d, [(cx - 106 * s, top_y), (cx + 106 * s, top_y), (cx + 146 * s, bot_y), (cx - 146 * s, bot_y)],
         NAVY, INK, max(2, int(4 * s)))
    for i in range(-3, 4):
        x0 = cx + i * 26 * s
        d.line([(x0, top_y + 8 * s), (x0 * 1.28, bot_y - 4 * s)], fill=NAVY_DARK, width=max(1, int(2 * s)))
    d.line([(cx - 142 * s, bot_y - 8 * s), (cx + 142 * s, bot_y - 8 * s)], fill=WHITE, width=max(2, int(3 * s)))


def draw_legs(d, cx, cy, s):
    for dx in (-46, 46):
        poly(d, [(cx + dx * s - 22 * s, cy + 292 * s), (cx + dx * s + 22 * s, cy + 292 * s),
                 (cx + dx * s + 17 * s, cy + 378 * s), (cx + dx * s - 17 * s, cy + 378 * s)], WHITE, INK, max(2, int(3 * s)))
        poly(d, [(cx + dx * s - 26 * s, cy + 372 * s), (cx + dx * s + 26 * s, cy + 372 * s),
                 (cx + dx * s + 32 * s, cy + 400 * s), (cx + dx * s - 32 * s, cy + 400 * s)], NAVY_DARK, INK, max(2, int(3 * s)))


def draw_face(d, cx, cy, s, expr):
    bit(d, [cx - 120 * s, cy - 120 * s, cx + 120 * s, cy + 130 * s], SKIN, INK, max(2, int(4 * s)))
    # 刘海（分三束，带尖）
    poly(d, [(cx - 122 * s, cy - 30 * s), (cx - 104 * s, cy - 132 * s), (cx - 44 * s, cy - 92 * s),
             (cx - 10 * s, cy - 140 * s), (cx + 34 * s, cy - 96 * s), (cx + 78 * s, cy - 138 * s),
             (cx + 122 * s, cy - 60 * s), (cx + 96 * s, cy - 16 * s), (cx + 40 * s, cy - 44 * s),
             (cx - 4 * s, cy - 10 * s), (cx - 62 * s, cy - 40 * s), (cx - 96 * s, cy - 6 * s)],
         HAIR_MID, INK, max(2, int(4 * s)))
    # 发丝高光
    for pts in ([(cx - 96 * s, cy - 96 * s), (cx - 60 * s, cy - 60 * s)],
                [(cx - 20 * s, cy - 108 * s), (cx + 6 * s, cy - 62 * s)],
                [(cx + 52 * s, cy - 100 * s), (cx + 74 * s, cy - 66 * s)]):
        d.line(pts, fill=HAIR_LIGHT, width=max(2, int(4 * s)))
    # 侧发（两束长发，尖尾）
    poly(d, [(cx - 122 * s, cy - 70 * s), (cx - 156 * s, cy + 96 * s), (cx - 120 * s, cy + 150 * s),
             (cx - 112 * s, cy + 40 * s)], HAIR_DARK, INK, max(2, int(3 * s)))
    poly(d, [(cx + 122 * s, cy - 70 * s), (cx + 156 * s, cy + 96 * s), (cx + 120 * s, cy + 150 * s),
             (cx + 112 * s, cy + 40 * s)], HAIR_DARK, INK, max(2, int(3 * s)))
    # 呆毛
    d.arc([cx - 26 * s, cy - 208 * s, cx + 44 * s, cy - 128 * s], 195, 25, fill=HAIR_LIGHT, width=max(3, int(5 * s)))

    eye_l, eye_r = cx - 54 * s, cx + 54 * s
    if expr in ('happy', 'proud', 'shy'):
        # 弯眼 ^ ^
        for ex in (eye_l, eye_r):
            d.arc([ex - 26 * s, cy - 30 * s, ex + 26 * s, cy + 18 * s], 200, 340, fill=INK, width=max(3, int(6 * s)))
    else:
        for ex in (eye_l, eye_r):
            bit(d, [ex - 26 * s, cy - 30 * s, ex + 26 * s, cy + 26 * s], EYE_DARK, INK, max(2, int(3 * s)))
            bit(d, [ex + 2 * s, cy - 22 * s, ex + 16 * s, cy - 8 * s], WHITE, None, 0)
            bit(d, [ex - 14 * s, cy + 4 * s, ex - 4 * s, cy + 14 * s], (176, 214, 255), None, 0)
    # 腮红
    for ex in (cx - 88 * s, cx + 88 * s):
        bit(d, [ex - 24 * s, cy + 34 * s, ex + 24 * s, cy + 66 * s], BLUSH, None, 0)
    # 嘴
    if expr == 'happy':
        d.arc([cx - 20 * s, cy + 52 * s, cx + 20 * s, cy + 88 * s], 20, 160, fill=(178, 82, 96), width=max(2, int(4 * s)))
    elif expr == 'proud':
        d.arc([cx - 22 * s, cy + 56 * s, cx + 22 * s, cy + 84 * s], 200, 340, fill=(178, 82, 96), width=max(2, int(4 * s)))
    elif expr == 'confused':
        d.line([(cx - 14 * s, cy + 70 * s), (cx + 14 * s, cy + 64 * s)], fill=(178, 82, 96), width=max(2, int(4 * s)))
    elif expr == 'shy':
        d.arc([cx - 14 * s, cy + 56 * s, cx + 14 * s, cy + 78 * s], 20, 160, fill=(178, 82, 96), width=max(2, int(4 * s)))
    else:
        d.arc([cx - 16 * s, cy + 56 * s, cx + 16 * s, cy + 82 * s], 20, 160, fill=(178, 82, 96), width=max(2, int(4 * s)))


def render(expr, size, out, transparent=False):
    W = H = size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if transparent else BG + (255,))
    s = size / 1000.0
    cx, cy = W * 0.5, H * 0.40

    if not transparent:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([cx - 380 * s, cy - 260 * s, cx + 380 * s, cy + 520 * s], fill=(40, 90, 180, 70))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(img)

    draw_hair_back(d, cx, cy, s)
    draw_tail(d, cx, cy, s)
    draw_legs(d, cx, cy, s)
    draw_body(d, cx, cy, s)
    draw_skirt(d, cx, cy, s)
    draw_face(d, cx, cy, s, expr)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "大肥鱼-水手服-开心.png"))
    ap.add_argument("--expr", default="happy", choices=["happy", "confused", "proud", "shy", "tired"])
    ap.add_argument("--size", type=int, default=1400)
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dir", default=os.path.join(home, "Videos", "大肥鱼作品"))
    args = ap.parse_args()

    if args.all:
        for e in ("happy", "confused", "proud", "shy", "tired"):
            p = os.path.join(args.dir, f"大肥鱼-水手服-{e}.png")
            render(e, args.size, p, args.transparent)
            print("已生成:", p)
    else:
        p = render(args.expr, args.size, args.out, args.transparent)
        print("已生成:", p, f"({os.path.getsize(p)} 字节, {args.size}x{args.size})")


if __name__ == "__main__":
    main()
