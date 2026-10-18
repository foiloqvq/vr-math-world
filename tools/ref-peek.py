#!/usr/bin/env python3
"""抓参考视频的片头 18 秒，抽 6 帧拼成连环画 —— 大肥鱼用来"看内容"。

用 B 站匿名 playurl（qn=16，360p），无需登录。
用法：python ref-peek.py BV1rC4y1P7Lt [BV...]
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FFMPEG = r"C:\yachiyo-tts\engine\ffmpeg.exe"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = os.path.join(os.environ.get("TEMP", "."), "refpeek")


def curl(url, referer="https://www.bilibili.com/"):
    r = subprocess.run(["curl.exe", "-sS", "--max-time", "25", "-A", UA, "-e", referer, url],
                       capture_output=True, text=True)
    return r.stdout


def peek(bv, seconds=18, shots=6):
    os.makedirs(OUT, exist_ok=True)
    view = json.loads(curl("https://api.bilibili.com/x/web-interface/view?bvid=" + bv))
    if view.get("code") != 0:
        print(f"{bv}: view code {view.get('code')}")
        return None
    d = view["data"]
    cid = d["pages"][0]["cid"]
    title = d["title"]
    play = json.loads(curl(
        f"https://api.bilibili.com/x/player/playurl?avid={d['aid']}&cid={cid}&qn=16&fnval=1&fourk=0",
        referer=f"https://www.bilibili.com/video/{bv}/"))
    if play.get("code") != 0:
        print(f"{bv}: playurl code {play.get('code')}")
        return None
    url = play["data"]["durl"][0]["url"]
    clip = os.path.join(OUT, bv + ".mp4")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-headers", f"Referer: https://www.bilibili.com/video/{bv}/\r\nUser-Agent: {UA}\r\n",
                    "-ss", "2", "-t", str(seconds), "-i", url, "-c", "copy", clip],
                   capture_output=True)

    frames = []
    for i in range(shots):
        t = seconds * (i + 0.5) / shots
        f = os.path.join(OUT, f"{bv}-{i}.png")
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}",
                        "-i", clip, "-frames:v", "1", f], capture_output=True)
        if os.path.exists(f):
            frames.append((t, f))

    if not frames:
        print(f"{bv}: 抽帧失败")
        return None

    tw, th = 560, 315
    cols = 3
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th + 40), (10, 14, 24))
    dr = ImageDraw.Draw(sheet)
    try:
        fnt = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
    except Exception:
        fnt = ImageFont.load_default()
    dr.text((12, 8), f"{title}  [{bv}]  片头 {seconds}s", font=fnt, fill=(230, 240, 255))
    for i, (t, f) in enumerate(frames):
        im = Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS)
        x, y = (i % cols) * tw, 40 + (i // cols) * th
        sheet.paste(im, (x, y))
        dr.rectangle([x, y + th - 24, x + 60, y + th], fill=(0, 0, 0))
        dr.text((x + 5, y + th - 23), f"{t:.1f}s", font=fnt, fill=(255, 255, 255))
    out = os.path.join(OUT, bv + "-sheet.png")
    sheet.save(out)
    return out, title


if __name__ == "__main__":
    for bv in sys.argv[1:]:
        r = peek(bv)
        if r:
            print("拼图:", r[0], "|", r[1])
