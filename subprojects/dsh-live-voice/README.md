# dsh-live-voice —— 语音通话模式

把「点一下麦克风 → 说话 → 点停止 → 改文字 → 按发送」的语音输入，
变成**打电话**那种体感：一直听着、说完自动提交、回复读完继续听。

> 为大肥鱼 × foilo 定制。全部本地：识别用 DSH 自带的 SenseVoice，播报用本机八千代 TTS。

## 一条链

```
麦克风(echoCancellation) → AudioWorklet 16kHz → 16ms 块算 RMS
   → 自适应噪声门限 + 断句(静音 700ms 判一句)
   → WAV(16k mono) → base64
   → ctx.remote.speech.transcribe（本机 SenseVoice）→ 文本
   → 写进输入框并回车提交
   → 读到新回复 → 八千代 TTS 合成播放（播放期间闭麦）
   → 回到聆听
```

## 怎么用

1. 侧栏 → 插件 → 确认 **语音输入** 与 **dsh-live-voice** 都开着（后者装好后默认开）。
2. 刷新页面（客户端插件改动需要刷新；宿主侧改动需要重启 DSH）。
3. 输入框左边出现 **📞 通话** 按钮：点一下开始，`📞 听着…` 就是在等说话。
4. 正常说话，停 0.7 秒就自动发出去；大肥鱼开始回答时会**自动闭麦**，回答读完自动继续听。
5. 再点一次结束通话。

调试：浏览器控制台里 `window.__dshLiveVoice.state` / `.history` / `.start()` / `.stop()`。

## 设计取舍（为什么要这么写）

| 坑 | 处理 |
| --- | --- |
| **自听**：我说话时麦克风会听见自己 | 播放期间把「我正在干活」当背压直接丢语音（`setBlocked`），不识别自己的声音；同时要了 `echoCancellation` |
| **回声里的半句** | 播放一开始就丢掉正在进行的句子（断句器 blocked → drop） |
| **断句** | 自适应噪声本底（前 600ms 校准，之后缓慢跟随）+ 3 倍门限 + 绝对下限 0.006；静音 700ms 判一句，太短的咔哒声丢掉 |
| **超长句** | 单句 20s 强制切，和后端 `segmentSeconds`/上限对齐 |
| **提交** | 用 `conversation.input.left` 的 `InputActions`：`captureInsertion()` + `insertText()`，再补一个 Enter 事件触发发送 |
| **识别后端** | 走 `ctx.remote.speech.transcribe`（本机 SenseVoice，int8 模型实测加载 1236ms、4 秒音频识别 210ms） |
| **播报** | 本机八千代 TTS（`127.0.0.1:7880`），按序排队，不抢话 |

## 已知限制（诚实版）

- **热更新后界面偶尔会闪坏**（2026-10-17 用户反馈）：改完 `client.js` 刷新页面时，
  聊天区偶尔变成透明 / 消息浮在壁纸上 / 右侧多出一列编号小点。
  **重进或 F5 一次就好**，不是内容丢失。
  缓解：`apply` 会先清掉旧的 `style[data-dsh-live-voice]`，避免残留叠加。
  嫌碍事可在 profile 里停用 `dsh-live-voice`（插件保留，只是不渲染 UI）。
- **判停时间**：默认 1.5 秒没声音才算说完（`window.__dshLiveVoiceConfig = {silenceMs: 1000}` 可改）。
  这个值调小了会把"想一想"的停顿当成说完，句子被切半截 —— 这是 2026-10-17 实机踩过的。
- **打断**目前是「等它说完」：大肥鱼播报时麦克风是关的，所以你插话它听不到。
  想要真·同时说听（barge-in），需要把播放期间的麦克风改成「只听不识别 + 声学门限」，
  或者上云端全双工方案（见工作区日志）。
- **提交依赖输入框可写**：草稿里如果已经有你打的字，`insertText` 可能被拒（版本冲突），
  这时按钮旁会出 ⚠，把草稿清空再说话。
- **回车提交是合成事件**：如果宿主改了回车行为，可能不生效；日志里会记 `heard` 但没提交。
- **不写会话事件**：本插件不注册任何宿主事件类型，避免污染会话历史加载。

## 测试

```powershell
$n = "C:\Users\nb666\AppData\Local\Programs\DeepSeek Harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe"
cd vr-math-world\subprojects\dsh-live-voice
& $n --test test/client.test.mjs
```

12 项纯逻辑测试：RMS、噪声本底、断句（正常/太短/屏蔽/超长）、WAV 头、base64、
会话快照解析、TTS 合成请求。**这些不依赖浏览器**，所以改断句参数后先跑它们。

浏览器侧只能真机验：点按钮、说话、看输入框是否自动出现文字并发出。
