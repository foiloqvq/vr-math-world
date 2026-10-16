# 月读八千代 TTS · DSH 接入工程

把「月读八千代 TTS 一键包」（GPT-SoVITS v2ProPlus 微调模型）接进 **DeepSeek Harness（DSH）** 的朗读插件，
让 DSH 的朗读功能使用本地八千代音色——**不联网、不花钱、不占别人服务器**。

## 归因

| 角色 | 谁 |
| --- | --- |
| **主工程（架构、桥接层、协议对接、调参与诊断工具）** | **大肥鱼**（DeepSeek Harness 上的本地智能体） |
| 素材搜集、真机试听与验收 | foilo qvq（[@foiloqvq](https://github.com/foiloqvq)） |

第三方依赖（本仓库**不收录**其代码与模型，仅以补丁形式说明改动）：

- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)（RVC-Boss，MIT）
- 「月读八千代 TTS 一键包 1.0.1」（发布者分发的整合包；模型与参考音频版权归其发布者/权利方）
- [dsh-plugin-tts](https://www.npmjs.com/package/@memef1f1y/dsh-plugin-tts)（@memef1f1y，DSH 朗读插件）

## 链路

```
DSH 朗读插件 (host, 19387)
      │  POST /api/v1/tts/tasks {text, ...}   ← 它以为对面是「本地 Index-TTS2 服务」
      ▼
桥接层 bridge/server.py (127.0.0.1:7880)      ← 本工程的核心
      │  POST /tts?oneclick_token=... {text, text_lang, +调参}
      ▼
月读八千代一键包 app/service.py (127.0.0.1:9880)
      │  GPT-SoVITS v2ProPlus：参考音频 + 微调模型
      ▼
wav → 桥接做后处理（响度/限幅）→ 插件按块播放
```

**桥接层解决的问题**

1. **协议不兼容**：插件只会说「Index-TTS2 三端点」，一键包只会说自己的 `/tts`。桥接做端点与字段翻译。
2. **上游是单飞锁**：并发请求会被 429。桥接内部排队 + 429/5xx/连接错误退避重试，长文朗读不再掉句。
3. **音色与语速**：把上游**锁死的参数**（切分方式、片段间隔、语速、超采样）从配置层开放出来。
4. **响度**：模型输出偏小（平均 -22.5 dB）；桥接做固定增益 + 压缩前不染色 + 限幅，逐块一致。

## 目录

```
bridge/     桥接层代码（本工程主体）
patches/    对第三方文件的最小改动（.patch，含说明）
tools/      可复用的量化诊断工具（音高 / 毛刺 / 底噪 / A-B 生成）
docs/       架构、协议、调参日志、诊断方法论、运维
```

## 快速开始

见 [docs/05-operations.md](docs/05-operations.md)。核心三步：

1. 部署一键包，用 `bridge/start-tts.bat` 起上游（9880）+ 桥接（7880）+ 预热
2. `bridge/config.example.json` 复制为 `bridge/config.json`，填好本地 token
3. 把朗读插件的服务地址指向 `http://127.0.0.1:7880`

## 阅读顺序建议

1. [docs/01-architecture.md](docs/01-architecture.md) —— 整体设计与职责边界
2. [docs/02-protocol.md](docs/02-protocol.md) —— 两套协议 + 我是怎么逆向出字段的
3. [docs/03-tuning-log.md](docs/03-tuning-log.md) —— 每个参数改动**都带实测数字**
4. [docs/04-diagnostics.md](docs/04-diagnostics.md) —— 量化诊断方法，以及**我的指标骗过我两次**的教训
5. [docs/05-operations.md](docs/05-operations.md) —— 常驻、自启、脱离宿主进程树