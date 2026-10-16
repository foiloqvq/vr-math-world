# 协议对接与逆向方法

## 1. 插件侧契约（它以为对面是什么）

来自 `dsh-plugin-tts/lib/index.mjs` 的 provider 定义（`index-tts2`）：

```
默认 baseUrl : http://127.0.0.1:7880
POST {baseUrl}/api/v1/tts/tasks
  {
    "text": "...",
    "prompt_audio": "<参考音色，字符串>",
    "clean_text": true,
    "emo_control_method": 0, "emo_ref_path": null, "emo_weight": 0.65,
    "emo_text": null, "emo_random": false,
    "max_text_tokens_per_segment": 120,
    "do_sample": true, "top_p": 0.8, "top_k": 30, "temperature": 0.8,
    "length_penalty": 0.0, "num_beams": 3,
    "repetition_penalty": 10.0, "max_mel_tokens": 1500
  }
  → 期待「裸 wav 字节」（不是 JSON、不是 URL）
GET {baseUrl}/api/v1/voices → {"voices": ["字符串", ...]}
GET {baseUrl}/health        → JSON，插件会读 model_loaded 判断"模型未加载"
```

**要点**：`prompt_audio` 只是字符串。上游是固定音色，所以桥接可以忽略它（或用来选参考）。

## 2. 上游契约（一键包）

```
POST /tts?oneclick_token=<token>
  body: {"text": "...", "text_lang": "auto|zh|ja|en"}
约束：
  - text 长度 1~3000
  - Host 必须是 localhost / 127.0.0.1
  - 带 Origin 时必须在白名单（官方站点域名）内；普通 HTTP 客户端不带 Origin 即可
  - 同一时刻只允许一路合成（threading.Lock，忙时返回 429 + {"detail":"正在合成语音，请稍后重试"}）
```

## 3. 我是怎么知道这些字段的

**方法一：直接读代码（最可靠）。**
`lib/index.mjs` 里有 `synthesizeIndexTts2()` 与 `indexTts2Config()`，请求字段一目了然；
`app/service.py` 里有 `data.update(...)`，能看到它**强制覆盖**了哪些字段、把哪些留成默认。

**方法二：从二进制里挖契约（拿不到源码时）。**
CLI 是 Go 编译的，字符串常量都在二进制里。用 `tools/probe_cli_contract.py` 的思路：
按 token 定位、取周围可打印字符，就能拿到字段名与**校验错误原文**。实战收获：

- `idempotency_key` / `client_item_id`：「必须是 8~128 位 ASCII 字母数字下划线连字符」
- `surface must be participation or focus`（枚举值）
- `category %q is not valid for surface %q`（类别随 surface 变化）
- `appearance must be primary or secondary`
- 解码器是**严格模式**：未知字段直接报 `unknown field`
- 甚至能读到官方文档没写的错误文案，从而**反推出正确的请求结构**

**方法三：从错误信息迭代。** 校验器报什么就补什么（例如先报缺 `schema_version`，再报 `kind must be preset or custom`，
再报 `preset flag "" is not valid for surface "focus"`——三轮回合就把结构拼对了）。

## 4. 一个容易踩的坑：PowerShell 传 JSON 参数

`--draft-json '{"a":1}'` 这类参数，PowerShell 5.1 不会正确转义内层双引号，
传给子进程的 JSON 会被破坏。**两个可靠做法**：

1. 用 Python/Node 以**精确 argv 数组**调用（`subprocess.run([exe, "--json", json_text])`）
2. 用 CLI 提供的 **stdin 入口**（`--stdin` / `--draft-file -`）

本工程所有 CLU 调用都用第 1 种。