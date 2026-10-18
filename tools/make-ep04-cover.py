#!/usr/bin/env python3
"""EP04 封面（16:9 + 4:3）—— 按新配方：
标题占画面 40%，道具（刻度尺 + 费马点）放大，背景压暗，左下 EP 编号。

用法：python make-ep04-cover.py [--out 目录]
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONTB = r"C:\Windows\Fonts\msyhbd.ttc"
FG = (240, 246, 255)
YEL = (255, 208, 96)
BLU = (110, 170, 255)
RED = (255, 118, 118)
CYA = (110, 230, 235)
DIM = (130, 148, 175)
BG = (5, 8, 14)


def font(sz, bold=True):
    for p in ((FONTB, FONT) if bold else (FONT, FONTB)):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def fermat(a, b, c):
    x = (a[0] + b[0] + c[0]) / 3
    y = (a[1] + b[1] + c[1]) / 3
    for _ in range(3000):
        gx = gy = 0.0
        for p in (a, b, c):
            d = max(1e-6, math.hypot(x - p[0], y - p[1]))
            gx += (x - p[0]) / d
            gy += (y - p[1]) / d
        n = math.hypot(gx, gy)
        if n < 1e-6:
            break
        x -= 1.6 * gx
        y -= 1.6 * gy
    return (x, y)


def compose(w, h, title_lines, sub, tag="EP04"):
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)

    # 极淡网格（质感）
    for gx in range(0, w, 60):
        d.line([(gx, 0), (gx, h)], fill=(10, 14, 22))
    for gy in range(0, h, 60):
        d.line([(0, gy), (w, gy)], fill=(10, 14, 22))

    # 右侧图形区：三角形 + 三色线 + 费马点（占右半）
    A = (w * 0.60, h * 0.86)
    B = (w * 0.97, h * 0.86)
    C = (w * 0.785, h * 0.50)
    F = fermat(A, B, C)
    d.line([A, B, C, A], fill=(215, 226, 245), width=max(2, w // 420))
    for p, col in ((A, YEL), (B, BLU), (C, RED)):
        d.line([F, p], fill=col, width=max(3, w // 300))
    r = max(6, w // 130)
    d.ellipse([F[0] - r, F[1] - r, F[0] + r, F[1] + r], fill=CYA)
    # 三个角的字母
    fa = font(max(14, int(h * 0.035)))
    for p, name, off in ((A, "A", (-int(h * 0.04), int(h * 0.03))),
                         (B, "B", (int(h * 0.015), int(h * 0.03))),
                         (C, "C", (-int(h * 0.01), -int(h * 0.06)))):
        d.text((p[0] + off[0], p[1] + off[1]), name, font=fa, fill=(200, 214, 235))

    # 刻度尺（道具，放大）
    ry = h * 0.93
    rh = h * 0.055
    d.rounded_rectangle([w * 0.56, ry, w * 0.98, ry + rh], radius=8,
                        fill=(16, 22, 34), outline=(80, 98, 128), width=2)
    for i in range(21):
        x = w * 0.56 + 14 + i * (w * 0.42 - 28) / 20
        ln = rh * 0.5 if i % 5 == 0 else rh * 0.28
        d.line([(x, ry + rh - 4), (x, ry + rh - 4 - ln)], fill=(120, 140, 170), width=2)

    # 左侧压暗，保证文字可读
    veil = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    vd.rectangle([0, 0, int(w * 0.56), h], fill=(4, 7, 13, 205))
    img = Image.alpha_composite(img.convert("RGBA"), veil).convert("RGB")
    d = ImageDraw.Draw(img)

    # 角标
    d.rounded_rectangle([int(w * 0.045), int(h * 0.07), int(w * 0.045) + int(w * 0.10), int(h * 0.07) + int(h * 0.058)],
                        radius=10, outline=CYA, width=2)
    d.text((int(w * 0.045) + int(w * 0.05), int(h * 0.07) + int(h * 0.029)), tag,
           font=font(int(h * 0.035)), fill=CYA, anchor="mm")

    # 标题：占画面高度 40%
    ty = int(h * 0.18)
    ft = font(int(h * 0.135))
    for line in title_lines:
        d.text((int(w * 0.045), ty), line, font=ft, fill=FG)
        ty += int(h * 0.145)

    d.text((int(w * 0.045), ty + int(h * 0.01)), sub, font=font(int(h * 0.05), False), fill=YEL)
    return img


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    lines = ["三个村子", "一个水站"]
    sub = "管道最短怎么修？"
    p169 = os.path.join(args.out, "EP04-封面.png")
    p43 = os.path.join(args.out, "EP04-封面-4x3.png")
    compose(1280, 720, lines, sub).save(p169)
    compose(1200, 900, lines, sub).save(p43)
    for p in (p169, p43):
        print("已生成:", p, f"({os.path.getsize(p)} 字节)")


if __name__ == "__main__":
    main()
