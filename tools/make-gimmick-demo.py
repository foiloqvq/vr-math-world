#!/usr/bin/env python3
"""玩法 demo —— 把几种"短视频互动玩法"一次性演示出来（14 秒，1080p）。

四种玩法：
1. 弹幕式关键字飞入（关键字从右飘过，像弹幕）
2. 隐藏帧彩蛋（某 2 帧藏一个答案，暂停才看得清）
3. 进度条彩蛋（进度条里跑一行小字）
4. 结尾 A/B 选择（让观众在评论区站队 → 提高互动率）

用法：python make-gimmick-demo.py [--out 路径]
"""
import argparse
import math
import os
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONTB = r"C:\Windows\Fonts\msyhbd.ttc"
W, H, FPS = 1280, 720, 30          # 画布 720p，输出放大到 1080p
BG = (10, 14, 24)
FG = (226, 236, 255)
ACCENT = (110, 230, 235)
GOLD = (255, 208, 96)
DIM = (130, 150, 180)


def font(sz, bold=False):
    for p in ((FONTB, FONT) if bold else (FONT, FONTB)):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def center(d, xy, text, f, fill=FG):
    d.text(xy, text, font=f, fill=fill, anchor="mm")


def complex_panel(num, den, t, w, h):
    ys, xs = np.mgrid[0:h, 0:w]
    x = (xs / w - 0.5) * 6.0
    y = -(ys / h - 0.5) * 3.4
    r = np.hypot(x, y) + 1e-6
    th = np.arctan2(y, x)
    k = num / den
    hue = (th * k / (2 * math.pi)) % 1.0
    val = np.clip(0.18 + 0.5 * np.minimum(1.0, (r ** k) / 2.2), 0, 1)
    i = (hue * 6).astype(np.int32) % 6
    fr = hue * 6 - np.floor(hue * 6)
    q = 1 - fr
    r0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [1, q, 0, 0, fr], 1)
    g0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [fr, 1, 1, q, 0], 0)
    b0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [0, 0, fr, 1, 1], 0)
    rgb = np.stack([r0, g0, b0], axis=-1) * val[..., None]
    return Image.fromarray((rgb * 255).astype(np.uint8), "RGB")


def bg_dim(t, dim=0.72, power=(3, 2)):
    bg = complex_panel(power[0], power[1], t, W, H)
    return Image.blend(bg, Image.new("RGB", (W, H), BG), dim)


# ---------------- 玩法 1：弹幕飞入 ----------------
DANMAKU = [
    (0.4, "等等这颜色在转？", (120, 220, 255)),
    (1.6, "√2 到底多少位", (255, 210, 120)),
    (2.8, "暂停截图！有彩蛋", (255, 150, 170)),
]


def draw_danmaku(d, t):
    f = font(26, True)
    for t0, text, col in DANMAKU:
        if t < t0:
            continue
        prog = (t - t0) / 3.2
        if prog > 1.15:
            continue
        x = W + 40 - prog * (W + 380)
        y = 90 + (hash(text) % 60)
        d.text((x, y), text, font=f, fill=col)


# ---------------- 玩法 2：隐藏帧彩蛋 ----------------
def draw_easter_egg(img, frame_i, total):
    """第 40%~42% 的几帧藏答案：正常播放一闪而过，暂停才看清。"""
    lo, hi = int(total * 0.40), int(total * 0.42)
    if lo <= frame_i <= hi:
        d = ImageDraw.Draw(img)
        d.text((24, H - 120), "彩蛋：第 100 位是 7", font=font(20, False), fill=(90, 100, 120))
    return img


# ---------------- 玩法 3：进度条里跑小字 ----------------
def draw_progress_with_text(d, prog, text):
    d.rectangle([0, H - 6, int(W * prog), H], fill=ACCENT)
    if int(prog * W) > 260:
        d.text((14, H - 26), text, font=font(15, False), fill=(70, 80, 100))


# ---------------- 主画面 ----------------
def frame(t, total):
    img = bg_dim(t)
    d = ImageDraw.Draw(img)

    if t < 3.2:
        center(d, (W // 2, 300), "√2 = 1.41421356…", font(52, True), FG)
        center(d, (W // 2, 380), "它到底有几位？", font(30), ACCENT)
    elif t < 6.0:
        center(d, (W // 2, 300), "第 100 位是几？", font(56, True), GOLD)
        center(d, (W // 2, 390), "（暂停截图，画面里藏着答案）", font(26), DIM)
    elif t < 10.5:
        center(d, (W // 2, 260), "A：它写不完", font(44, True), FG)
        center(d, (W // 2, 340), "B：它能写完", font(44, True), FG)
        center(d, (W // 2, 430), "评论区站队 —— 你选哪个？", font(30), ACCENT)
    else:
        center(d, (W // 2, 290), "选 A 的扣 1，选 B 的扣 2", font(40, True), FG)
        center(d, (W // 2, 370), "下期揭晓：为什么它写不完", font(28), GOLD)

    draw_danmaku(d, t)
    return img


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "玩法demo.mp4"))
    args = ap.parse_args()

    total = 14.0
    n_frames = int(total * FPS)
    sr = 32000
    wav_tmp = os.path.join(tempfile.gettempdir(), "gimmick-demo.wav")
    with wave.open(wav_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.zeros(int(total * sr), dtype=np.int16).tobytes())

    outf = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(outf), exist_ok=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_tmp, "-c:v", "h264_mf", "-b:v", "5M",
           "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080:flags=lanczos",
           "-c:a", "aac", "-shortest", outf]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n_frames):
        t = i / FPS
        img = frame(t, total)
        img = draw_easter_egg(img, i, n_frames)
        d = ImageDraw.Draw(img)
        draw_progress_with_text(d, i / max(1, n_frames - 1), "大肥鱼代劳 · 暂停看看进度条")
        d.text((W - 14, 12), "玩法 demo", font=font(18, False), fill=(90, 100, 120), anchor="ra")
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg 失败")
    print(f"完成：{outf}  {total:.1f} 秒 / {n_frames} 帧")


if __name__ == "__main__":
    main()
