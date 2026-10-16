#!/usr/bin/env python3
"""音频客观指标：响度 / 停顿底噪 / 毛刺 / 高频能量。

用法: python measure_audio.py --file a.wav [--file b.wav ...]
提示: 指标只作参考——务必与真机试听对齐一次再拿它做决策（见 docs/04）。
"""
import argparse, wave
import numpy as np


def analyze(path):
    with wave.open(path, "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    hop = int(0.01 * sr)
    rms = np.array([np.sqrt((x[i:i + hop] ** 2).mean() + 1e-12)
                    for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(rms)
    # 停顿底噪：能量最低的 10% 帧
    floor = float(np.mean(np.sort(db)[:max(1, len(db) // 10)]))
    # 毛刺：采样点突变计数（会被"更亮"影响，不是纯噪声指标）
    glitch = int((np.abs(np.diff(x)) > 0.25).sum())
    # 句中停顿：20~400ms 的静音段，且前后都有语音
    voiced = db > (db.max() - 28)
    gaps, start = 0, None
    for i, v in enumerate(voiced):
        if not v and start is None:
            start = i
        elif v and start is not None:
            if 0.02 <= (i - start) * 0.01 <= 0.4 and start > 3 and i < len(voiced) - 3:
                gaps += 1
            start = None
    return dict(dur=len(x) / sr, peak=db.max(), median=float(np.median(db)),
                floor=floor, glitch=glitch, gaps=gaps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", required=True)
    for f in ap.parse_args().file:
        m = analyze(f)
        print("%-40s 时长%6.2fs 峰值%7.1f 中位%7.1f 停顿底噪%7.1f dB 毛刺%5d 句中停顿%3d" % (
            f.split("\\")[-1][:40], m["dur"], m["peak"], m["median"], m["floor"], m["glitch"], m["gaps"]))


if __name__ == "__main__":
    main()