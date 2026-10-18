#!/usr/bin/env python3
"""本地语音转写：视频/音频 → 文字 + SRT（大肥鱼的"耳朵"）。

用法：
  python transcribe.py 视频.mp4                 # 打印文字
  python transcribe.py 视频.mp4 --srt 输出.srt   # 顺便存字幕
  python transcribe.py 视频.mp4 --model medium   # 更准（慢 3 倍）
  python transcribe.py 视频.mp4 --compare 参考文本.txt   # 对比预期台词

实现：ffmpeg 先抽 16k 单声道 wav → faster-whisper（CPU int8）。
为什么先抽 wav：直接让 whisper 解视频会依赖 PyAV 版本，容易炸；抽成 wav 最稳。
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import wave

import numpy as np

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"
MODEL_DIR = os.path.join(os.environ.get("USERPROFILE", "."), ".cache", "dafeiyu-asr")


def extract_wav(video, dest):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video,
                    "-vn", "-ac", "1", "-ar", "16000", dest], check=True)
    return dest


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return data, sr


def ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def normalize(t):
    t = re.sub(r"[，。！？、,.!?；;：:\"''（）()\s]", "", t or "")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--model", default="small", help="tiny / base / small / medium")
    ap.add_argument("--srt", default="")
    ap.add_argument("--compare", default="", help="参考文本文件（逐句对比，标出差异）")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--prompt", default="", help="给模型的提示词（默认空：塞词会污染输出）")
    args = ap.parse_args()

    src = os.path.abspath(args.input)
    if not os.path.exists(src):
        raise SystemExit("找不到文件: " + src)

    wav = os.path.join(tempfile.gettempdir(), "asr-input.wav")
    extract_wav(src, wav)
    audio, sr = read_wav(wav)

    os.makedirs(MODEL_DIR, exist_ok=True)
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8", download_root=MODEL_DIR)
    kw = dict(language=args.lang, vad_filter=True, beam_size=5)
    if args.prompt:
        kw["initial_prompt"] = args.prompt
    segments, info = model.transcribe(audio, **kw)

    lines = []
    for s in segments:
        text = (s.text or "").strip()
        if text:
            lines.append((s.start, s.end, text))

    print(f"== 转写（{args.model} / {info.language} / {info.duration:.1f}s 音频）==")
    for st, en, text in lines:
        print(f"[{st:6.2f}-{en:6.2f}] {text}")

    if args.srt:
        with open(args.srt, "w", encoding="utf-8") as f:
            for i, (st, en, text) in enumerate(lines, start=1):
                f.write(f"{i}\n{ts(st)} --> {ts(en)}\n{text}\n\n")
        print("已写字幕:", args.srt)

    if args.compare and os.path.exists(args.compare):
        ref = [l.strip() for l in open(args.compare, encoding="utf-8") if l.strip()]
        print("\n== 与预期台词对比 ==")
        for i in range(max(len(ref), len(lines))):
            r = normalize(ref[i]) if i < len(ref) else "（缺）"
            g = normalize(lines[i][2]) if i < len(lines) else "（缺）"
            if r == g:
                print(f"  {i+1}. ✅ {ref[i] if i < len(ref) else ''}")
            else:
                print(f"  {i+1}. ⚠️ 预期：{ref[i] if i < len(ref) else '（缺）'}")
                print(f"      识别：{lines[i][2] if i < len(lines) else '（缺）'}")

    if os.path.exists(wav):
        os.remove(wav)


if __name__ == "__main__":
    main()
