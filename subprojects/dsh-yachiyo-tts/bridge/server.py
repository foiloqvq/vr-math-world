"""
月读八千代 TTS · DSH 桥接层 v2
-------------------------------
作用：对 DeepSeek Harness 的 dsh-plugin-tts 冒充「本地 Index-TTS2 服务」，
把插件要求的三个端点翻译成「月读八千代一键包」本机 API（127.0.0.1:9880）。

v2 针对实际使用暴露的三个问题做了加固：
  1) 长文朗读偶尔失败 / 断断续续
     -> 上游同一时刻只允许一路合成（单飞锁），并发请求会被 429 拒绝。
        改为「排队 + 重试」：桥接内部串行发请求，429/5xx/连接错误按退避重试。
  2) 声音太小 -> 固定增益 + 压缩 + 限幅（逐块一致，不会忽大忽小）
  3) 不够清脆 -> 高通去闷 + 3.2kHz 提清晰度 + 5.8kHz 加空气感

插件侧契约（来自 dsh-plugin-tts/lib/index.mjs）：
  GET  /health -> JSON（插件读 model_loaded）；GET /api/v1/voices -> {"voices":[...]}
  POST /api/v1/tts/tasks -> 原样返回 wav 字节
上游（一键包 app/service.py）：POST /tts?oneclick_token=<TOKEN> {"text","text_lang"} -> wav
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)

UPSTREAM = str(CFG.get("upstream", "http://127.0.0.1:9880")).rstrip("/")
TOKEN = str(CFG.get("token", ""))
PORT = int(CFG.get("port", 7880))
# 安全限额（2026-10-17 自查后加）：请求体最大 64 KB，单次合成文本最多 2000 字。
# 目的不是防御攻击者（本机服务），而是防止"网页误触发/自己写错循环"把机器拖死。
MAX_BODY_BYTES = int(CFG.get("maxBodyBytes", 64 * 1024))
MAX_TEXT_CHARS = int(CFG.get("maxTextChars", 2000))
VOICE_NAME = str(CFG.get("voiceName", "月见八千代（内置）"))
TEXT_LANG = str(CFG.get("textLang", "zh"))
UPSTREAM_LIMIT = int(CFG.get("upstreamTextLimit", 3000))
CHUNK_LIMIT = max(200, UPSTREAM_LIMIT - 300)
RETRY_SECONDS = int(CFG.get("retry429Seconds", 600))
# 默认合成参数（来自 config.json 的 synthOptions）：不切分 + 极小片段间隔 + 语速
SYNTH_OPTS = dict(CFG.get("synthOptions") or {})
LONG_SPLIT = str(SYNTH_OPTS.pop("fallbackTextSplitMethod", "cut1"))
SYNTH_OPTS = {k: v for k, v in SYNTH_OPTS.items() if k != "fallbackTextSplitMethod"}

PP = CFG.get("postProcess") or {}
PP_ENABLED = bool(PP.get("enabled", False))
FFMPEG = str(PP.get("ffmpeg", r"C:\yachiyo-tts\engine\ffmpeg.exe"))
PP_FILTER = str(PP.get("filter", (
    "highpass=f=70,"
    "equalizer=f=3200:width_type=o:width=2:g=2,"
    "equalizer=f=5800:width_type=o:width=2:g=3.5,"
    "acompressor=threshold=-20dB:ratio=3:attack=4:release=150:makeup=2,"
    "volume=3dB,alimiter=limit=0.94"
)))

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_UPSTREAM_LOCK = threading.Lock()   # 上游是单飞锁：这里串行化，避免自家人打自家人


def _log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg) + "\n"
    try:
        with open(os.path.join(HERE, "bridge.log"), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    try:
        sys.stdout.write(line)
        sys.stdout.flush()
    except Exception:
        pass


def upstream_health(timeout=6):
    try:
        with _OPENER.open(UPSTREAM + "/health", timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return False, str(e)


def split_text(text):
    text = (text or "").strip()
    if len(text) <= CHUNK_LIMIT:
        return [text] if text else []
    parts, cur = [], ""
    for piece in re.split(r"(?<=[。！？!?；;\n])", text):
        if not piece:
            continue
        if len(cur) + len(piece) <= CHUNK_LIMIT:
            cur += piece
        else:
            if cur:
                parts.append(cur)
            while len(piece) > CHUNK_LIMIT:
                parts.append(piece[:CHUNK_LIMIT])
                piece = piece[CHUNK_LIMIT:]
            cur = piece
    if cur:
        parts.append(cur)
    return [p for p in parts if p.strip()]


def _post_process(wav_bytes):
    """ffmpeg 处理响度与音色；任何失败都原样返回，绝不因为美化而丢音频。"""
    if not PP_ENABLED or not os.path.exists(FFMPEG):
        return wav_bytes
    src = dst = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            src = f.name
        dst = src.replace(".wav", ".pp.wav")
        p = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                            "-i", src, "-af", PP_FILTER, "-ar", "32000", "-ac", "1", dst],
                           capture_output=True, timeout=120)
        if p.returncode != 0 or not os.path.exists(dst):
            _log("后处理失败(rc=%s)，返回原始音频：%s" % (p.returncode, p.stderr.decode("utf-8", "replace")[:200]))
            return wav_bytes
        with open(dst, "rb") as f:
            out = f.read()
        return out if len(out) > 1000 else wav_bytes
    except Exception as e:
        _log("后处理异常，返回原始音频：%s" % e)
        return wav_bytes
    finally:
        for p_ in (src, dst):
            try:
                if p_ and os.path.exists(p_):
                    os.remove(p_)
            except Exception:
                pass


def synth_once(text):
    opts = dict(SYNTH_OPTS)
    if len(text) > 120 and opts.get("text_split_method") == "cut0":
        opts["text_split_method"] = LONG_SPLIT
    body = {"text": text, "text_lang": TEXT_LANG}
    body.update(opts)
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    url = UPSTREAM + "/tts?oneclick_token=" + urllib.parse.quote(TOKEN)
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    deadline = time.time() + RETRY_SECONDS
    attempt = 0
    while True:
        attempt += 1
        try:
            with _OPENER.open(req, timeout=900) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if e.code in (429, 500, 502, 503, 504) and time.time() < deadline:
                time.sleep(min(1.0 + attempt * 0.5, 5.0))
                continue
            raise RuntimeError("上游 HTTP %s：%s" % (e.code, detail or e.reason))
        except Exception as e:
            if time.time() < deadline:
                time.sleep(min(1.0 + attempt * 0.5, 5.0))
                continue
            raise RuntimeError("连不上上游 %s：%s" % (UPSTREAM, e))


def concat_wav(chunks):
    if len(chunks) == 1:
        return chunks[0]
    out = io.BytesIO()
    writer = None
    for raw in chunks:
        with wave.open(io.BytesIO(raw), "rb") as w:
            if writer is None:
                writer = wave.open(out, "wb")
                writer.setnchannels(w.getnchannels())
                writer.setsampwidth(w.getsampwidth())
                writer.setframerate(w.getframerate())
            writer.writeframes(w.readframes(w.getnframes()))
    if writer is not None:
        writer.close()
    return out.getvalue()


def synthesize(text):
    parts = split_text(text)
    if not parts:
        raise RuntimeError("文本为空")
    chunks = []
    for p in parts:
        with _UPSTREAM_LOCK:
            chunks.append(synth_once(p))
    for c in chunks:
        if len(c) < 1000:
            raise RuntimeError("上游返回的音频过小（可能合成失败）")
    return _post_process(concat_wav(chunks))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "yachiyo-bridge/2.0"

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/status"):
            alive, detail = upstream_health()
            return self._json({
                "bridge": "yachiyo-bridge/2.0", "port": PORT, "upstream": UPSTREAM,
                "upstreamAlive": alive, "voice": VOICE_NAME, "textLang": TEXT_LANG,
                "postProcess": PP_ENABLED, "synthOptions": SYNTH_OPTS, "upstreamDetail": detail if not alive else "ok",
            })
        if path == "/health":
            alive, _ = upstream_health(timeout=5)
            return self._json({
                "ok": True, "model_loaded": alive, "engine": "gpt-sovits-v2ProPlus-yachiyo",
                "voice": VOICE_NAME, "upstream": UPSTREAM, "postProcess": PP_ENABLED,
            })
        if path == "/api/v1/voices":
            return self._json({"voices": [VOICE_NAME]})
        self._json({"detail": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/v1/tts/tasks":
            return self._json({"detail": "not found"}, 404)

        # ---- 本机服务的最小防护（2026-10-17 安全自查后加）----
        # 背景：这个桥接只监听 127.0.0.1，但**你浏览器里打开的任意网页**都能用
        # 「简单请求」(text/plain + no-cors) 打到 localhost —— 不需要 CORS 预检。
        # 也就是说：恶意网页可以不问你就让这个服务合成语音（占 CPU、出声、刷上游额度）。
        # 三道闸：只认本机 Host、拒绝带外部 Origin 的请求、限制请求体与文本长度。
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        if host not in ("127.0.0.1", "localhost", "[::1]", "::1"):
            return self._json({"detail": "forbidden host"}, 403)
        origin = (self.headers.get("Origin") or "").strip()
        if origin and not origin.lower().startswith(("http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost")):
            return self._json({"detail": "forbidden origin"}, 403)
        site = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if site in ("cross-site", "same-site"):
            return self._json({"detail": "forbidden site"}, 403)

        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n > MAX_BODY_BYTES:                      # 防止超大 body 占内存
            return self._json({"detail": "body too large"}, 413)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            params = json.loads(raw or b"{}")
        except Exception:
            return self._json({"detail": "invalid json"}, 400)
        text = str(params.get("text") or "").strip()
        if not text:
            return self._json({"detail": "empty text"}, 400)
        if len(text) > MAX_TEXT_CHARS:              # 防止一次塞几十万字
            return self._json({"detail": "text too long (max %d)" % MAX_TEXT_CHARS}, 413)
        t0 = time.time()
        try:
            wav = synthesize(text)
        except Exception as e:
            _log("合成失败 len=%d: %s" % (len(text), e))
            return self._json({"detail": str(e)}, 502)
        _log("合成成功 len=%d 用时=%.1fs 大小=%dKB" % (len(text), time.time() - t0, len(wav) // 1024))
        self._send(200, wav, "audio/wav")


def main():
    alive, detail = upstream_health()
    _log("桥接 v2 启动 port=%d upstream=%s 上游=%s 后处理=%s"
         % (PORT, UPSTREAM, "在线" if alive else detail, PP_ENABLED))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
