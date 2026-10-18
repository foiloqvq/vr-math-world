#!/usr/bin/env python3
"""审片工具：把一条视频抽成"连环画"（contact sheet），大肥鱼看着审。

用法：
  python review-video.py 视频.mp4 [--shots 12] [--out 输出.png]

输出：
  · 一张 N 帧拼图（每帧带时间戳），给大肥鱼直接看
  · 视频基础信息（分辨率 / 时长 / 码率 / 有没有音轨）
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"
FFPROBE = r"C:\yachiyo-tts\engine\ffprobe.exe"
FONT = r"C:\Windows\Fonts\msyh.ttc"


def probe(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffprobe 失败: " + r.stderr.strip()[:200])
    j = json.loads(r.stdout)
    dur = float(j["format"]["duration"])
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    info = {
        "时长": round(dur, 2),
        "分辨率": f'{v["width"]}x{v["height"]}' if v else "无视频流",
        "帧率": v.get("avg_frame_rate") if v else "-",
        "视频码率": int(v.get("bit_rate", 0)) // 1000 if v and v.get("bit_rate") else "-",
        "音轨": "有" if a else "❌ 没有音轨",
    }
    return dur, info


def grab(path, t, dest):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", dest],
                   capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--shots", type=int, default=12)
    ap.add_argument("--out", default="")
    ap.add_argument("--cols", type=int, default=4)
    args = ap.parse_args()

    path = os.path.abspath(args.video)
    if not os.path.exists(path):
        raise SystemExit("找不到视频: " + path)

    dur, info = probe(path)
    n = max(1, args.shots)
    cols = max(1, args.cols)
    rows = (n + cols - 1) // cols
    tw, th = 480, 270                      # 每格大小
    sheet = Image.new("RGB", (cols * tw, rows * th), (10, 14, 24))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(FONT, 20)
    except Exception:
        f = ImageFont.load_default()

    for i in range(n):
        t = dur * (i + 0.5) / n
        tmp = os.path.join(os.environ.get("TEMP", "."), f"rv-{i}.png")
        grab(path, t, tmp)
        if not os.path.exists(tmp):
            continue
        im = Image.open(tmp).convert("RGB").resize((tw, th), Image.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(im, (x, y))
        label = f"{t:5.1f}s"
        d.rectangle([x, y + th - 26, x + 74, y + th], fill=(0, 0, 0))
        d.text((x + 6, y + th - 24), label, font=f, fill=(230, 240, 255))
        os.remove(tmp)

    out = args.out or os.path.join(os.path.dirname(path), "审片-" + os.path.splitext(os.path.basename(path))[0] + ".png")
    sheet.save(out)
    print("视频信息：")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("审片拼图：", out)


if __name__ == "__main__":
    main()
