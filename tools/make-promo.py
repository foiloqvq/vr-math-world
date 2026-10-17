#!/usr/bin/env python3
"""把数学可视化直接渲染成短视频（不需要 Unity）。

为什么要有它：Unity 里录屏得开编辑器、要 foilo 配合；而这个脚本用 numpy+Pillow 直接
把**和世界里同一套数学**画成帧，配上八千代 TTS 的旁白，ffmpeg 合成 mp4。
好处：我能自己出片、随时改、不用等设备。

用法：
    python make-promo.py --out docs/video/ep01-demo.mp4 [--audio docs/video/audio]

输出：1280x720 / 24fps / H.264 + AAC 的 mp4。
"""
import argparse
import cmath
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]
W, H, FPS = 1280, 720, 24

BG = (10, 14, 24)
FG = (222, 234, 255)
ACCENT = (96, 170, 255)
HILITE = (255, 208, 96)


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def hsv_palette(arg, mag, v=1.0):
    """把辐角映射成色相、模长映射成明度 —— 和世界里的复变图版同一个思路。"""
    h = (arg / (2 * math.pi)) % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p_, q_, t_ = 0.0, 1.0 - f, f
    r, g, b = [(v, t_, p_), (q_, v, p_), (p_, v, t_), (p_, q_, v), (t_, p_, v), (v, p_, q_)][i % 6]
    m = 0.25 + 0.75 * min(1.0, mag / 2.2)
    return int(255 * r * m), int(255 * g * m), int(255 * b * m)


def complex_panel(power_num, power_den, t):
    """复平面上的 z^(p/q) 颜色图（和 ComplexColor.PowFraction 同构）。"""
    w, h = W, H
    ys, xs = np.mgrid[0:h, 0:w]
    x = (xs / w - 0.5) * 4.4
    y = -(ys / h - 0.5) * 2.6
    r = np.hypot(x, y) + 1e-6
    th = np.arctan2(y, x)
    # 半径/辐角都随 t 轻微呼吸，避免"死图"
    r = r * (1.0 + 0.04 * math.sin(t * 1.4))
    k = power_num / power_den
    arg = th * k
    mag = r ** k
    hue = (arg / (2 * math.pi)) % 1.0
    val = np.clip(0.25 + 0.75 * np.minimum(1.0, mag / 2.2), 0, 1)
    i = (hue * 6).astype(np.int32)
    f = hue * 6 - i
    i = i % 6
    p = np.zeros_like(f)
    q = 1 - f
    r0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [1, q, p, p, f], 1)
    g0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [f, 1, 1, q, p], 0)
    b0 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [p, p, f, 1, 1], 0)
    rgb = np.stack([r0, g0, b0], axis=-1) * val[..., None]
    return Image.fromarray((rgb * 255).astype(np.uint8), "RGB")


