#!/usr/bin/env python3
"""EP04《费马点》渲染器 —— 按新配方：
  · 黑底极简 + 颜色即语义（PA 黄 / PB 蓝 / PC 红）
  · 每段一个信息单元（配音推进）
  · 道具：会滑入的刻度尺，实时显示 PA+PB+PC
  · 中英双语字幕（中文主字幕 + 英文小字）
  · 左下角系列编号 EP04 · 大肥鱼

用法：python make-ep04.py [--no-subs] [--out 路径]
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
W, H, FPS = 1280, 720, 30
BG = (4, 6, 10)
FG = (238, 244, 255)
DIM = (120, 138, 165)
YEL = (255, 208, 96)      # PA
BLU = (110, 170, 255)     # PB
RED = (255, 118, 118)     # PC
CYA = (110, 230, 235)

MASCOT_DIR = r"C:\Users\nb666\Documents\deepseek-harness\default-workspace\vr-math-world\docs\character\art"

A = (0.30 * W, 0.72 * H)
B = (0.70 * W, 0.72 * H)
C = (0.50 * W, 0.38 * H)


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


def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def fermat_point(a, b, c, iters=400):
    """数值求费马点（梯度下降，简单可靠）。若有角 >=120°，退回该顶点。"""
    angs = []
    pts = [a, b, c]
    for i in range(3):
        p, q, r = pts[i], pts[(i + 1) % 3], pts[(i + 2) % 3]
        v1 = (q[0] - p[0], q[1] - p[1])
        v2 = (r[0] - p[0], r[1] - p[1])
        angs.append(math.degrees(abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                           v1[0] * v2[0] + v1[1] * v2[1]))))
    for i, ang in enumerate(angs):
        if ang >= 120:
            return pts[i]
    x = (a[0] + b[0] + c[0]) / 3
    y = (a[1] + b[1] + c[1]) / 3
    # 标准梯度下降：sum |F-P| 的梯度是 sum (F-P)/|F-P|，步长小一点就稳
    for _ in range(3000):
        gx = gy = 0.0
        for p in pts:
            d = max(1e-6, dist((x, y), p))
            gx += (x - p[0]) / d
            gy += (y - p[1]) / d
        n = math.hypot(gx, gy)
        if n < 1e-6:
            break
        x -= 1.6 * gx
        y -= 1.6 * gy
        # 别跑出三角形包围盒
        x = min(max(x, min(a[0], b[0], c[0])), max(a[0], b[0], c[0]))
        y = min(max(y, min(a[1], b[1], c[1])), max(a[1], b[1], c[1]))
    return (x, y)


F = fermat_point(A, B, C)


def draw_triangle(d, a=A, b=B, c=C, width=3, col=(230, 236, 250)):
    d.line([a, b, c, a], fill=col, width=width, joint="curve")
    f = font(24, True)
    for p, name, off in ((a, "A", (-26, 12)), (b, "B", (18, 12)), (c, "C", (0, -26))):
        d.text((p[0] + off[0], p[1] + off[1]), name, font=f, fill=col)


def fog(t, seed=0):
    """极淡的星点背景，避免纯黑死板。"""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for i in range(70):
        x = rnd.random() * W
        y = rnd.random() * H
        s = 1 if rnd.random() < 0.8 else 2
        d.point((x, y), fill=(18 + int(14 * math.sin(t + i)), 20, 30))
    return img


def seg_frame(t, dur, idx):
    img = fog(t, idx)
    d = ImageDraw.Draw(img)
    return img, d


# ---------------- 各镜 ----------------
def f_village(t, dur):
    img, d = seg_frame(t, dur, 1)
    pts = [(0.24 * W, 0.62 * H), (0.76 * W, 0.62 * H), (0.50 * W, 0.28 * H)]
    for i, p in enumerate(pts):
        d.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], fill=(90, 130, 190))
        d.text((p[0] + 20, p[1] - 10), "村 " + "ABC"[i], font=font(22), fill=DIM)
    for i, j in ((0, 1), (1, 2), (2, 0)):
        d.line([pts[i], pts[j]], fill=(50, 62, 84), width=2)
    if t > 0.8:
        center(d, (W // 2, 0.47 * H), "?", font(64, True), CYA)
    return img


def f_point(t, dur):
    img = fog(t, 2)
    d = ImageDraw.Draw(img)
    draw_triangle(d)
    a = min(1.0, t / 1.2)
    r = 16 * a
    d.ellipse([F[0] - r, F[1] - r, F[0] + r, F[1] + r], fill=CYA)
    if a >= 1:
        d.text((F[0] + 16, F[1] - 8), "P", font=font(26, True), fill=CYA)
    return img


def f_segments(t, dur):
    img = fog(t, 3)
    d = ImageDraw.Draw(img)
    draw_triangle(d)
    grow = min(1.0, t / 1.5)
    for p, col in ((A, YEL), (B, BLU), (C, RED)):
        ex = F[0] + (p[0] - F[0]) * grow
        ey = F[1] + (p[1] - F[1]) * grow
        d.line([F, (ex, ey)], fill=col, width=5)
    d.ellipse([F[0] - 12, F[1] - 12, F[0] + 12, F[1] + 12], fill=CYA)
    total = (dist(F, A) + dist(F, B) + dist(F, C)) / 120.0
    center(d, (W // 2, H - 150), f"PA+PB+PC = {total:.2f}", font(30, True), CYA)
    for p, col, name in ((A, YEL, "PA"), (B, BLU, "PB"), (C, RED, "PC")):
        mx = (F[0] + p[0]) / 2
        my = (F[1] + p[1]) / 2
        d.text((mx, my), name, font=font(20, True), fill=col)
    return img


def f_ruler(t, dur):
    img = fog(t, 4)
    d = ImageDraw.Draw(img)
    draw_triangle(d)
    d.ellipse([F[0] - 12, F[1] - 12, F[0] + 12, F[1] + 12], fill=CYA)
    # 刻度尺从右侧滑入
    slide = min(1.0, t / 1.0)
    x0 = W - slide * (W - 160)
    y0 = H - 210
    w, h = W - 240, 46
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=6, fill=(16, 22, 34), outline=(70, 88, 118), width=2)
    for i in range(0, 21):
        x = x0 + 16 + i * (w - 32) / 20
        ln = 16 if i % 5 == 0 else 8
        d.line([(x, y0 + h - 6), (x, y0 + h - 6 - ln)], fill=(120, 140, 170), width=2)
    d.text((x0 + 12, y0 - 26), "量一量：谁最短？", font=font(22), fill=DIM)
    return img


def f_equi(t, dur):
    img = fog(t, 5)
    d = ImageDraw.Draw(img)
    draw_triangle(d, width=2, col=(120, 132, 152))

    def equi(p, q, out_dir):
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        hh = L * math.sqrt(3) / 2
        # 选朝外那一侧
        cx, cy = mx + nx * hh, my + ny * hh
        if (cx - out_dir[0]) ** 2 + (cy - out_dir[1]) ** 2 < (mx - out_dir[0]) ** 2 + (my - out_dir[1]) ** 2:
            cx, cy = mx - nx * hh, my - ny * hh
        return (cx, cy)

    centre = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
    sides = [(A, B), (B, C), (C, A)]
    cols = [(150, 190, 240), (150, 200, 230), (170, 190, 240)]
    for i, (p, q) in enumerate(sides):
        if t < 0.7 * i:
            continue
        grow = min(1.0, (t - 0.7 * i) / 0.9)
        vx, vy = equi(p, q, centre)
        # 顶点从边中点"长"出来
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        tx, ty = mx + (vx - mx) * grow, my + (vy - my) * grow
        d.line([p, (tx, ty), q], fill=cols[i], width=3)
        if grow >= 1:
            d.ellipse([tx - 8, ty - 8, tx + 8, ty + 8], fill=cols[i])
    return img


def f_connect(t, dur):
    img = fog(t, 6)
    d = ImageDraw.Draw(img)
    # 重画三个等边三角形（静态）
    tmp = f_equi(99, 1)
    img.paste(tmp, (0, 0))
    d = ImageDraw.Draw(img)
    draw_triangle(d, width=2, col=(120, 132, 152))
    centre = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)

    def equi(p, q):
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        hh = L * math.sqrt(3) / 2
        cx, cy = mx + nx * hh, my + ny * hh
        if (cx - centre[0]) ** 2 + (cy - centre[1]) ** 2 < (mx - centre[0]) ** 2 + (my - centre[1]) ** 2:
            cx, cy = mx - nx * hh, my - ny * hh
        return (cx, cy)

    pairs = [((A, B), C), ((B, C), A), ((C, A), B)]
    for i, ((p, q), opp) in enumerate(pairs):
        if t < 0.9 * i:
            continue
        v = equi(p, q)
        g = min(1.0, (t - 0.9 * i) / 0.8)
        d.line([v, (v[0] + (opp[0] - v[0]) * g, v[1] + (opp[1] - v[1]) * g)], fill=CYA, width=3)
    return img


def f_meet(t, dur):
    img = f_connect(99, 1)
    d = ImageDraw.Draw(img)
    pul = 1 + 0.15 * math.sin(t * 6)
    r = 18 * pul
    d.ellipse([F[0] - r, F[1] - r, F[0] + r, F[1] + r], fill=CYA)
    d.text((F[0] + 22, F[1] - 10), "费马点", font=font(24, True), fill=CYA)
    center(d, (W // 2, H - 150), "三条线的交点", font(28, True), FG)
    return img


def f_angle_cond(t, dur):
    img = fog(t, 8)
    d = ImageDraw.Draw(img)
    draw_triangle(d)
    # 三个角标角度
    angs = []
    pts = [A, B, C]
    for i in range(3):
        p, q, r = pts[i], pts[(i + 1) % 3], pts[(i + 2) % 3]
        v1 = (q[0] - p[0], q[1] - p[1])
        v2 = (r[0] - p[0], r[1] - p[1])
        a = math.degrees(abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                       v1[0] * v2[0] + v1[1] * v2[1])))
        angs.append(a)
    limit = min(1.0, t / 2.0) * 120
    for p, a, name in zip(pts, angs, "ABC"):
        col = RED if a >= 118 else (200, 214, 235)
        d.text((p[0] + 6, p[1] + 20), f"{name}={a:.0f}°", font=font(22, True), fill=col)
    center(d, (W // 2, H - 150), f"每个角都要 < {limit:.0f}°", font(30, True),
           RED if limit >= 119 else FG)
    return img


def f_obtuse(t, dur):
    img = fog(t, 9)
    d = ImageDraw.Draw(img)
    # 钝角三角形：C 向右拉远
    a = (0.14 * W, 0.80 * H)
    b = (0.86 * W, 0.80 * H)
    c = (0.72 * W, 0.34 * H)
    draw_triangle(d, a, b, c)
    f = fermat_point(a, b, c)
    d.ellipse([f[0] - 14, f[1] - 14, f[0] + 14, f[1] + 14], fill=RED)
    d.text((f[0] + 20, f[1] - 10), "费马点 = 顶点", font=font(24, True), fill=RED)
    center(d, (W // 2, H - 150), "有角 ≥ 120° 时，它就挪到那个顶点", font(28), FG)
    return img


def paste_mascot(img, cx, cy, target_h=280, expr="happy"):
    p = os.path.join(MASCOT_DIR, f"大肥鱼-水手服-{expr}.png")
    if not os.path.exists(p):
        return img
    m = Image.open(p).convert("RGBA")
    arr = np.array(m.convert("RGB")).astype(np.float32)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    alpha = np.clip((lum - 16.0) / 26.0, 0, 1) * 255
    m.putalpha(Image.fromarray(alpha.astype(np.uint8), "L"))
    k = target_h / m.height
    m = m.resize((max(1, int(m.width * k)), target_h), Image.LANCZOS)
    canvas = img.convert("RGBA")
    canvas.alpha_composite(m, (int(cx - m.width / 2), int(cy - m.height / 2)))
    return canvas.convert("RGB")


def f_outro(t, dur):
    img = fog(t, 10)
    d = ImageDraw.Draw(img)
    center(d, (W // 2, 250), "费马点", font(64, True), FG)
    center(d, (W // 2, 330), "三条线交于一点，省下一截管子", font(26), CYA)
    img = paste_mascot(img, W - 200, H - 180, 300)
    d = ImageDraw.Draw(img)
    d.text((40, H - 60), "EP04 · 大肥鱼", font=font(24, True), fill=DIM)
    d.text((W - 20, H - 40), "大肥鱼代发 · AI 助手", font=font(18), fill=(90, 100, 120), anchor="ra")
    return img


SEGS = [f_village, f_point, f_segments, f_ruler, f_equi, f_connect, f_meet, f_angle_cond, f_obtuse, f_outro]

SUBS = [
    ("三个村子要共用一个水站，管道怎么修最短？", "Three villages, one well: shortest pipes?"),
    ("答案在三角形里面，叫费马点。", "The answer sits inside: the Fermat point."),
    ("它到三个顶点的距离之和，是所有点里最小的。", "It minimizes PA + PB + PC."),
    ("怎么找？先说构造。", "How to find it? The construction."),
    ("每条边向外，作一个等边三角形。", "Build an equilateral triangle on each side."),
    ("再把新顶点和对面的顶点连起来。", "Link each new vertex to the opposite corner."),
    ("三条线交于一点，就是费马点。", "They meet at one point: the Fermat point."),
    ("不过有个前提：三个角都要小于一百二十度。", "Caveat: every angle must be under 120 deg."),
    ("哪个角超过一百二十度，费马点就挪到那个顶点。", "Over 120 deg? It moves to that vertex."),
    ("我是大肥鱼，下期讲旋转六十度。", "I'm DaFeiyu. Next: rotate by 60 deg."),
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
    ap.add_argument("--out", default=os.path.join(home, "Videos", "大肥鱼作品", "EP04-费马点.mp4"))
    ap.add_argument("--no-subs", action="store_true")
    ap.add_argument("--out-suffix", default="")
    args = ap.parse_args()

    adir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "video", "audio", "ep04")
    adir = os.path.abspath(adir)
    lines = [os.path.join(adir, f"line{i:02d}.wav") for i in range(1, 11)]
    for p in lines:
        if not os.path.exists(p):
            raise SystemExit("缺配音: " + p)

    pads = [0.35, 0.3, 0.4, 0.3, 0.3, 0.3, 0.5, 0.35, 0.4, 1.6]
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

    wav_tmp = os.path.join(tempfile.gettempdir(), "ep04-audio.wav")
    with wave.open(wav_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())

    if args.out_suffix:
        root, ext = os.path.splitext(args.out)
        args.out = root + args.out_suffix + ext
    outf = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(outf), exist_ok=True)

    enc = pick_encoder()
    cargs = ["-c:v", enc, "-b:v", "8M"] if enc == "h264_mf" else ["-c:v", "mpeg4", "-q:v", "3"]
    n_frames = int(total * FPS)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav_tmp] + cargs + ["-pix_fmt", "yuv420p", "-vf", "scale=1920:1080:flags=lanczos",
                                     "-c:a", "aac", "-b:a", "192k", "-shortest", outf]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    f_zh = font(30, True)
    f_en = font(19, False)
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
        img = SEGS[k](local, seg_dur[k])

        if not args.no_subs:
            d2 = ImageDraw.Draw(img)
            zh, en = SUBS[k]
            tw = d2.textlength(zh, font=f_zh)
            d2.rectangle([(W - tw) / 2 - 18, H - 128, (W + tw) / 2 + 18, H - 24], fill=(0, 0, 0))
            d2.text((W / 2, H - 92), zh, font=f_zh, fill=FG, anchor="mm")
            d2.text((W / 2, H - 50), en, font=f_en, fill=(150, 170, 200), anchor="mm")
            d2.rectangle([0, H - 5, int(W * i / max(1, n_frames - 1)), H], fill=CYA)
            d2.text((W - 16, 14), "EP04 · 大肥鱼", font=font(18, True), fill=(110, 130, 160), anchor="ra")
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg 失败")
    print(f"完成：{outf}  {total:.1f} 秒 / {n_frames} 帧")


if __name__ == "__main__":
    main()
