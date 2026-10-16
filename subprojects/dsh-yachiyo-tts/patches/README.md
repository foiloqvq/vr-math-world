# 第三方补丁说明

> 本仓库**不收录**第三方源代码，只提供最小改动补丁（.diff）。
> 补丁会被上游更新覆盖——升级后需重新应用。

## 1. `service.py.patch` — 一键包服务脚本

`app/service.py` 原本把**除 text/text_lang 之外的所有参数都写死**（参考音频、提示文本、切分方式、批量等），
导致无法从外部调语速/音质。补丁做的是"**白名单式放开**"：

- 允许从请求里读：`speed_factor`、`temperature`、`sample_steps`、`super_sampling`、`seed`、
  `text_split_method`（正则校验 `^(auto_)?cut[0-5]$`）、`fragment_interval`
- 允许 `ref_audio_path` 但**限定文件名白名单**（只允许包内 `reference/` 下的特定文件），防止路径穿越
- `prompt_text` / `prompt_lang`（限 `ja|zh|en|auto`）
- 所有数值都做了**区间夹紧**（如 speed 0.5~2.0、temperature 0.1~1.5）

风险：位置参数被夹紧后不会抛错；若上游大改 `data.update(...)` 结构，补丁会失效（用 `git apply` 时会明确报冲突）。

## 2. `dsh-plugin-tts.host.patch` — 插件宿主端分块策略

`lib/index.mjs` 的 `chunkCal()` 对 `index-tts2` 写死了 `{chunkSec: 15, prewarm: 2}`，
意味着**返回前先把 2 块都合成完**（首声等待长），而且块越小接缝越多、音高台阶越明显。
补丁改成 `{chunkSec: 16, prewarm: 1}`：接缝 6 个 → 1 个，音高跨度 1.77 → 0.35 半音。

注意：宿主端代码在**宿主启动时加载**，改完必须**重启宿主**才生效。

## 3. `dsh-plugin-tts.client.patch` — 插件客户端默认 provider

`lib/client.js` 的 `loadSettings()` 在从 localStorage 读设置时，把 `provider === "rvc"` 映射为
`"index-tts2"`（原意：接入本工程后默认走本地八千代，而不是旧的本地方案）。
客户端代码同样在页面加载时读取，改完需**刷新页面**。

> 这三处补丁都属于"必要但不想常驻"的改动：**能用桥接层绕开的一律不补丁**。