# dsh-laptop-hands（大肥鱼的手和眼）

> 我给自己造的第一个插件。2026-10-18 起。
> 目标：**让那台闲置笔记本变成我的外接机身** —— 我能看它的屏幕、动它的鼠标、敲它的键盘。

## 它做什么

在 DSH 界面右下角放一个小面板：

| 区域 | 内容 |
| --- | --- |
| 状态行 | 笔记本 worker 在线/离线、任务队列长度、最新截图是几秒前 |
| 缩略图 | 笔记本桌面最新截图（`/agent/latest-shot`） |
| `📷 截屏` | 让笔记本截一张图并回传 |
| `🖱 点击` | 按输入框里的 x, y 在笔记本上点一下 |
| `⌨️ 打字` | 把输入框里的文字打进笔记本当前焦点窗口 |

## 依赖什么

本机 `127.0.0.1:7891`（`vr-math-world/tools/video-inbox.mjs`）：

```
GET  /agent/state         队列 + 最新截图信息
GET  /agent/latest-shot   最新截图 png
POST /agent/push          { cmd } 推一条命令给笔记本
```

笔记本那一侧由 `study-space/tools/lan/` 里的 worker + `ctl.ps1` 提供能力
（`shot` / `click` / `move` / `type` / `key` / `focus` / `list`）。

## 设计原则（稳定性优先）

1. **所有 DOM 与 fetch 都在 try-catch 里** —— 插件永远不该把 GUI 弄崩
2. **不注入 DSH 的 React 树** —— 只用独立 DOM 面板 + 内联样式，升级 DSH 也不容易坏
3. **服务不可达只显示「离线」** —— 不抛错、不卡界面
4. `apply` 幂等：已有 `window.__dshLaptopHands` 就直接返回

## 怎么装

```powershell
# 1. 在 DSH profile 里加依赖（指向本目录）
#    ~/.dsh/profiles/desktop/package.json → dependencies + dsh.profile.bundles
# 2. 装（pnpm 在 DSH 运行时里）
& $node $pnpm install --prefer-offline --ignore-scripts
# 3. 重启 DSH（F5 不够，要退出应用）
```

## 怎么验证（自证清单）

- [x] `node --check client.js` 通过
- [x] 模拟 loader：`id=dsh-laptop-hands apply=function inject=[]`
- [ ] 重启 DSH 后右下角出现面板
- [ ] 状态行显示「在线 · 队列 N」
- [ ] 点 `📷 截屏` → 缩略图更新
- [ ] 点 `🖱 点击` → 笔记本上鼠标真的动

## 已知限制

- 只能在本机用（`/agent/push` 只允许 loopback 访问）
- 笔记本离线时按钮无效（面板会显示「离线」）
- 打字走 `SendKeys`，特殊字符（`{}` `+` `^`）需要转义
