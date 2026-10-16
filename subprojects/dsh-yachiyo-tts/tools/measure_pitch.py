#!/usr/bin/env python3
"""音高稳定性测量：把"念到一半高低"变成数字。

用法:
  python measure_pitch.py --dir <分块wav目录>      # 每块一个 wav（按文件名排序）
  python measure_pitch.py --file long.wav --split 16   # 单文件按 N 秒切块

输出: 各块中位 f0、块边界台阶（半音）、整段跨度。
经验阈值: 边界台阶 > 0.6 半音基本能被人耳听出来。
"""
import argparse, glob, io, os, wave
import numpy as np


def load(path):
    with wave.open(path, "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def median_f0(x, sr, fmin=70, fmax=400, win=0.04, hop=0.02, min_clarity=0.3):
    """自相关法估计基频，返回语音帧的中位数。"""
    W, H = int(win * sr), int(hop * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    vals = []
    for i in range(0, max(1, len(x) - W), H):
        fr = x[i:i + W]
        if np.sqrt((fr ** 2).mean()) < 0.01:      # 静音帧
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, mode="full")[W - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        if not len(seg):
            continue
        k = int(np.argmax(seg)) + lo
        if ac[k] / ac[0] > min_clarity:
            vals.append(sr / k)
    return float(np.median(vals)) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--file")
    ap.add_argument("--split", type=float, default=16.0, help="单文件按多少秒切块")
    a = ap.parse_args()
    chunks = []
    if a.dir:
        chunks = [(os.path.basename(p), load(p)) for p in sorted(glob.glob(os.path.join(a.dir, "*.wav")))]
    elif a.file:
        x, sr = load(a.file)
        step = int(a.split * sr)
        for i in range(0, len(x), step):
            chunks.append(("#%d" % (i // step + 1), (x[i:i + step], sr)))
    if not chunks:
        print("没有输入（--dir 或 --file）"); return
    print("%-28s %8s %10s" % ("块", "时长s", "中位f0"))
    meds = []
    for name, (x, sr) in chunks:
        m = median_f0(x, sr)
        print("%-28s %8.2f %10s" % (name[:28], len(x) / sr, "%.0fHz" % m if m else "-"))
        if m: meds.append(m)
    if len(meds) > 1:
        jumps = [12 * np.log2(meds[i + 1] / meds[i]) for i in range(len(meds) - 1)]
        print("\n边界台阶(半音): %s" % " ".join("%+.2f" % j for j in jumps))
        print("最大台阶 %.2f 半音   整段跨度 %.2f 半音" % (
            max(abs(j) for j in jumps), 12 * np.log2(max(meds) / min(meds))))


if __name__ == "__main__":
    main()