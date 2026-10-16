"""
启动后自动预热：等上游就绪后先合成两句短的，把 CUDA/模型 kernel 预热掉。
这样用户第一次点「朗读」时不用干等 30 秒。
"""
import json
import time
import urllib.request

BRIDGE = "http://127.0.0.1:7880"
LOG = r"C:\yachiyo-tts\bridge\warmup.log"


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg) + "\n"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def ready(deadline):
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BRIDGE + "/health", timeout=5) as r:
                d = json.load(r)
            if d.get("model_loaded"):
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def synth(text):
    body = json.dumps({"text": text, "prompt_audio": "x"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BRIDGE + "/api/v1/tts/tasks", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return len(r.read())


def main():
    if not ready(time.time() + 900):
        log("预热放弃：上游 15 分钟没就绪")
        return
    for i, text in enumerate(("预热一。", "预热二。"), 1):
        t0 = time.time()
        try:
            size = synth(text)
            log("预热第 %d 句完成：%.1fs，%dKB" % (i, time.time() - t0, size // 1024))
        except Exception as e:
            log("预热第 %d 句失败：%s" % (i, e))


if __name__ == "__main__":
    main()
