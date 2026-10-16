# 运维：常驻、自启、不打扰

## 两个进程

| 进程 | 端口 | 启动方式 |
| --- | --- | --- |
| 上游（一键包） | 9880 | `runtime\python\python.exe -I app\bootstrap.py nvidia serve 9880`，需环境变量 `TSUKUYOMI_TOKEN`（值从 `bridge/token.txt` 读） |
| 桥接层 | 7880 | `runtime\python\python.exe bridge\server.py` |

`bridge/start-tts.bat` 会：起上游 → 等 60 秒 → 起桥接 → 6 秒后跑 `warmup.py` 预热。
`bridge/stop-tts.bat` 关掉这两个端口上的进程。

## 关键设计：脱离宿主进程树

如果把服务当成宿主（DSH/Electron）的子进程启动，**宿主一重启服务就全没了**。
本工程用 WMI 创建进程（父进程是系统服务），宿主重启不会带走它们：

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = 'cmd /c start "yachiyo-upstream" /min "...\python.exe" -I "...\app\bootstrap.py" nvidia serve 9880'
}
```

开机自启用 **Startup 快捷方式**（登录时拉起 `start-tts.bat`）。
注意：`schtasks` / `Register-ScheduledTask` 在非管理员会话下会被**拒绝访问**，所以没有用计划任务。

## 常见故障

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 朗读报"连不上服务" | 桥接或上游没起 | 双击 `start-tts.bat`；看 7880/9880 是否在监听 |
| 某个词被跳过 | 上游 429 且重试超时 | 桥接已内置排队+重试；看 `bridge/bridge.log` |
| 第一次朗读要等 30 秒 | CUDA/模型冷启动 | `warmup.py` 会自动预热；手动跑一次亦可 |
| 改了 `bridge/config.json` 不生效 | 桥接只在启动时读配置 | 重启桥接进程（3 秒，不用重启宿主） |
| 音高忽高忽低 | 宿主分块太小，块间接缝多 | 把宿主分块调到 16 秒（见 `patches/`） |
| 打游戏时朗读变慢 | 语音服务与游戏抢同一张显卡 | 玩之前 `stop-tts.bat` 释放显存 |