#!/usr/bin/env python3
"""审"音频"：把一条视频的声音量出数字 + 画出来（大肥鱼靠这个"听"）。

用法：python review-audio.py 视频.mp4 [--out 前缀]

输出：
  1. 响度：集成 LUFS、真峰值、峰值 dB、RMS dB      ← B 站建议 -16 LUFS，峰值 ≤ -1 dB
  2. 削波：有多少采样点贴顶（破音）
  3. 静音段：哪几段是"没声音"的（留白太长会掉完播）
  4. 配乐检测：低频能量占比 + 频谱平坦度 → 判断有没有 BGM
  5. 两张图：波形图 + 频谱图（保存成 png，大肥鱼直接看）
"""
import argparse
import json
import os
import re
import subprocess
import sys

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"


def run(args):
    return subprocess.run(args, capture_output=True, text=True, errors="replace")


def loudness(path):
    r = run([FFMPEG, "-hide_banner", "-i", path, "-af",
             "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        return {}
    return json.loads(m.group(0))


def astats(path):
    r = run([FFMPEG, "-hide_banner", "-i", path, "-af", "astats=metadata=1:reset=0", "-f", "null", "-"])
    out = {}
    for key, pat in (("peak_db", r"Peak level dB:\s*(-?[\d.]+)"),
                     ("rms_db", r"RMS level dB:\s*(-?[\d.]+)"),
                     ("flat_factor", r"Flat factor:\s*([\d.]+)"),
                     ("peak_count", r"Peak count:\s*(\d+)")):
        mm = re.search(pat, r.stderr)
        out[key] = float(mm.group(1)) if mm else None
    return out


def silence(path, thresh_db=-40, min_len=0.35):
    r = run([FFMPEG, "-hide_banner", "-i", path, "-af",
             f"silencedetect=noise={thresh_db}dB:d={min_len}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", r.stderr)]
    segs = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else None
        segs.append((s, e))
    return segs


def band_energy(path):
    """低频(<200Hz) 与中高频(200-4000Hz) 的能量比 —— 粗略判断有没有 BGM/鼓点。"""
    r = run([FFMPEG, "-hide_banner", "-i", path, "-af",
             "lowpass=f=200,astats=metadata=1:reset=0", "-f", "null", "-"])
    low = re.search(r"RMS level dB:\s*(-?[\d.]+)", r.stderr)
    r2 = run([FFMPEG, "-hide_banner", "-i", path, "-af",
              "highpass=f=200,lowpass=f=4000,astats=metadata=1:reset=0", "-f", "null", "-"])
    mid = re.search(r"RMS level dB:\s*(-?[\d.]+)", r2.stderr)
    if not low or not mid:
        return None
    return float(low.group(1)), float(mid.group(1))


def render_pngs(path, prefix):
    wav = os.path.join(os.path.dirname(prefix), os.path.basename(prefix) + ".wav")
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
         "-ac", "1", "-ar", "16000", wav])
    wave_png = prefix + "-波形.png"
    spec_png = prefix + "-频谱.png"
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", wav,
         "-filter_complex", "showwavespic=s=1600x360:colors=#6ee6eb", "-frames:v", "1", wave_png])
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", wav,
         "-lavfi", "showspectrumpic=s=1600x500:legend=1:color=intensity", spec_png])
    try:
        os.remove(wav)
    except OSError:
        pass
    return wave_png, spec_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    path = os.path.abspath(args.video)
    if not os.path.exists(path):
        raise SystemExit("找不到视频: " + path)

    prefix = args.out or os.path.join(os.path.dirname(path),
                                      "音频-" + os.path.splitext(os.path.basename(path))[0])

    print("== 响度 ==")
    L = loudness(path)
    if L:
        print(f"  集成响度 input_i = {L.get('input_i')} LUFS   （B 站建议 -16）")
        print(f"  真峰值   input_tp = {L.get('input_tp')} dBTP   （≤ -1 才安全）")
        print(f"  动态范围 input_lra = {L.get('input_lra')} LU")
        try:
            print(f"  建议增益：{float(-16.0) - float(L.get('input_i')):+.1f} dB")
        except (TypeError, ValueError):
            pass
    A = astats(path)
    print("== 峰值/削波 ==")
    print(f"  峰值 {A.get('peak_db')} dB / RMS {A.get('rms_db')} dB")
    if A.get("peak_db") is not None and A["peak_db"] > -0.5:
        print("  ⚠️ 峰值贴近 0 dB，有削波破音风险")
    if A.get("flat_factor") and A["flat_factor"] > 0:
        print(f"  ⚠️ flat factor = {A['flat_factor']}（有采样点被削平）")

    print("== 静音段（>-40dB 以下算静音，>0.35s 才报） ==")
    segs = silence(path)
    if not segs:
        print("  没有明显静音段 ✓")
    for s, e in segs:
        dur = (e - s) if e else None
        print(f"  {s:6.2f}s → " + (f"{e:6.2f}s（{dur:.2f}s）" if e else "直到结尾"))

    be = band_energy(path)
    if be:
        low, mid = be
        diff = low - mid
        verdict = "低频明显（很可能有 BGM / 鼓点）" if diff > -6 else "以人声为主，几乎没有配乐"
        print("== 配乐检测 ==")
        print(f"  低频(<200Hz) {low:.1f} dB  中高频 {mid:.1f} dB  差值 {diff:+.1f} dB")
        print(f"  判断：{verdict}")

    wave_png, spec_png = render_pngs(path, prefix)
    print("== 图 ==")
    print("  波形：", wave_png)
    print("  频谱：", spec_png)


if __name__ == "__main__":
    main()
