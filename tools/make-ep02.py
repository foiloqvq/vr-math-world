#!/usr/bin/env python3
"""EP02《√2 被发现的那晚》渲染器 —— 复用 EP01 的管线（numpy/Pillow 画帧 + ffmpeg 合成）。

用法：python make-ep02.py [--out 路径.mp4]
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
W, H, FPS = 1280, 720, 24
BG = (10, 14, 24)
FG = (222, 234, 255)
ACCENT = (110, 230, 235)
GOLD = (255, 208, 96)
SEA = (40, 90, 160)

SQRT2 = "1.41421356237309504880168872420969807856967187537694"


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


def frame_intro(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # 海浪
    for k in range(4):
        y0 = 430 + k * 34
        pts = [(x, y0 + 16 * math.sin(x / 90.0 + t * 1.6 + k)) for x in range(0, W + 8, 8)]
        d.line(pts, fill=(20 + 18 * k, 50 + 22 * k, 96 + 26 * k), width=3)
    a = min(1.0, t / 0.7)
    center(d, (W // 2, 250), "√2", font(int(120 * a) + 1, True), tuple(int(c * a) for c in ACCENT))
    center(d, (W // 2, 350), "公元前 500 年", font(28), (150, 170, 200))
    return img


def frame_square(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    s = 300
    x0, y0 = (W - s) // 2 - 120, 180
    # 正方形
    d.rectangle([x0, y0, x0 + s, y0 + s], outline=(120, 170, 240), width=4)
    d.text((x0 + s // 2 - 10, y0 - 34), "1", font=font(30), fill=(150, 180, 220))
    d.text((x0 - 34, y0 + s // 2 - 12), "1", font=font(30), fill=(150, 180, 220))
    # 对角线（逐步画出）
    p = min(1.0, t / 1.6)
    xe, ye = x0 + s * p, y0 + s * p
    d.line([(x0, y0), (xe, ye)], fill=GOLD, width=6)
    if p >= 1.0:
        center(d, (x0 + s * 0.62, y0 + s * 0.42), "√2", font(44, True), GOLD)
    # 右侧滚动小数
    n = int(t * 14)
    txt = SQRT2[:max(2, min(len(SQRT2), n))]
    d.text((x0 + s + 60, y0 + 40), "√2 =", font=font(30), fill=ACCENT)
    d.text((x0 + s + 60, y0 + 86), txt, font=font(26), fill=(220, 235, 255))
    d.text((x0 + s + 60, y0 + 150), "① 写不成 a/b", font=font(24), fill=(255, 170, 120))
    d.text((x0 + s + 60, y0 + 190), "② 无限，不循环", font=font(24), fill=(255, 170, 120))
    return img


def frame_frac(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center(d, (W // 2, 90), "他们说：万物皆分数", font(38, True), FG)
    pairs = [(3, 2), (7, 5), (17, 12), (99, 70), (239, 169)]
    for i, (a, b) in enumerate(pairs):
        y = 200 + i * 82
        x = 300 + (i % 2) * 60
        d.text((x, y), f"{a}/{b}", font=font(40, True), fill=(200, 220, 255))
        # 逐个划掉
        if t > 0.6 * (i + 1):
            d.line([(x - 10, y + 22), (x + 120, y + 22)], fill=(255, 90, 90), width=5)
    if t > 3.2:
        center(d, (W // 2, H - 90), "……没有一个正好等于 √2", font(30), (255, 170, 120))
    return img


def frame_numberline(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    y = H // 2
    d.line([(80, y), (W - 80, y)], fill=(120, 150, 190), width=3)
    for i in range(0, 5):
        x = 80 + i * (W - 160) / 4
        d.line([(x, y - 12), (x, y + 12)], fill=(120, 150, 190), width=3)
        d.text((x - 8, y + 20), str(i), font=font(24), fill=(150, 175, 210))
    # √2 位置（1.414 → 约 1/4 处偏右）
    x2 = 80 + (1.4142 / 4) * (W - 160)
    d.ellipse([x2 - 10, y - 10, x2 + 10, y + 10], fill=GOLD)
    d.text((x2 - 20, y - 60), "√2", font=font(34, True), fill=GOLD)
    # 小数字滚动
    n = int(t * 10)
    center(d, (W // 2, 130), SQRT2[:max(2, min(len(SQRT2), n))], font(34), ACCENT)
    center(d, (W // 2, H - 90), "永远不循环，永远不重复", font(30), (200, 220, 255))
    return img


def draw_whale(d, cx, cy, s=0.32):
    body = (86, 156, 246)
    belly = (226, 240, 255)
    d.polygon([(cx - 96 * s, cy + 6 * s), (cx - 140 * s, cy - 40 * s), (cx - 120 * s, cy + 6 * s),
               (cx - 140 * s, cy + 52 * s)], fill=body)
    d.ellipse([cx - 112 * s, cy - 66 * s, cx + 96 * s, cy + 84 * s], fill=body)
    d.ellipse([cx - 74 * s, cy - 4 * s, cx + 76 * s, cy + 80 * s], fill=belly)
    d.ellipse([cx + 30 * s, cy - 26 * s, cx + 44 * s, cy - 6 * s], fill=(22, 30, 48))
    d.ellipse([cx + 34 * s, cy - 22 * s, cx + 40 * s, cy - 14 * s], fill=(255, 255, 255))
    d.ellipse([cx + 6 * s, cy + 10 * s, cx + 34 * s, cy + 26 * s], fill=(255, 150, 170))


def frame_outro(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    a = min(1.0, t / 0.7)
    center(d, (W // 2, 210), "无理数 ≠ 没道理", font(52, True), tuple(int(c * a) for c in FG))
    center(d, (W // 2, 290), "它只是没法用分数表达", font(28), ACCENT)
    draw_whale(d, W - 200, H - 160)
    center(d, (W // 2, H - 60), "大肥鱼代发 · AI 助手", font(22), (120, 130, 150))
    return img


def read_wav(p):
    with wave.open(p, "rb") as w:
        n, ch, sr, sw = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
        raw = w.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def pick_encoder():
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return "mpeg4"
    for enc, cargs in (("h264_mf", ["-c:v", "h264_mf", "-b:v", "5M"]),
                       ("mpeg4", ["-c:v", "mpeg4", "-q:v", "3"])):
        if (" " + enc + " ") not in out:
            continue
        test = os.path.join(tempfile.gettempdir(), "e2enc.mp4")
        try:
            r = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "64x64", "-r", "24", "-i", "-",
                                "-frames:v", "2"] + cargs + [test],
                               input=b"\x00" * (64 * 64 * 3 * 2), capture_output=True, timeout=30)
            if r.returncode == 0 and os.path.getsize(test) > 0:
                return enc
        except Exception:
            pass
    return "mpeg4"


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "EP02-根号二被发现的那晚.mp4"))
    ap.add_argument("--audio", default=os.path.join(os.path.dirname(__file__), "..", "docs", "video", "audio", "ep02"))
    args = ap.parse_args()

    audio_dir = os.path.abspath(args.audio)
    lines = [os.path.join(audio_dir, f"line{i:02d}.wav") for i in range(1, 8)]
    for p in lines:
        if not os.path.exists(p):
            raise SystemExit("缺少配音: " + p)

    pads = [0.8, 0.4, 0.5, 0.5, 0.5, 0.6, 1.8]
    track = []
    sr = None
    seg_dur = []
    audio = []
    for p, pad in zip(lines, pads):
        d, s = read_wav(p)
        sr = s
        audio.append(d)
        seg_dur.append(len(d) / s + pad)

    total = sum(seg_dur)
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)
    pos = 0.0
    for d, pad in zip(audio, pads):
        st = int(pos * sr)
        track[st:st + len(d)] += d
        pos += len(d) / sr + pad

    wav_tmp = os.path.join(tempfile.gettempdir(), "ep02-audio.wav")
    with wave.open(wav_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())

    subs = [
        "公元前五百年，有人因为一个数字被扔进了海里。",
        "那个数字是 √2。",
        "他证明了：正方形的对角线，写不成两个整数之比。",
        "学派说：万物皆分数。",
        "1.41421356… 永远不循环，永远不重复。",
        "所以它不叫「没道理」，叫「无理」。",
        "我是大肥鱼，下期走进黎曼面。",
    ]
    segs = [frame_intro, frame_square, frame_square, frame_frac, frame_numberline, frame_outro, frame_outro]

    enc = pick_encoder()
    print("编码器:", enc)
    cargs = ["-c:v", enc, "-b:v", "5M"] if enc == "h264_mf" else ["-c:v", "mpeg4", "-q:v", "3"]
    n_frames = int(total * FPS)
    outf = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(outf), exist_ok=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_tmp] + cargs + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", outf]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    f_sub = font(32)
    f_bar = font(20)
    for i in range(n_frames):
        t = i / FPS
        k, acc = -1, 0.0
        for j, d in enumerate(seg_dur):
            if t < acc + d:
                k = j
                break
            acc += d
        if k < 0:
            k = len(seg_dur) - 1
        local = t - acc
        img = segs[k](local, seg_dur[k])
        d2 = ImageDraw.Draw(img)
        sub = subs[k]
        tw = d2.textlength(sub, font=f_sub)
        d2.rectangle([(W - tw) / 2 - 18, H - 96, (W + tw) / 2 + 18, H - 26], fill=(8, 12, 20))
        d2.text((W / 2, H - 61), sub, font=f_sub, fill=FG, anchor="mm")
        d2.rectangle([0, H - 6, int(W * i / max(1, n_frames - 1)), H], fill=ACCENT)
        d2.text((W - 14, 12), "大肥鱼代劳", font=f_bar, fill=(90, 100, 120), anchor="ra")
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg 失败")
    print(f"完成：{outf}  {total:.1f} 秒 / {n_frames} 帧")


if __name__ == "__main__":
    main()
