#!/usr/bin/env python3
"""从 Go 编译的 CLI 二进制里挖接口契约（拿不到源码时的逆向方法）。

原理: Go 把字符串常量连续存放在二进制里。按 token 定位后取周围可打印字符，
往往能直接读到字段名、枚举值和**校验错误原文**，从而反推出正确请求结构。

用法:
  python probe_cli_contract.py --exe eigenflux.exe --token surface --window 160
  python probe_cli_contract.py --exe x.exe --tags              # 一次性扫常见关键词
"""
import argparse, re

TAGS = ["json:\"", "must be one of", "is required", "not allowed", "unknown field",
        "invalid ", "schema_version", "idempotency_key", "category", "surface",
        "appearance", "flag", "client_item_id"]


def load(path):
    with open(path, "rb") as f:
        return f.read().decode("latin-1")


def near(text, token, window):
    out = []
    for m in list(re.finditer(re.escape(token), text))[:8]:
        i = m.start()
        seg = text[max(0, i - window): i + window]
        seg = "".join(c if 32 <= ord(c) < 127 else "." for c in seg)
        out.append(seg.replace("\n", " "))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--token")
    ap.add_argument("--window", type=int, default=140)
    ap.add_argument("--tags", action="store_true")
    a = ap.parse_args()
    text = load(a.exe)
    print("二进制 %.1f MB" % (len(text) / 1024 / 1024))
    tokens = TAGS if a.tags else [a.token]
    for t in tokens:
        if not t:
            continue
        hits = near(text, t, a.window)
        if not hits:
            continue
        print("\n########## %s（%d 处） ##########" % (t, len(hits)))
        for h in hits:
            print("  ..." + h + "...")


if __name__ == "__main__":
    main()