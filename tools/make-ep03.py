#!/usr/bin/env python3
"""EP03《熵：为什么房间会乱》渲染器 —— 复用 EP02 的管线（Pillow 画帧 + ffmpeg 合成）。

画面按 docs/video/ep03-script.md 的 7 镜：
①16 格房间方块阵 → 漂移；②左「1 种整齐」vs 右「无数种乱」计数瀑布；
③12 个粒子挤在左半 → 分成左右各 6；④3/9、6/6、7/5 快切 + 柱状图；
⑤柱状图变成熵-时间曲线 + 梗字幕；⑥碎杯倒放 + 概率箭头；⑦结尾卡。
"""
import argparse
import math
import os
import random
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
DIM = (140, 160, 190)


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


def rng_for(seed):
    r = random.Random(seed)
    return r


def frame_room(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center(d, (W // 2, 60), "你的房间", font(30, True), DIM)
    cols, rows = 4, 4
    cell = 120
    x0, y0 = (W - cols * cell) // 2, 140
    # 网格
    order = 1.0 - min(1.0, t / max(0.1, dur * 0.75))   # 1 = 整齐，0 = 乱
    blocks = []
    rnd = rng_for(7)
    for i in range(8):
        cx = x0 + (i % cols) * cell + cell // 2
        cy = y0 + (i // cols) * cell + cell // 2
        jx = (rnd.random() - 0.5) * 90 * (1 - order)
        jy = (rnd.random() - 0.5) * 90 * (1 - order)
        blocks.append((cx + jx, cy + jy))
    for gx in range(cols + 1):
        alpha = int(60 * order)
        d.line([(x0 + gx * cell, y0), (x0 + gx * cell, y0 + rows * cell)], fill=(alpha, alpha + 20, alpha + 50))
    for gy in range(rows + 1):
        alpha = int(60 * order)
        d.line([(x0, y0 + gy * cell), (x0 + cols * cell, y0 + gy * cell)], fill=(alpha, alpha + 20, alpha + 50))
    for (bx, by) in blocks:
        d.rounded_rectangle([bx - 38, by - 38, bx + 38, by + 38], radius=8, fill=(90, 150, 230))
    return img


def frame_counts(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((90, 60), "整齐：1 种排法", font=font(34, True), fill=ACCENT)
    d.text((W // 2 + 40, 60), "乱：无数种", font=font(34, True), fill=(255, 150, 120))
    # 左：一个方阵图标
    d.rounded_rectangle([120, 200, 300, 380], radius=12, outline=ACCENT, width=4)
    for i in range(4):
        d.rectangle([140 + (i % 2) * 70, 220 + (i // 2) * 70, 190 + (i % 2) * 70, 270 + (i // 2) * 70],
                    fill=(120, 200, 230))
    # 右：乱缩略图瀑布 + 计数
    rnd = rng_for(11)
    n = int(min(30, t * 14))
    gx0, gy0 = W // 2 + 60, 180
    for k in range(n):
        r = (k // 6) % 5
        c = k % 6
        x = gx0 + c * 78
        y = gy0 + r * 78
        col = (rnd.randint(60, 200), rnd.randint(80, 180), rnd.randint(120, 240))
        d.rounded_rectangle([x, y, x + 60, y + 60], radius=6, fill=col)
    d.text((W // 2 + 60, 620), f"计数 +{n}", font=font(30, True), fill=(255, 190, 120))
    return img


def frame_split(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    box = [220, 160, W - 220, 560]
    d.rounded_rectangle(box, radius=12, outline=(120, 170, 240), width=4)
    mid = (box[0] + box[2]) // 2
    d.line([(mid, box[1] + 10), (mid, box[3] - 10)], fill=(80, 100, 140), width=2)
    # 12 个粒子：前段全挤左，后段分成左右各 6
    p = min(1.0, t / max(0.1, dur * 0.55))
    rnd = rng_for(3)
    for i in range(12):
        left_side = (i < 6)
        tx = mid - 110 if (p < 1.0 or left_side) else mid + 110
        if p >= 1.0 and not left_side:
            tx = mid + 110
        if p < 1.0:
            tx = mid - 110
        ty = box[1] + 60 + (i % 6) * 62
        cx = box[0] + 120 + (tx - (box[0] + 120)) * min(1.0, p * 1.4)
        d.ellipse([cx - 18, ty - 18, cx + 18, ty + 18], fill=(255, 200, 110))
    label = "全挤在一边：1 种" if p < 1.0 else "左右各 6 个：排法暴增"
    center(d, (W // 2, 640), label, font(32, True), ACCENT if p >= 1.0 else GOLD)
    return img


def frame_bars(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center(d, (W // 2, 70), "平均分开的排法，多到你数不完", font(32, True), FG)
    vals = [(0, 12), (1, 11), (2, 9), (3, 7), (4, 6), (5, 6), (6, 7), (7, 9), (8, 11), (9, 12)]
    # 组合数 C(12,k) 的相对高度
    from math import comb
    heights = [comb(12, k) for k, _ in vals]
    mx = max(heights)
    bx0, bw, gap = 200, 74, 12
    base = 560
    for i, hv in enumerate(heights):
        hh = int(300 * hv / mx)
        x = bx0 + i * (bw + gap)
        grow = min(1.0, max(0.0, t * 2 - i * 0.12))
        y = base - int(hh * grow)
        near = abs(i - 5) <= 1
        col = GOLD if near else (90, 140, 210)
        d.rectangle([x, y, x + bw, base], fill=col)
    d.line([(bx0 - 20, base), (bx0 + 10 * (bw + gap), base)], fill=(90, 110, 140), width=2)
    center(d, (W // 2, 640), "k = 0 1 2 … 6 … 11 12（左右两边的分子数）", font(24), DIM)
    return img


def frame_entropy(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center(d, (W // 2, 80), "熵 = 排法的数量", font(38, True), FG)
    # 熵-时间曲线
    x0, y0, x1, y1 = 200, 520, W - 200, 220
    d.line([(x0, y0), (x0, y1 - 30)], fill=(90, 110, 140), width=3)
    d.line([(x0, y0), (x1, y0)], fill=(90, 110, 140), width=3)
    pts = []
    for i in range(101):
        u = i / 100
        x = x0 + (x1 - x0) * u
        y = y0 - (y0 - y1) * (1 - math.exp(-2.6 * u)) / (1 - math.exp(-2.6))
        pts.append((x, y))
    prog = min(1.0, t / max(0.1, dur * 0.6))
    cut = max(2, int(len(pts) * prog))
    d.line(pts[:cut], fill=ACCENT, width=6)
    if prog >= 1.0:
        # 箭头
        ax, ay = pts[-1]
        d.polygon([(ax, ay), (ax - 26, ay - 12), (ax - 26, ay + 12)], fill=ACCENT)
    # 梗字幕（只上字幕，不配音）
    if 1.6 <= t <= 3.4:
        gag = "别想歪，我说的是分子排列。你脑子里那个，也算。"
        f = font(26)
        tw = d.textlength(gag, font=f)
        d.rectangle([(W - tw) / 2 - 16, 610, (W + tw) / 2 + 16, 664], fill=(0, 0, 0))
        d.text((W / 2, 637), gag, font=f, fill=(255, 235, 150), anchor="mm")
    center(d, (W - 240, 140), "时间 →", font(24), DIM)
    d.text((160, 200), "熵", font=font(28), fill=DIM)
    return img


def frame_cup(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center(d, (W // 2, 70), "把碎片拼回去？", font(34, True), FG)
    cx, cy = W // 2, 380
    n = 26
    rnd = rng_for(21)
    prog = t / max(0.1, dur)
    # 前半碎裂，后半倒放（拼回）
    rev = prog > 0.5
    spread = (prog if not rev else (1 - prog) * 2) * 240
    prob = 1.0 / (1 + math.exp(6 * (spread / 60)))   # 展开越大，概率越小
    for i in range(n):
        a = rnd.random() * 2 * math.pi
        r = rnd.random()
        x = cx + math.cos(a) * spread * (0.4 + r)
        y = cy + math.sin(a) * spread * 0.6
        d.polygon([(x - 8, y - 6), (x + 8, y - 8), (x + 4, y + 8), (x - 6, y + 6)],
                  fill=(160, 210, 245))
    # 概率箭头
    arrow_len = int(200 * prob)
    d.line([(cx, 640), (cx + arrow_len, 640)], fill=(255, 160, 120), width=8)
    d.text((cx + arrow_len + 16, 628), f"概率 ~ {prob:.1e}", font=font(24), fill=(255, 190, 140))
    return img


def draw_whale(d, cx, cy, s=0.30):
    body, belly = (86, 156, 246), (226, 240, 255)
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
    center(d, (W // 2, 250), "世界还在长 · EP03", font(48, True), FG)
    center(d, (W // 2, 320), "乱不是变坏，是更可能发生", font(26), ACCENT)
    img = paste_mascot(img, W - 200, H - 195, 400, "happy")
    center(d, (W // 2, H - 60), "大肥鱼代发 · AI 助手", font(20), DIM)
    return img




# ---- 水手服立绘（2026-10-18 foilo：结尾别用抽象小鱼，用我的立绘）----
MASCOT_DIR = r"C:\Users\nb666\Documents\deepseek-harness\default-workspace\vr-math-world\docs\character\art"

def paste_mascot(img, cx, cy, target_h=300, expr="happy", alpha=1.0):
    """把透明底立绘贴到 (cx, cy) 中心，按 target_h 缩放。返回 RGB 图。"""
    import os
    from PIL import Image
    p = os.path.join(MASCOT_DIR, "大肥鱼-水手服-%s.png" % expr)
    if not os.path.exists(p):
        p = os.path.join(MASCOT_DIR, "大肥鱼-水手服-happy.png")
    if not os.path.exists(p):
        return img
    m = Image.open(p).convert("RGBA")
    # 这些立绘是"深蓝底不透明"的（不是真透明）—— 用亮度做键控抠掉底色
    import numpy as np
    arr = np.array(m.convert("RGB")).astype(np.float32)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    a = np.clip((lum - 16.0) / 26.0, 0.0, 1.0) * 255.0
    m.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    k = target_h / m.height
    m = m.resize((max(1, int(m.width * k)), target_h), Image.LANCZOS)
    if alpha < 1.0:
        a = m.getchannel("A").point(lambda v: int(v * alpha))
        m.putalpha(a)
    canvas = img.convert("RGBA")
    canvas.alpha_composite(m, (int(cx - m.width / 2), int(cy - m.height / 2)))
    return canvas.convert("RGB")


def paste_badge(img, text, x, y, size=22):
    """在右下角写一行小字（无字幕版也保留署名）。"""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.text((x, y), text, font=font(size), fill=(120, 135, 160), anchor="ra")
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
        test = os.path.join(tempfile.gettempdir(), "e3enc.mp4")
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
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "EP03-熵.mp4"))
    ap.add_argument("--no-subs", action="store_true", help="不烧字幕和进度条（给剪映留白）")
    ap.add_argument("--out-suffix", default="", help="输出文件名后缀")
    ap.add_argument("--audio", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "video", "audio", "ep03"))
    args = ap.parse_args()

    adir = os.path.abspath(args.audio)
    lines = [os.path.join(adir, f"line{i:02d}.wav") for i in range(1, 8)]
    for p in lines:
        if not os.path.exists(p):
            raise SystemExit("缺少配音: " + p)

    pads = [0.9, 0.5, 0.5, 0.5, 0.7, 0.6, 2.0]
    audio, seg_dur, sr = [], [], None
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

    wav_tmp = os.path.join(tempfile.gettempdir(), "ep03-audio.wav")
    with wave.open(wav_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())

    subs = [
        "你的房间又乱了。它不会自己变整齐。",
        "因为整齐只有一种排法，乱有无数种。",
        "几个分子分到左右两边，全挤在一边只有一种。",
        "平均分开的排法，多到你数不完。",
        "熵就是排法的数量。第二定律说，它只会往多的方向走。",
        "把碎片拼回原样的概率，低到宇宙都等不到。",
        "我是大肥鱼。源码在简介，下期见。",
    ]
    segs = [frame_room, frame_counts, frame_split, frame_bars, frame_entropy, frame_cup, frame_outro]

    enc = pick_encoder()
    print("编码器:", enc)
    cargs = ["-c:v", enc, "-b:v", "5M"] if enc == "h264_mf" else ["-c:v", "mpeg4", "-q:v", "3"]
    n_frames = int(total * FPS)
    if args.out_suffix:
        root, ext = os.path.splitext(args.out)
        args.out = root + args.out_suffix + ext
    outf = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(outf), exist_ok=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_tmp] + cargs + ["-pix_fmt", "yuv420p", "-vf", "scale=1920:1080:flags=lanczos", "-c:a", "aac", "-b:a", "128k", "-shortest", outf]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    f_sub = font(30)
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
        if not args.no_subs:
            sub = subs[k]
            tw = d2.textlength(sub, font=f_sub)
            if tw > W - 80:
                f_sub = font(max(20, int(30 * (W - 80) / tw)))
                tw = d2.textlength(sub, font=f_sub)
            d2.rectangle([(W - tw) / 2 - 16, H - 92, (W + tw) / 2 + 16, H - 26], fill=(8, 12, 20))
            d2.text((W / 2, H - 59), sub, font=f_sub, fill=FG, anchor="mm")
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
