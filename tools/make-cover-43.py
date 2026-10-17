#!/usr/bin/env python3
"""把 16:9 封面转成 B 站要求的 4:3（1146x860 → 这里出 1200x900，安全余量）。

为什么要它：B 站首页推荐封面是 **4:3**，直接传 16:9 的图会被裁/被拒
（2026-10-17 实测：投稿页封面弹窗里 16:9 的图放不进去）。
做法：按宽度缩放原图，上下补同色渐变 + 网格，看起来是"设计好的留白"，不是黑边。
"""
import os
import sys
from PIL import Image, ImageDraw

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.expanduser("~"), "Videos", "大肥鱼作品", "EP01-封面.png")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.expanduser("~"), "Videos", "大肥鱼作品", "EP01-封面-4x3.png")

W, H = 1200, 900          # 4:3


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    src = Image.open(SRC).convert("RGB")
    # 按宽度缩放
    scale = W / src.width
    fitted = src.resize((W, int(src.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H))

    # 背景：和原图同色系的渐变 + 网格（让留白看起来是设计）
    d = ImageDraw.Draw(canvas)
    top, bottom = (12, 22, 44), (6, 10, 20)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(top, bottom, y / H))
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(20, 30, 52))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(20, 30, 52))

    y0 = (H - fitted.height) // 2
    canvas.paste(fitted, (0, y0))
    canvas.save(DST, quality=95)
    print("已生成 4:3 封面:", DST, f"({os.path.getsize(DST)} 字节, {W}x{H})")


if __name__ == "__main__":
    main()
