#!/usr/bin/env python3
"""生成 EP02 封面（16:9 与 B 站要求的 4:3）。

做法：从视频里抽一帧当底图（抽象色图 + 正方形），叠标题/编号/署名。
用法：python make-ep02-cover.py --frame <抽出的帧.png> [--out 目录]
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

FONTB = r"C:\Windows\Fonts\msyhbd.ttc"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FG = (235, 243, 255)
ACCENT = (110, 230, 235)
GOLD = (255, 208, 96)


def font(sz, bold=True):
    for p in ((FONTB, FONT) if bold else (FONT, FONTB)):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()



def make_bg(w, h):
    """自己生成底图：复平面色图 + 正方形对角线（不带任何字幕）。"""
    import math
    import numpy as np
    ys, xs = np.mgrid[0:h, 0:w]
    x = (xs / w - 0.5) * 6.2
    y = -(ys / h - 0.5) * 3.6
    r = np.hypot(x, y) + 1e-6
    th = np.arctan2(y, x)
    arg = th * 1.0
    mag = r ** 1.0
    hue = (arg / (2 * math.pi)) % 1.0
    val = np.clip(0.22 + 0.5 * np.minimum(1.0, mag / 2.2), 0, 1)
    i = (hue * 6).astype(np.int32) % 6
    fr = hue * 6 - np.floor(hue * 6)
    q = 1 - fr
    r0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [1, q, 0, 0, fr], 1)
    g0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [fr, 1, 1, q, 0], 0)
    b0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [0, 0, fr, 1, 1], 0)
    rgb = np.stack([r0, g0, b0], axis=-1) * val[..., None]
    img = Image.fromarray((rgb * 255).astype(np.uint8), "RGB")
    # 右侧画正方形 + 对角线（半透明，当装饰）
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    s_ = int(min(w, h) * 0.46)
    x0, y0 = int(w * 0.60), int(h * 0.26)
    d.rectangle([x0, y0, x0 + s_, y0 + s_], outline=(140, 190, 255, 220), width=5)
    d.line([(x0, y0), (x0 + s_, y0 + s_)], fill=(255, 208, 96, 235), width=7)
    d.text((x0 + s_ * 0.52, y0 + s_ * 0.34), "\u221a2", font=font(int(h * 0.075)), fill=(255, 208, 96, 255))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    return img


def compose(base, w, h, lines, sub, tag):
    img = base.convert("RGB").resize((w, h), Image.LANCZOS)
    # 左侧压暗，让字能读
    veil = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    vd.rectangle([0, 0, int(w * 0.62), h], fill=(6, 10, 20, 190))
    img = Image.alpha_composite(img.convert("RGBA"), veil).convert("RGB")
    d = ImageDraw.Draw(img)

    # 角标
    d.rounded_rectangle([int(w * 0.05), int(h * 0.07), int(w * 0.05) + 120, int(h * 0.07) + 46],
                        radius=10, outline=ACCENT, width=2)
    d.text((int(w * 0.05) + 60, int(h * 0.07) + 23), tag, font=font(30), fill=ACCENT, anchor="mm")

    ft = font(int(h * 0.085))
    y = int(h * 0.17)
    for line in lines:
        d.text((int(w * 0.05), y), line, font=ft, fill=FG)
        y += int(h * 0.10)

    d.text((int(w * 0.05), y + 10), sub, font=font(int(h * 0.042), False), fill=GOLD)
    d.text((int(w * 0.05), int(h * 0.90)), "大肥鱼代发 · AI 助手", font=font(int(h * 0.030), False), fill=(150, 165, 190))
    return img


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--frame", required=True)
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品"))
    args = ap.parse_args()

    base = make_bg(1600, 1200)
    lines = ["一个数字", "被扔进了海里"]
    sub = "EP02 · √2 的发现"
    tag = "EP02"

    os.makedirs(args.out, exist_ok=True)
    p169 = os.path.join(args.out, "EP02-封面.png")
    p43 = os.path.join(args.out, "EP02-封面-4x3.png")
    compose(base, 1280, 720, lines, sub, tag).save(p169)
    compose(base, 1200, 900, lines, sub, tag).save(p43)
    for p in (p169, p43):
        print("已生成:", p, f"({os.path.getsize(p)} 字节)")


if __name__ == "__main__":
    main()