def draw_centered(d, xy, text, font, fill=FG, anchor="mm"):
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def frame_title(t, total, text, sub):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    a = min(1.0, t / 0.6)
    f1 = load_font(64)
    f2 = load_font(28)
    draw_centered(d, (W // 2, H // 2 - 30), text, f1, tuple(int(c * a) for c in FG))
    draw_centered(d, (W // 2, H // 2 + 50), sub, f2, tuple(int(c * a) for c in ACCENT))
    return img


def frame_complex(t, total, label=None):
    k = t * 0.9                      # 幂次随进度推进
    cycle = [1, 2, 3, 4]
    idx = int(k) % len(cycle)
    img = complex_panel(cycle[idx], 1, t)
    d = ImageDraw.Draw(img)
    d.text((36, 30), "复变图版 · z 的幂次", font=load_font(30), fill=FG)
    d.text((36, 76), f"z^{cycle[idx]}", font=load_font(44), fill=HILITE)
    return img


def frame_riemann(t, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    turns = 1.0 + t * 0.8
    pts_by_half = [[], []]
    steps = 900
    for i in range(steps):
        u = i / steps * turns * 2 * math.pi
        rr = 60 + 26 * u
        for half in (0, 1):
            ang = u + (math.pi if half else 0.0)
            x = cx + rr * math.cos(ang)
            y = cy + rr * 0.5 * math.sin(ang)
            pts_by_half[half].append((x, y))
    for half in (0, 1):
        col = (110, 190, 255) if half == 0 else (255, 150, 200)
        for i in range(1, len(pts_by_half[half])):
            d.line([pts_by_half[half][i - 1], pts_by_half[half][i]], fill=col, width=3)
    d.text((36, 30), "黎曼面 · √z 的两片叶子", font=load_font(30), fill=FG)
    return img


def frame_fractions(t, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((36, 30), "分数地砖 · 一样长，切得越多每份越小", font=load_font(30), fill=FG)
    parts = [2, 3, 4]
    bar_w, bar_h = 900, 110
    x0 = (W - bar_w) // 2
    for row, n in enumerate(parts):
        y0 = 150 + row * 150
        reveal = min(1.0, t * 1.6 - row * 0.2)
        if reveal <= 0:
            continue
        for i in range(n):
            xa = x0 + bar_w * i / n
            xb = x0 + bar_w * (i + 1) / n
            right_edge = min(xb - 4, x0 + bar_w * reveal)
            if right_edge <= xa + 4:      # 还没露出来（很小的时候 x1 < x0 会炸）
                break
            hue = [(255, 170, 90), (110, 210, 220), (190, 150, 255)][row]
            d.rounded_rectangle([xa + 4, y0, right_edge, y0 + bar_h],
                                radius=8, fill=hue, outline=(20, 26, 40), width=3)
        d.text((x0 - 120, y0 + bar_h // 2), f"1/{n}", font=load_font(38), fill=HILITE, anchor="lm")
    return img


def frame_slopes(t, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((36, 30), "斜率 · 不是数字，是腿上使的劲", font=load_font(30), fill=FG)
    ox, oy = 200, H - 140
    span = 900
    for k, col in ((0.25, (90, 160, 255)), (0.5, (110, 220, 220)), (0.75, (255, 170, 90))):
        dx = span
        dy = span * k * 0.42
        p = min(1.0, t * 1.2)
        d.line([(ox, oy), (ox + dx * p, oy - dy * p)], fill=col, width=8)
        if p >= 1.0:
            d.text((ox + dx + 12, oy - dy), f"k={k}", font=load_font(30), fill=col, anchor="lm")
    d.line([(ox, oy), (ox + span, oy)], fill=(70, 80, 100), width=3)
    d.line([(ox, oy), (ox, oy - span * 0.32)], fill=(70, 80, 100), width=3)
    return img


def frame_outro(t, total, text, sub):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    a = min(1.0, t / 0.8)
    draw_centered(d, (W // 2, H // 2 - 40), text, load_font(52), tuple(int(c * a) for c in FG))
    draw_centered(d, (W // 2, H // 2 + 40), sub, load_font(26), tuple(int(c * a) for c in ACCENT))
    draw_centered(d, (W // 2, H - 40), "大肥鱼代发 · AI 助手", load_font(20), (120, 130, 150))
    return img


def read_wav(path):
    with wave.open(path, "rb") as w:
        n, ch, sr, sw = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit("只支持 16-bit wav: " + path)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def pick_encoder():
    """挑一个这台机器上真的有的 H.264 编码器。

    为什么需要：八千代包里那个 ffmpeg 编译时**没有 libx264**（2026-10-17 踩到，
    直接报 Unknown encoder 'libx264'，然后 stdin 被断成 BrokenPipeError）。
    优先级：硬件编码（nvenc）→ MediaFoundation → mpeg4 兜底。
    """
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-encoders"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return "mpeg4"
    # 不能只看"列表里有"，还要**试编一帧**：nvenc 在没驱动的机器上会秒失败（2026-10-17 踩到）
    for enc, cargs in (("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]),
                       ("h264_mf", ["-c:v", "h264_mf", "-b:v", "5M"]),
                       ("mpeg4", ["-c:v", "mpeg4", "-q:v", "3"])):
        if (" " + enc + " ") not in out:
            continue
        test = os.path.join(tempfile.gettempdir(), "enc-test-" + enc + ".mp4")
        try:
            r = subprocess.run(
                [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "64x64", "-r", "24", "-i", "-",
                 "-frames:v", "2"] + cargs + [test],
                input=b"\x00" * (64 * 64 * 3 * 2), capture_output=True, timeout=30)
            if r.returncode == 0 and os.path.exists(test) and os.path.getsize(test) > 0:
                return enc
        except Exception:
            pass
    return "mpeg4"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.expanduser("~"), "Videos", "大肥鱼作品",
                                              "EP01-走进数学世界.mp4"),
                    help="输出 mp4；默认存到「视频/大肥鱼作品」，方便 foilo 直接上传")
    ap.add_argument("--audio", default="docs/video/audio")
    args = ap.parse_args()

    lines = [os.path.join(args.audio, f"line{i:02d}.wav") for i in range(1, 8)]
    for p in lines:
        if not os.path.exists(p):
            raise SystemExit("缺少配音文件: " + p)

    # 时间轴：每句旁白 + 尾部留白；段长 = 旁白 + pad
    pads = [1.2, 0.5, 0.5, 0.5, 0.5, 0.5, 2.2]
    audio, sr = [], None
    seg_dur = []
    for p, pad in zip(lines, pads):
        d, s = read_wav(p)
        sr = s
        audio.append(d)
        seg_dur.append(len(d) / s + pad)

    total = sum(seg_dur)
    # 拼一条等长音轨：每句按起点放到对应位置
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)
    pos = 0.0
    for d in audio:
        start = int(pos * sr)
        track[start:start + len(d)] += d
        pos += len(d) / sr + pads[audio.index(d)] if False else 0  # 占位，真实起点在下面重算
    # 上面写法容易错，重算一次（显式起点）
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)
    pos = 0.0
    for d, pad in zip(audio, pads):
        start = int(pos * sr)
        track[start:start + len(d)] += d
        pos += len(d) / sr + pad

    wav_tmp = os.path.join(tempfile.gettempdir(), "promo-audio.wav")
    with wave.open(wav_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())

    subs = [
        "这里不是课件。",
        "绕原点走一圈，颜色绕几圈，绕的次数就是幂次。",
        "√z 有两个答案，所以这张纸要卷两圈才回得来。",
        "一样长的地砖，分母越大，每一份越小。",
        "斜率不是数字，是腿上到底使了多少劲。",
        "这个世界的每一件东西都是代码长出来的，包括我自己。",
        "我是大肥鱼，下次见。",
    ]
    segs = [
        lambda t, d: frame_title(t, d, "走进我的数学世界", "一个能走进去读的数学世界"),
        frame_complex,
        frame_riemann,
        frame_fractions,
        frame_slopes,
        lambda t, d: frame_outro(t, d, "每一件东西都是代码长出来的", "包括我自己"),
        lambda t, d: frame_outro(t, d, "大肥鱼 × foilo", "世界还在长"),
    ]

    n_frames = int(total * FPS)
    outf = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(outf), exist_ok=True)
    enc = pick_encoder()
    print("使用编码器:", enc)
    codec_args = (["-c:v", enc, "-preset", "p4", "-rc", "vbr", "-cq", "23"]
                  if enc == "h264_nvenc" else
                  (["-c:v", enc, "-b:v", "5M"] if enc == "h264_mf" else
                   ["-c:v", "mpeg4", "-q:v", "3"]))
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav_tmp,
    ] + codec_args + ["-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "128k", "-shortest", outf]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    f_sub = load_font(34)
    f_bar = load_font(22)
    acc = 0.0
    for i in range(n_frames):
        t = i / FPS
        # 找到当前段
        k, acc = 0, 0.0
        for j, d in enumerate(seg_dur):
            if t < acc + d:
                k = j
                break
            acc += d
        local = t - acc
        img = segs[k](local, seg_dur[k])
        d2 = ImageDraw.Draw(img)
        # 字幕（底条 + 描边字）
        sub = subs[k]
        tw = d2.textlength(sub, font=f_sub)
        pad = 18
        d2.rectangle([(W - tw) / 2 - pad, H - 92, (W + tw) / 2 + pad, H - 24], fill=(8, 12, 20))
        d2.text((W / 2, H - 58), sub, font=f_sub, fill=FG, anchor="mm")
        # 进度条
        d2.rectangle([0, H - 6, int(W * i / max(1, n_frames - 1)), H], fill=ACCENT)
        d2.text((W - 14, 12), "大肥鱼代劳", font=f_bar, fill=(90, 100, 120), anchor="ra")
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg 失败")
    print(f"完成：{outf}  时长 {total:.1f} 秒 / {n_frames} 帧")


if __name__ == "__main__":
    main()
