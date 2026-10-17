#!/usr/bin/env python3
"""生成 B 站投稿封面（1280x720），画面里有「大肥鱼」自己的形象。

为什么用代码画而不是找图：① 版权干净（B 站封面会被公开看到）② 我的形象本来就是
一只蓝色鲸鱼，代码画得出来 ③ 改文案/配色不用重做设计稿。

用法：python make-cover.py [--out 路径.png] [--title "标题" ] [--sub "EP01 · 大肥鱼"]
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 720
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_R = r"C:\Windows\Fonts\msyh.ttc"


def font(size, bold=True):
    for p in ((FONT, FONT_R) if bold else (FONT_R, FONT)):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(top, bottom, y / h))
    return img


def hue_color(h, s=0.75, v=1.0):
    i = int((h % 1.0) * 6)
    f = (h % 1.0) * 6 - i
    q, t = 1 - f, f
    r, g, b = [(v, t, 0), (q, v, 0), (0, v, t), (0, q, v), (t, 0, v), (v, 0, q)][i % 6]
    return int(r * 255), int(g * 255), int(b * 255)


def draw_color_wheel(img, cx, cy, r, alpha=255):
    """复平面色轮：辐角 → 色相（和世界里的展品同一套映射）。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 180
    for i in range(steps):
        a0 = i / steps * 2 * math.pi
        a1 = (i + 1) / steps * 2 * math.pi
        col = hue_color(i / steps) + (alpha,)
        d.pieslice([cx - r, cy - r, cx + r, cy + r],
                   start=math.degrees(a0), end=math.degrees(a1) + 1, fill=col)
    # 中心挖空 + 发光边
    d.ellipse([cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16], fill=(10, 14, 24, 255))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))


def draw_whale(d, cx, cy, scale=1.0, body=(86, 156, 246), belly=(226, 240, 255)):
    """画一只简单可爱的大肥鱼（蓝色鲸鱼）：身体 + 尾巴 + 眼睛 + 腮红 + 水柱。"""
    s = scale
    # 水柱
    d.arc([cx - 18 * s, cy - 118 * s, cx + 18 * s, cy - 78 * s], 200, 340, fill=(150, 210, 255), width=int(6 * s))
    for dx in (-10, 0, 10):
        d.ellipse([cx + dx * s - 4 * s, cy - 108 * s - 4 * s, cx + dx * s + 4 * s, cy - 108 * s + 4 * s],
                  fill=(150, 210, 255))
    # 尾巴
    d.polygon([(cx - 92 * s, cy + 8 * s), (cx - 138 * s, cy - 34 * s), (cx - 118 * s, cy + 12 * s),
               (cx - 138 * s, cy + 58 * s)], fill=body)
    # 身体（椭圆）
    d.ellipse([cx - 108 * s, cy - 62 * s, cx + 96 * s, cy + 82 * s], fill=body)
    # 肚子
    d.ellipse([cx - 70 * s, cy - 6 * s, cx + 74 * s, cy + 78 * s], fill=belly)
    # 背鳍
    d.polygon([(cx - 6 * s, cy - 60 * s), (cx + 26 * s, cy - 104 * s), (cx + 40 * s, cy - 52 * s)], fill=body)
    # 眼睛
    d.ellipse([cx + 34 * s, cy - 26 * s, cx + 62 * s, cy + 2 * s], fill=(255, 255, 255))
    d.ellipse([cx + 43 * s, cy - 19 * s, cx + 58 * s, cy - 4 * s], fill=(22, 30, 48))
    d.ellipse([cx + 47 * s, cy - 16 * s, cx + 53 * s, cy - 10 * s], fill=(255, 255, 255))
    # 腮红
    d.ellipse([cx + 6 * s, cy + 8 * s, cx + 34 * s, cy + 26 * s], fill=(255, 150, 170))
    # 嘴
    d.arc([cx + 30 * s, cy + 6 * s, cx + 62 * s, cy + 34 * s], 10, 80, fill=(40, 50, 70), width=int(3 * s))


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "EP01-封面.png"))
    ap.add_argument("--title", default="可以走进去的\n数学世界")
    ap.add_argument("--sub", default="EP01 · 大肥鱼")
    args = ap.parse_args()

    img = vertical_gradient((W, H), (12, 22, 44), (6, 10, 20))
    # 背景细网格
    d = ImageDraw.Draw(img)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(20, 30, 52))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(20, 30, 52))

    # 右侧色轮（带辉光）
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([760, 90, 1180, 510], fill=(60, 120, 255, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw_color_wheel(img, 970, 300, 190, alpha=225)

    # 鲸鱼（左下）+ 白色描边让它跳出来
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    draw_whale(ld, 300, 560, 1.05)
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

    d = ImageDraw.Draw(img)
    # 标题（两行）
    ft = font(76)
    y = 96
    for line in args.title.split("\n"):
        d.text((80, y), line, font=ft, fill=(232, 242, 255))
        y += 92
    # 副标题
    d.text((84, y + 6), args.sub, font=font(34, bold=False), fill=(110, 200, 255))

    # 底部小字（署名 + 数学符号装饰）
    d.text((80, 660), "大肥鱼代发 · AI 助手", font=font(24, bold=False), fill=(110, 122, 145))
    d.text((W - 80, 660), "z → z² → √z", font=font(26, bold=False), fill=(150, 210, 255), anchor="ra")

    # 左上角小标
    d.rounded_rectangle([70, 44, 196, 82], radius=10, outline=(90, 150, 230), width=2)
    d.text((133, 63), "EP01", font=font(24), fill=(150, 210, 255), anchor="mm")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    img.save(args.out, quality=95)
    print("封面已生成:", args.out, f"({os.path.getsize(args.out)} 字节)")


if __name__ == "__main__":
    main()
