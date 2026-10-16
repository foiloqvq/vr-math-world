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
- **数学区开张（2026-10-17）**：`Slot_1` 摆上第一件新展品 —— **复变函数的颜色映射**：
  `f(z) = z²`；**色相 = 辐角、明暗 = |f(z)| 的模**，另外等模环（每 2 倍）与等辐角射线（每 15°）压暗；
  两块面共用**同一张贴图**（512²，取色 38 ms）：① Slot_1 台面上的竖直图版（+X 实部 / +Y 虚部，
  法线朝入口）② 数学区中间**可以走上去的彩色地砖**（体感锚点：从红线走到 i 线，颜色已转到对面）。
  走近发光、按 `E` 有 5 句讲解，`complexMapGlow` 是调"亮不亮"的旋钮。
  验证数字：引擎外 **33 条断言全过** · headless 生成 `exit 0`（objects=195 meshes=171）·
  `Verify OK`（图版 顶点 9409 / UV 9409 / 贴图 True；地砖 顶点 16641 / UV 16641 / 贴图 True）
- 最新提交见 `git log -1`

## 三、下一步（还没做的第一件事）

**让 Slot_1 的展品"能变"：按一个键换幂次**（n = 1 / 2 / 3 / 4）。

同一块图版、同一张地砖，`f(z) = zⁿ` 一换，颜色绕的圈数就跟着变 ——
n=1 绕一圈、n=2 绕两圈、n=3 绕三圈，肉眼直接数得出来。这是把"辐角翻倍"这件事
从"听讲解"变成"亲手按一下"的最短路径（贴图重算一次只要 ~40 ms，实时换没问题）。

要拍板的两件小事：
1. 键位：`1/2/3` 已被传送占用 —— 建议 `Q` 循环，或 `[` `]` 前后切；
2. n 只允许整数，还是放进 `n = 1/2`（平方根，会在负实轴上"撕开"一个分支切）——
   分支切是复变函数最漂亮的一课，但会让图版在一条射线上出现断层，得你看了才知道接不接受。

再往后（Slot_2 的候选）：**黎曼面的立体版**，把多值函数"摊开"成一圈层叠的曲面。

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
  Meshes/     MeshMath(曲面/莫比乌斯/圆环/椭球/PanelXY 竖直图版) · ComplexColor(复变函数→颜色)
              SnapMath(贴地数学) · MeshUtil(建网格 + 平面投影 UV)
              —— 纯数学，不引用 UnityEngine，可在引擎外测试
  Scene/      ExhibitScene(世界生成器，区域与展品都在这)
              SurfaceWalker(曲面行走/跳跃/视角规格/相机模式/传送)
              ExhibitZone(展品感知框) · SpeedHud · MaterialKit · SlowSpin
  Mascot/     MascotBody(程序化鱼) · MascotFollow(跟随/漫游/停下)
              MascotDialogue(讲解与语音) · CompanionControl(E/R) · Narration(讲解词)
  Editor/     BuildScene(菜单生成 + Verify 断言)
tools/meshmath-test/  引擎外测试（含"漂移对照"、复变函数取色与图版法线等不变量）
docs/        vision-and-interests.md(方向与公理) · NEXT.md(本文件) · 其它说明
```

**复变函数展品在这几处**：函数与参数在 `ExhibitScene` 顶部（`ComplexExhibitFn` / `ComplexMapSize` /
`ComplexMapPixels` / `complexMapGlow`）；颜色规则在 `Meshes/ComplexColor.cs`（**唯一真相**，
贴图与测试都从这里取色）；两处摆放（竖直图版 + 可走地砖）在 `ExhibitScene.BuildComplexColorMap()`。

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
10. **别用 `Math.Log2`**：Unity 的 .NET 配置（.NET Standard 2.1）里没有它，而引擎外的
    测试工程是 `net8.0`、**有**它 —— 于是"33 条断言全过、Unity 编译报 CS0117"，
    2026-10-17 真翻车一次（`ComplexColor.cs` 三处）。**教训：`dotnet` 编译通过 ≠ Unity 能编过**，
    新增纯数学文件后必须跑一次 headless 生成；用不到的 BCL 新 API 一律自己写（如 `Log2`）。
11. **`MeshUtil.MakeMesh` 不生成 UV** → 直接挂贴图的话所有顶点都取 (0,0)，整块面只显示
    一个像素的颜色（以前展品都是纯色材质，所以一直没暴露）。现在用 `MeshUtil.SetPlanarUVs`
    按平面投影铺 UV（竖直面 `(0,1)`、地面 `(0,2)`），并且 `Verify` 会把 UV 数硬检查一遍。
12. **纹理要 `wrapMode = Clamp`**：默认 Repeat 会让图版边缘的颜色从对面串回来，
    在色相绕圈的图上特别显眼（颜色看着"接错了"）。

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
| **`study-space`**（原 llm_rag_proxy，改名已完成） | 文献 + 作业 + 错题（foilo 的 + 大肥鱼的踩坑） | 自用 | **地基已打**（目录 + .gitignore + README，提交 d0059de） |

**待办（按顺序）**：

1. ~~改 study-space 名字~~ —— **已完成**：`llm_rag_proxy` 已改名为 `study-space`，
   本地 remote 已同步（2026-10-16）。**仅剩 `My_Library` 改名**（改成公开图书馆，名字待定）。
   注意：GitHub 对旧名会自动重定向，所以短期内老链接不会断。
2. `My_Library` 整理：~~把 `dsh-yachiyo-tts/` 与 `toolchain/` 搬到
   `vr-math-world/subprojects/` 与 `tools/`~~ —— **内容已于 `734b079` 搬完**
   （公开图书馆那边已只剩数学笔记与 Python 练习）；**剩改名 + 整理成"公开资源"的样子**。
3. ~~回到主项目：往数学区 **Slot_1** 摆第一件新展品 —— 复变函数的颜色映射~~
   —— **已完成（2026-10-17）**，下一步见第三节（换幂次 / Slot_2 摆黎曼面）。
4. **C/C++ 构建产物已出仓**（`74f3975`）：`.gitignore` 补了 C/C++ 一节；
   以后 `tools/toolchain/examples/` 下跑过 cmake 也不会再污染仓库。

**学习空间的约定**（写在该仓库 README 里）：文献只存"我们写的东西 + 链接"，不放别人的 PDF；
错题不只记答案，要记"当时为什么想错"；大肥鱼犯的错也留档。

