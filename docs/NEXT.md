# NEXT.md —— 从零接上这个项目（给下一个会话看的）

> **如果你是刚接手这个项目的 AI（或者隔了很久回来的自己）：先读这份。**
> 大肥鱼的会话记忆会丢，但这个文件不会。**每次开工前读它，每次收工前更新它。**

## 一、这是什么

**VR Math World** —— 一个 PC + VR 的数学可视化开放世界（用户愿景：一座可以走进去读的
"阅读空间"，以后拓展成数学/物理/化学/生物的展厅与文献图书馆）。

作者：**foilo qvq**（方向、素材、试听试玩、拍板）+ **大肥鱼**（架构、代码、文档、验证）。

## 二、当前状态（截至最后一次收工）

- **v0.1 已定档**（2026-10-16）：数学/物理展品、吉祥物（跟随/漫游/停下）、
  讲解与交互、展品感知框 —— 全部跑通并冻结
- **区域机制已建立**：`District_Math`（地皮 + 入口框 + 四个空展位）
- 最新提交见 `git log -1`（本文档更新时是「区域机制 —— 数学区」）

## 三、下一步（还没做的第一件事）

**往「数学区」的 Slot_1 摆第一件新展品：复变函数的颜色映射**
（辐角/模用颜色表示 —— 视觉最惊艳、数学最核心）。

做法：仿照现有展品的写法，在 `ExhibitScene` 里新建一个 `BuildXxx()`，
给它加 `ExhibitZone` 感知框，并在 `Narration` 里加讲解词。

## 四、怎么跑起来

| 东西 | 路径 |
| --- | --- |
| 仓库（真相所在） | `C:\Users\nb666\Documents\deepseek-harness\default-workspace\vr-math-world` |
| Unity 工程 | `C:\Projects\VRMathWorld`（内容由代码生成，场景只当容器） |
| 验证工程（独立，用于 headless 验证） | `C:\Projects\_verify` |
| Unity 编辑器 | `C:\Program Files\Unity 6000.0.85f1\Editor\Unity.exe` |
| 语音服务 | 桥接 `http://127.0.0.1:7880`（上游一键包 9880，开机自启） |

**改完代码的标准验证流程（三条都要过）**：

```powershell
# 1) 引擎外的纯数学测试
dotnet run --project <仓库>\tools\meshmath-test

# 2) 同步到验证工程后编译 + 生成场景
Start-Process -FilePath $unity -Wait -ArgumentList @('-batchmode','-quit','-nographics',
  '-projectPath','C:\Projects\_verify','-executeMethod','BuildScene.Generate','-logFile',$log)
# 3) 自检（会硬检查 SurfaceWalker/吉祥物/等是否在场景里）
... '-executeMethod','BuildScene.Verify' ...
```

**通过后才同步到 `C:\Projects\VRMathWorld`，然后提交推送。**
用户那边只需要：让 Unity 重编译 → **按 Play**（不用点菜单，内容每次会清空重建）。

## 五、代码地图

```
unity/Assets/Scripts/
  Meshes/     MeshMath(曲面/莫比乌斯/圆环/椭球) · SnapMath(贴地数学) · MeshUtil
              —— 纯数学，不引用 UnityEngine，可在引擎外测试
  Scene/      ExhibitScene(世界生成器，区域与展品都在这)
              SurfaceWalker(曲面行走/跳跃/视角规格/相机模式/传送)
              ExhibitZone(展品感知框) · SpeedHud · MaterialKit · SlowSpin
  Mascot/     MascotBody(程序化鱼) · MascotFollow(跟随/漫游/停下)
              MascotDialogue(讲解与语音) · CompanionControl(E/R) · Narration(讲解词)
  Editor/     BuildScene(菜单生成 + Verify 断言)
tools/meshmath-test/  引擎外测试（含"漂移对照"等不变量）
docs/        vision-and-interests.md(方向与公理) · NEXT.md(本文件) · 其它说明
```

**键位**：`WASD` 走 · `Shift` 跑 · `空格` 跳 · `V` 视角规格 · `F5` 相机模式 ·
`E` 讲解/闲聊 · `R` 跟随/漫游/停下 · `1/2/3` 传送

