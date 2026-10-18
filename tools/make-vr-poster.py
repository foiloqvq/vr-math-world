#!/usr/bin/env python3
"""生成 VR 里的「项目导图板」贴图 → unity/Assets/Resources/Art/ProjectMap.png

尺寸 2048×1280（16:10），深色底、按分支上色、根在左、分支向右展开。
用法：python make-vr-poster.py
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONTB = r"C:\Windows\Fonts\msyhbd.ttc"
BG = (10, 14, 24)
BG2 = (13, 18, 30)
FG = (232, 240, 255)
DIM = (140, 158, 186)

BRANCHES = [
    ("主线 · 可以走进去的数学世界", (110, 230, 235), [
        "复变函数图版 · 颜色=辐角",
        "黎曼面 · √z 的两层",
        "分数地砖 · 踩上去体感分母",
        "斜率斜坡 · k 越大越累",
    ]),
    ("视频线", (255, 208, 96), [
        "已发布 EP01 / EP02 / EP03",
        "待发布 EP04 费马点",
        "待发布 EP05 黎曼面",
        "工具链 · 2D / Blender 3D",
    ]),
    ("工具链 · 审片与发布", (255, 158, 199), [
        "连环画审片 · 响度频谱",
        "本地转写 · faster-whisper",
        "修片 -16 LUFS / 12Mbps",
        "B 站自动化 · CDP 上传",
    ]),
    ("形象 · 站点 · 私库", (150, 190, 255), [
        "大肥鱼 · 水手服 5 表情",
        "作品站 · GitHub Pages",
        "私库 · 记忆/日记/队列",
        "插件 · 语音 + 灵枢",
    ]),
]


def font(sz, bold=True):
    for p in ((FONTB, FONT) if bold else (FONT, FONTB)):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    default = r"C:\Users\nb666\Documents\deepseek-harness\default-workspace\vr-math-world\unity\Assets\Resources\Art\ProjectMap.png"
    ap.add_argument("--out", default=default)
    args = ap.parse_args()

    W, H = 2048, 1280
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 背景网格 + 光晕
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(16, 21, 33))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(16, 21, 33))
    for r in range(520, 40, -40):
        a = int(10 * (1 - r / 520))
        d.ellipse([140 - r, H // 2 - r, 140 + r, H // 2 + r], outline=(20 + a, 40 + a, 60 + a))

    # 标题
    d.text((96, 70), "VR Math World", font=font(78), fill=FG)
    d.text((100, 168), "项目地图 · 一个可以走进去的数学世界", font=font(38, False), fill=(110, 230, 235))
    d.line([(96, 232), (W - 96, 232)], fill=(30, 42, 64), width=2)

    # 根节点
    root_cx, root_cy = 290, 720
    d.ellipse([root_cx - 120, root_cy - 120, root_cx + 120, root_cy + 120],
              fill=(18, 30, 48), outline=(90, 130, 175), width=4)
    d.text((root_cx, root_cy - 16), "VR", font=font(56), fill=FG, anchor="mm")
    d.text((root_cx, root_cy + 44), "Math World", font=font(30, False), fill=(110, 230, 235), anchor="mm")

    # 四个分支：右侧两列摆
    cols_x = [560, 1300]
    top_y = [300, 700]
    slot_h = 76
    for i, (title, color, items) in enumerate(BRANCHES):
        cx = cols_x[i % 2]
        cy = top_y[i // 2]
        # 连线（从根到分支）
        d.line([(root_cx + 120, root_cy), (cx - 26, cy + 26)], fill=(38, 54, 80), width=3)
        # 分支标题条
        tw = d.textlength(title, font=font(34))
        d.rounded_rectangle([cx - 20, cy - 14, cx + max(tw, 320) + 26, cy + 62], radius=12,
                            fill=(15, 22, 36), outline=color, width=3)
        d.text((cx + 2, cy + 6), title, font=font(34), fill=color)
        # 子项
        for j, it in enumerate(items):
            y = cy + 96 + j * slot_h
            d.line([(cx - 4, y + 20), (cx + 26, y + 20)], fill=color, width=2)
            d.ellipse([cx + 22, y + 14, cx + 34, y + 26], fill=color)
            d.text((cx + 48, y), it, font=font(30, False), fill=(214, 226, 245))

    # 页脚
    d.line([(96, H - 96), (W - 96, H - 96)], fill=(30, 42, 64), width=2)
    d.text((96, H - 74), "foilo qvq × 大肥鱼（AI 助手） · 世界还在长", font=font(28, False), fill=DIM)
    d.text((W - 96, H - 74), "EP0X · 数学/科学/历史科学", font=font(28, False), fill=DIM, anchor="ra")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    img.save(args.out)
    print("已生成:", args.out, f"({os.path.getsize(args.out)} 字节, {W}x{H})")


if __name__ == "__main__":
    main()
