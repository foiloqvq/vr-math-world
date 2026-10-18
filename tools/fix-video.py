#!/usr/bin/env python3
"""自动修片：把常见导出发行问题一次性修掉，产出交给 foilo 继续精剪。

修什么：
  · 响度 → -16 LUFS（B 站标准），真峰值压到 -1.5 dB（防削波）
  · 视频码率 → 12 Mbps（导出被压糊的补回来，只能补"不糊"，不能补细节）
  · 帧率 → 统一 30fps
  · 可选：剪掉开头/结尾的秒数（--trim-head / --trim-tail）

用法：
  python fix-video.py 输入.mp4
  python fix-video.py 输入.mp4 --trim-head 1.5 --trim-tail 2
"""
import argparse
import os
import subprocess

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"
FFPROBE = r"C:\yachiyo-tts\engine\ffprobe.exe"


def duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default="")
    ap.add_argument("--trim-head", type=float, default=0.0)
    ap.add_argument("--trim-tail", type=float, default=0.0)
    ap.add_argument("--lufs", type=float, default=-16.0)
    ap.add_argument("--bitrate", default="12M")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    src = os.path.abspath(args.input)
    if not os.path.exists(src):
        raise SystemExit("找不到文件: " + src)

    dur = duration(src)
    keep = max(0.1, dur - args.trim_head - args.trim_tail)
    out = args.out or os.path.join(os.path.dirname(src),
                                   os.path.splitext(os.path.basename(src))[0] + "-修正版.mp4")

    af = (f"loudnorm=I={args.lufs}:TP=-1.5:LRA=11,"
          f"alimiter=limit=0.84:level=false")
    vf = f"fps={args.fps},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"

    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
    if args.trim_head > 0:
        cmd += ["-ss", f"{args.trim_head}"]
    cmd += ["-i", src, "-t", f"{keep}" if (args.trim_head or args.trim_tail) else f"{dur}",
            "-vf", vf, "-c:v", "h264_mf", "-b:v", args.bitrate,
            "-pix_fmt", "yuv420p", "-af", af, "-c:a", "aac", "-b:a", "256k",
            "-movflags", "+faststart", out]

    print("开始修复：", os.path.basename(src), f"（{dur:.1f}s → {keep:.1f}s）")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ 失败：", r.stderr[-600:])
        raise SystemExit(1)
    print("✅ 输出：", out, f"({os.path.getsize(out) / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