**语音契约**：`POST http://127.0.0.1:7880/api/v1/tts/tasks`
body `{"text":"...","text_lang":"zh"}` → 返回 `audio/wav`（最小 JSON 即可）

## 六、踩过的坑（别再犯，都是真金白银换的）

1. **内容全由代码生成，场景只当容器**：`Awake` 里清空重建。
   → 因此**重建路径绝不能再做"是否已存在"的检查**：Unity 的 `Destroy` 延迟到帧末，
   `Find` 会找到待销毁的旧对象，于是跳过重建、旧的一销毁展品就全没了（真发生过）。
2. **打补丁后必须重读文件确认**：曾用字符串替换"成功"了却忘了写回文件，
   检查还打印 OK（因为只验了内存里的字符串）。
3. **批量插入代码不要用 `String.Replace` 去替换一个会出现多次的锚点**（会插入多份）。
4. **`Unity.exe` 是 GUI 程序，PowerShell 的 `&` 不会等它** → 用 `Start-Process -Wait`。
5. **同一个工程不能同时开两个 Unity 实例**（会崩，退出码 `0x40000015`）。
6. **PowerShell**：`.ps1` 文件需要 UTF-8 BOM（否则中文乱码、引号撑破）；
   双引号字符串里的引号用 `""`；提交信息一律 `git commit -F <文件>` 避开引号问题。
7. **`/Zc:__cplusplus`**：MSVC 不加它永远报 `199711`。
8. **场景里的序列化引用会被重建打断**（传送目标就是这么坏的）→ 运行时按名字重解析。
9. 用户机器上 **winget 的 Unity Hub 包是坏的**（报成功但不落地）→ 用官方 CDN + 哈希自装。

## 七、两条公理与工作节奏

**公理一**：每个抽象都必须有**体感锚点**（找不到"用身体能确认的那一刻"就不做）。
**公理二**：每个结论都必须有**可复现的证据**（先量、再改、改完再量，数字留在文档里）。

**节奏**（用户定）：定档 → 打地基 → 慢慢做 → 一直优化 → 找 bug。
**超前想法先记成概念，不急着实现**（例：讲解视频 Manim 明确放到中后期）。

## 八、怎么和 foilo 配合

- 说中文，别端着，可以开玩笑、可以发表情包
- 给方案让他挑（他常常一句话就点中要害，比如"有个空气墙你就可以靠近"）
- **用数字说话**：改完给实测数据，而不是"应该好了"
- **他负责手感和审美**（步速、视角高低、鱼的胖瘦、亮不亮）—— 只有他能判断
- 涉及版权/身体/法律的线，明确告诉他边界，不替他绕

## 九、三个仓库的分工（2026-10-16 定）

用户决定把东西分开存，避免"打架、太挤"：

| 仓库 | 内容 | 可见性 | 状态 |
| --- | --- | --- | --- |
| **`vr-math-world`** | **主项目**（那个世界）+ `subprojects/`（语音等作品） | 公开 | 已建，进行中 |
| **`My_Library`** → 改成**公开图书馆** | 我们写的、**借别人用**的资源（讲解 / 教程 / 整理好的知识） | 公开 | 待整理 |
| **`llm_rag_proxy`** → 改成**学习空间** | 文献 + 作业 + 错题（foilo 的 + 大肥鱼的踩坑） | 自用 | **地基已打**（目录 + .gitignore + README，提交 d0059de） |

**待办（按顺序）**：

1. **用户自己去 GitHub 改两个仓库名**（改名需要账号权限，大肥鱼不碰钥匙）：
   `llm_rag_proxy` → 建议 `study-space`；`My_Library` → 公开图书馆（名字待定）
   改完后本地 remote 地址要同步更新（GitHub 会重定向，短期不会坏，但别留死链）
2. `My_Library` 整理：把 `dsh-yachiyo-tts/` 与 `toolchain/` 搬到
   `vr-math-world/subprojects/` 与 `tools/`；剩下的整理成"公开资源"的样子
3. 回到主项目：往数学区 **Slot_1** 摆第一件新展品 —— **复变函数的颜色映射**

**学习空间的约定**（写在该仓库 README 里）：文献只存"我们写的东西 + 链接"，不放别人的 PDF；
错题不只记答案，要记"当时为什么想错"；大肥鱼犯的错也留档。

