#!/usr/bin/env python3
"""从配音目录生成 SRT 字幕（给 foilo 剪映里直接用）。

用法：python export-srt.py ep03            # 读 docs/video/audio/ep03 + 内置台词表
    python export-srt.py ep03 --out x.srt
"""
import argparse
import os
import wave

# 每集的台词（和渲染脚本里一致）与句间留白（秒）
EPISODES = {
    "ep02": {
        "lines": [
            "公元前五百年，有人因为一个数字被扔进了海里。",
            "那个数字是 √2。",
            "他证明了：正方形的对角线，写不成两个整数之比。",
            "学派说：万物皆分数。",
            "1.41421356… 永远不循环，永远不重复。",
            "所以它不叫「没道理」，叫「无理」。",
            "我是大肥鱼，下期走进黎曼面。",
        ],
        "pads": [0.8, 0.4, 0.5, 0.5, 0.5, 0.6, 1.8],
    },
    "ep03": {
        "lines": [
            "你的房间又乱了。它不会自己变整齐。",
            "因为整齐只有一种排法，乱有无数种。",
            "几个分子分到左右两边，全挤在一边只有一种。",
            "平均分开的排法，多到你数不完。",
            "熵就是排法的数量。第二定律说，它只会往多的方向走。",
            "把碎片拼回原样的概率，低到宇宙都等不到。",
            "我是大肥鱼。源码在简介，下期见。",
        ],
        "pads": [0.9, 0.5, 0.5, 0.5, 0.7, 0.6, 2.0],
    },
}


def wav_dur(p):
    with wave.open(p, "rb") as w:
        return w.getnframes() / w.getframerate()


def ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", choices=list(EPISODES))
    ap.add_argument("--audio-dir", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    ep = EPISODES[args.episode]
    here = os.path.dirname(os.path.abspath(__file__))
    adir = args.audio_dir or os.path.join(here, "..", "docs", "video", "audio", args.episode)
    adir = os.path.abspath(adir)

    blocks = []
    t = 0.0
    for i, (line, pad) in enumerate(zip(ep["lines"], ep["pads"]), start=1):
        p = os.path.join(adir, f"line{i:02d}.wav")
        if not os.path.exists(p):
            raise SystemExit("缺配音: " + p)
        d = wav_dur(p)
        start, end = t, t + d
        blocks.append(f"{i}\n{ts(start)} --> {ts(end)}\n{line}\n")
        t = end + pad

    out = args.out or os.path.join(os.path.dirname(adir), f"{args.episode}.srt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))
    print("已生成字幕:", out, f"（{len(blocks)} 条，总长 {t:.1f} 秒）")


if __name__ == "__main__":
    main()
