#!/usr/bin/env python3
"""用 ffmpeg 批量生成 A/B 变体，供真机试听对比。

用法: python build_ab.py --src raw.wav --outdir ./ab --preset loudness denoise bright
预设:
  loudness  只提响度不染色（最终采用的方案）
  bright    加存在感 EQ（注意：抬高频会同时抬声码器伪影）
  denoise   轻度降噪 + 柔化高频
  frontdesk 明亮+靠前+略快（"前台感"）
  pitchup   音高 +1.5%（asetrate+atempo，时长不变）
"""
import argparse, os, subprocess

FF = os.environ.get("FFMPEG", "ffmpeg")
TAIL = "volume=5dB,alimiter=limit=0.85:level=disabled"   # 注意 level=disabled，否则会被归一化回 0dB
PRESETS = {
    "loudness": "highpass=f=70," + TAIL,
    "bright": "highpass=f=70,equalizer=f=350:width_type=o:width=1.5:g=-1.5,"
              "equalizer=f=1200:width_type=o:width=2:g=1,equalizer=f=2800:width_type=o:width=2:g=2.5," + TAIL,
    "denoise": "highpass=f=70,afftdn=nr=10:nf=-45,lowpass=f=11000," + TAIL,
    "frontdesk": "highpass=f=70,equalizer=f=2800:width_type=o:width=2:g=2.5,atempo=1.04," + TAIL,
    "pitchup": "asetrate=32480,aresample=32000,atempo=0.98522," + TAIL,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--outdir", default="ab")
    ap.add_argument("--preset", nargs="+", default=list(PRESETS))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    for i, name in enumerate(a.preset, 1):
        if name not in PRESETS:
            print("未知预设:", name); continue
        out = os.path.join(a.outdir, "%d-%s.wav" % (i, name))
        cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", a.src,
               "-af", PRESETS[name], "-ar", "32000", "-ac", "1", out]
        subprocess.run(cmd, check=False)
        print("生成:", out)


if __name__ == "__main__":
    main()