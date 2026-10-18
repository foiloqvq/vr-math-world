#!/usr/bin/env python3
"""EP05《黎曼面》—— 2D 讲概念 + Blender 渲的 3D 转台收尾。

素材：
  · docs/video/audio/ep05/line01..08.wav   （配音）
  · assets/3d/riemann/f_0001.png ...       （Blender 渲的 150 帧转台）

用法：python make-ep05.py [--no-subs] [--out 路径]
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
W, H, FPS = 1280, 720, 30
BG = (5, 8, 14)
FG = (240, 246, 255)
CYA = (110, 230, 235)
YEL = (255, 208, 96)
RED = (255, 118, 118)
DIM = (130, 148, 175)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MASCOT_DIR = os.path.join(REPO, "docs", "character", "art")
FRAMES3D = os.path.join(REPO, "assets", "3d", "riemann")


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


def paste_mascot(img, cx, cy, h=170, expr="happy"):
    p = os.path.join(MASCOT_DIR, f"大肥鱼-水手服-{expr}.png")
    if not os.path.exists(p):
        return img
    m = Image.open(p).convert("RGBA")
    arr = np.array(m.convert("RGB")).astype(np.float32)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    alpha = np.clip((lum - 16.0) / 26.0, 0, 1) * 255
    m.putalpha(Image.fromarray(alpha.astype(np.uint8), "L"))
    k = h / m.height
    m = m.resize((max(1, int(m.width * k)), h), Image.LANCZOS)
    canvas = img.convert("RGBA")
    canvas.alpha_composite(m, (int(cx - m.width / 2), int(cy - m.height / 2)))
    return canvas.convert("RGB")


def base_img():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for gx in range(0, W, 64):
        d.line([(gx, 0), (gx, H)], fill=(9, 12, 19))
    for gy in range(0, H, 64):
        d.line([(0, gy), (W, gy)], fill=(9, 12, 19))
    return img, d


# ---------------- 2D 分镜 ----------------
def f_hook(t, dur):
    img, d = base_img()
    center(d, (W // 2, 240), "√-1 = ?", font(96, True), CYA)
    if t > 0.7:
        center(d, (W // 2, 360), "答案 1 个？还是 2 个？", font(34), YEL)
    return img


def f_two(t, dur):
    img, d = base_img()
    cx, cy = W // 2, 300
    d.ellipse([cx - 190, cy - 190, cx + 190, cy + 190], outline=(90, 110, 140), width=3)
    d.line([(cx - 220, cy), (cx + 220, cy)], fill=(60, 74, 96), width=2)
    d.line([(cx, cy - 220), (cx, cy + 220)], fill=(60, 74, 96), width=2)
    for ang, col, label in ((math.pi / 2, YEL, "i"), (-math.pi / 2, RED, "-i")):
        x = cx + 150 * math.cos(ang)
        y = cy - 150 * math.sin(ang)
        g = min(1.0, t / 1.2)
        d.ellipse([cx + (x - cx) * g - 14, cy + (y - cy) * g - 14,
                   cx + (x - cx) * g + 14, cy + (y - cy) * g + 14], fill=col)
        if g >= 1:
            d.text((x + 20, y - 14), label, font=font(34, True), fill=col)
    return img


def f_loop(t, dur):
    img, d = base_img()
    cx, cy = W // 2, 310
    r = 150
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(70, 88, 116), width=3)
    prog = min(1.0, t / (dur * 0.8))
    pts = []
    for i in range(int(180 * prog) + 2):
        a = math.pi * i / 90 * 2          # 两圈
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    if len(pts) > 1:
        d.line(pts, fill=CYA, width=5, joint="curve")
    if prog > 0.55:
        center(d, (W // 2, H - 190), "绕一圈 → 变了；绕两圈 → 回来了", font(28), YEL)
    return img


def f_multivalue(t, dur):
    img, d = base_img()
    center(d, (W // 2, 150), "多值函数", font(40, True), FG)
    # 一个输入 → 两个输出
    ix, iy = 300, 380
    d.ellipse([ix - 12, iy - 12, ix + 12, iy + 12], fill=CYA)
    d.text((ix - 8, iy - 44), "z", font=font(26, True), fill=CYA)
    for k, (dy, col, lab) in enumerate(((-110, YEL, "√z"), (110, RED, "-√z"))):
        g = min(1.0, max(0.0, t / 0.9 - k * 0.25))
        ex, ey = 980, iy + dy
        d.line([(ix, iy), (ix + (ex - ix) * g, iy + (ey - iy) * g)], fill=col, width=4)
        if g >= 1:
            d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill=col)
            d.text((ex + 20, ey - 14), lab, font=font(28, True), fill=col)
    center(d, (W // 2, H - 150), "两个答案，不是错，是本来就有两个", font(26), DIM)
    return img


def f_two_sheets(t, dur):
    img, d = base_img()
    center(d, (W // 2, 120), "把平面拆成两层", font(38, True), FG)
    for k, (y0, col, name) in enumerate(((250, CYA, "第 1 层"), (430, YEL, "第 2 层"))):
        g = min(1.0, max(0.0, t / 0.8 - k * 0.3))
        if g <= 0:
            continue
        x0 = 260 + (1 - g) * 200
        d.rounded_rectangle([x0, y0, x0 + 780, y0 + 120], radius=12,
                            outline=col, width=3, fill=(col[0] // 12, col[1] // 12, col[2] // 12))
        d.text((x0 + 24, y0 + 44), name, font=font(30, True), fill=col)
    return img


def f_turn_sheet(t, dur):
    img, d = base_img()
    center(d, (W // 2, 120), "每绕原点一圈，翻一层", font(36, True), FG)
    for k, y0 in enumerate((260, 440)):
        d.rounded_rectangle([300, y0, 560, y0 + 100], radius=10, outline=(90, 110, 140), width=3)
        d.text((320, y0 + 34), f"层 {k + 1}", font=font(26), fill=DIM)
    # 箭头：层1 → 层2 → 层1
    prog = min(1.0, t / (dur * 0.9))
    pairs = [(560, 310, 800, 310), (800, 310, 800, 490), (800, 490, 560, 490)]
    for i, (x1, y1, x2, y2) in enumerate(pairs):
        if prog > i / 3:
            g = min(1.0, (prog - i / 3) * 3)
            d.line([(x1, y1), (x1 + (x2 - x1) * g, y1 + (y2 - y1) * g)], fill=CYA, width=4)
    return img


def f_close(t, dur):
    img, d = base_img()
    center(d, (W // 2, 260), "绕两圈，才回到原处", font(46, True), FG)
    center(d, (W // 2, 340), "两层正好接上 —— 这就是黎曼面", font(28), CYA)
    return img


def f_3d(t, dur, frame_idx):
    """3D 段：直接用 Blender 渲的帧。"""
    name = os.path.join(FRAMES3D, f"f_{frame_idx:04d}.png")
    if os.path.exists(name):
        src = Image.open(name).convert("RGBA")
        tw, th = int(W * 0.94), int(H * 0.94)
        src = src.resize((tw, th), Image.LANCZOS)
        img, _ = base_img()
        canvas = img.convert("RGBA")
        canvas.alpha_composite(src, ((W - tw) // 2, (H - th) // 2))
        return canvas.convert("RGB")
    img, d = base_img()
    center(d, (W // 2, H // 2), "（3D 帧缺失）", font(30), RED)
    return img


def f_outro(t, dur):
    img, d = base_img()
    center(d, (W // 2, 230), "黎曼面", font(64, True), FG)
    center(d, (W // 2, 310), "让多值函数有了一个可以站的地方", font(26), CYA)
    img = paste_mascot(img, W - 200, H - 180, 300)
    d = ImageDraw.Draw(img)
    d.text((40, H - 60), "EP05 · 大肥鱼", font=font(24, True), fill=DIM)
    return img


SEGS = [f_hook, f_two, f_loop, f_multivalue, f_two_sheets, f_turn_sheet, f_3d, f_3d, f_close, f_outro]

SUBS = [
    ("一个数开平方，答案是不是只有一个？", "Does a square root have only one answer?"),
    ("不是。根号负一，有两个答案。", "No. sqrt(-1) has two."),
    ("更奇怪的是：绕两圈才回到原处。", "Weirdly, it takes two turns to come back."),
    ("这叫多值：一个输入，两个输出。", "That's multi-valued: one input, two outputs."),
    ("怎么办？把平面拆成两层。", "The fix: split the plane into two sheets."),
    ("每绕原点一圈，就翻到另一层。", "Each lap around zero flips you to the other sheet."),
    ("绕两圈才回来，两层正好接上。", "Two laps later, the sheets join up."),
    ("这个东西，叫黎曼面。", "This object is a Riemann surface."),
    ("这就是为什么 √z 有两个答案。", "That's why sqrt(z) has two answers."),
    ("我是大肥鱼，下期见。", "I'm DaFeiyu. See you next time."),
]


def read_wav(p):
    with wave.open(p, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr


def pick_encoder():
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return "mpeg4"
    for enc in ("h264_mf", "mpeg4"):
        if " " + enc + " " in out:
            return enc
    return "mpeg4"


def main():
    ap = argparse.ArgumentParser()
    home = os.path.expanduser("~")
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "EP05-黎曼面.mp4"))
    ap.add_argument("--no-subs", action="store_true")
    args = ap.parse_args()

    adir = os.path.join(REPO, "docs", "video", "audio", "ep05")
    lines = [os.path.join(adir, f"line{i:02d}.wav") for i in range(1, 9)]
    for p in lines:
        if not os.path.exists(p):
            raise SystemExit("缺配音: " + p)

    # 8 句配音 → 10 个画面段（第 7、8 段共用最后两句，都是 3D）
    pads = [0.35, 0.4, 0.35, 0.35, 0.4, 0.35, 0.5, 0.35, 0.4, 1.8]
    seg_line = [0, 1, 2, 3, 4, 5, 6, 7, 7, 7]   # 画面段 → 用第几句配音（最后几段复用）
    audio, dur_line, sr = [], [], None
    for p in lines:
        d, s = read_wav(p)
        sr = s
        audio.append(d)
        dur_line.append(len(d) / s)

    # 画面段时长 = 对应配音 + 间隔
    seg_dur = []
    for k in range(len(SEGS)):
        li = seg_line[k]
        pad = pads[k]
        seg_dur.append(dur_line[li] + pad)

    total = sum(seg_dur)
    # 音频轨：按画面段顺序铺（后三段共用最后一句，只铺一次）
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)
    placed = set()
    pos = 0.0
    for k, d_ in enumerate(seg_dur):
        li = seg_line[k]
        if li not in placed:
            st = int(pos * sr)
            track[st:st + len(audio[li])] += audio[li]
            placed.add(li)
        pos += d_

    wav_tmp = os.path.join(tempfile.gettempdir(), "ep05-audio.wav")
    with wave.open(wav_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())

    # 3D 帧：数一下有多少张
    f3 = sorted([f for f in os.listdir(FRAMES3D) if f.startswith("f_") and f.endswith(".png")]) if os.path.isdir(FRAMES3D) else []
    n3d = len(f3)

    outf = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(outf), exist_ok=True)
    enc = pick_encoder()
    cargs = ["-c:v", enc, "-b:v", "8M"] if enc == "h264_mf" else ["-c:v", "mpeg4", "-q:v", "3"]
    n_frames = int(total * FPS)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_tmp] + cargs + ["-pix_fmt", "yuv420p",
                                     "-vf", "scale=1920:1080:flags=lanczos", "-c:a", "aac", "-b:a", "192k",
                                     "-shortest", outf]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    f_zh, f_en = font(30, True), font(19, False)

    # 3D 段起止（第 7、8 段）
    t_start = sum(seg_dur[:6])
    t_end = t_start + seg_dur[6] + seg_dur[7]
    for i in range(n_frames):
        t = i / FPS
        k, acc = -1, 0.0
        for j, d_ in enumerate(seg_dur):
            if t < acc + d_:
                k = j
                break
            acc += d_
        if k < 0:
            k = len(seg_dur) - 1
        local = t - acc

        if t_start <= t < t_end and n3d:
            frac = (t - t_start) / max(1e-6, (t_end - t_start))
            idx = 1 + int(frac * (n3d - 1))
            img = f_3d(local, seg_dur[k], idx)
        else:
            img = SEGS[k](local, seg_dur[k])

        img = paste_mascot(img, W - 105, H - 205 + 5 * math.sin(t * 2.2), 170)
        if not args.no_subs:
            d2 = ImageDraw.Draw(img)
            zh, en = SUBS[k]
            tw = d2.textlength(zh, font=f_zh)
            d2.rectangle([(W - tw) / 2 - 18, H - 128, (W + tw) / 2 + 18, H - 24], fill=(0, 0, 0))
            d2.text((W / 2, H - 92), zh, font=f_zh, fill=FG, anchor="mm")
            d2.text((W / 2, H - 50), en, font=f_en, fill=(150, 170, 200), anchor="mm")
            d2.rectangle([0, H - 5, int(W * i / max(1, n_frames - 1)), H], fill=CYA)
            d2.text((40, H - 150), "EP05 · 大肥鱼", font=font(18, True), fill=(110, 130, 160))
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg 失败")
    print(f"完成：{outf}  {total:.1f} 秒 / {n_frames} 帧 / 3D 帧 {n3d} 张")


if __name__ == "__main__":
    main()
