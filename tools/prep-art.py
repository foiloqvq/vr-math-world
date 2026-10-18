#!/usr/bin/env python3
"""把 foilo 画的图处理成视频可用素材（去底 → 裁边 → 统一高度）。

用法：
  python prep-art.py 输入.png                      # 单张
  python prep-art.py 目录/ --grid 3x3              # 九宫格总览切分
  python prep-art.py 目录/ --height 900            # 统一高度

输出：<同目录>/ready/<原名>-ready.png（透明底、裁到内容边界）
"""
import argparse
import os

import numpy as np
from PIL import Image

# 我们的深蓝底（10,14,24）和常见白底都要能抠
BG_CANDIDATES = [(10, 14, 24), (255, 255, 255), (0, 0, 0)]


def key_background(im, tol=34, soft=26):
    """把接近"四角颜色"的像素变透明（软过渡，避免锯齿）。"""
    im = im.convert("RGBA")
    arr = np.array(im).astype(np.float32)
    h, w = arr.shape[:2]
    # 取四角平均当作背景色
    corners = [arr[2, 2, :3], arr[2, w - 3, :3], arr[h - 3, 2, :3], arr[h - 3, w - 3, :3]]
    bg = np.mean(corners, axis=0)
    dist = np.linalg.norm(arr[:, :, :3] - bg, axis=2)
    alpha = np.clip((dist - tol) / soft, 0.0, 1.0) * 255.0
    # 如果原图已经有 alpha，就取最小值，别把已透明的又画回来
    alpha = np.minimum(alpha, arr[:, :, 3])
    arr[:, :, 3] = alpha
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def trim(im, pad=8):
    bbox = im.split()[3].point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    return im.crop((max(0, x0 - pad), max(0, y0 - pad),
                    min(im.width, x1 + pad), min(im.height, y1 + pad)))


def fit_height(im, h):
    k = h / im.height
    return im.resize((max(1, int(im.width * k)), h), Image.LANCZOS)


def process(path, outdir, height=None, grid=None):
    im = Image.open(path)
    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(outdir, exist_ok=True)
    outs = []
    pieces = []
    if grid:
        cols, rows = [int(x) for x in grid.lower().split("x")]
        w, h = im.size
        cw, ch = w // cols, h // rows
        for r in range(rows):
            for c in range(cols):
                pieces.append((f"{name}-{r + 1}{c + 1}", im.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))))
    else:
        pieces.append((name, im))

    for label, piece in pieces:
        out = trim(key_background(piece))
        if height:
            out = fit_height(out, height)
        dest = os.path.join(outdir, f"{label}-ready.png")
        out.save(dest)
        outs.append((dest, out.size))
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default="")
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--grid", default="")
    args = ap.parse_args()

    src = os.path.abspath(args.input)
    if os.path.isdir(src):
        files = [os.path.join(src, f) for f in sorted(os.listdir(src))
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    else:
        files = [src]

    for f in files:
        outdir = args.out or os.path.join(os.path.dirname(f), "ready")
        for dest, size in process(f, outdir, args.height or None, args.grid or None):
            print(f"✅ {dest}  {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
