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
  **按 `4` 直接传送到数学区**（落在彩色地砖上、面朝图版）——
  传送点的朝向由 `Teleport_Math` 这个空物体自己决定（转过 180°）。
  验证数字：引擎外 **33 条断言全过** · headless 生成 `exit 0`（objects=195 meshes=171）·
  `Verify OK`（图版 顶点 9409 / UV 9409 / 贴图 True；地砖 顶点 16641 / UV 16641 / 贴图 True）
- 最新提交见 `git log -1`

## 三、下一步（还没做的第一件事）

**Slot_1 展品已经能变，而且是"分数幂"了（2026-10-17）**：
按 **`Q`** 在 **`z → √z → z² → z³ → z⁴ → z`** 之间循环（幂次表用分子/分母表示：1/1、1/2、2/1、3/1、4/1）。

- **整数幂**：绕原点走一圈，颜色绕 **n 圈**（n=1 一圈、2 两圈、3 三圈）——肉眼直接数。
- **√z（1/2）**：颜色只绕**半圈**，而且在**负实轴上撕开一道分支切** ——
  同一条轴的两侧颜色不同（arg 从 +π 跳到 -π，开方后是 +π/2 与 -π/2）。这就是"一道缝"。
- HUD 上那行小字会跟着变：当前 `f(z) = …`；√z 那一项额外提示"负实轴上有道缝"。
- 实现：幂次表的真身在 `ExhibitScene.ComplexPowNumerators / ComplexPowDenominators`
  （**唯一真相**；`ComplexPowerDefault = 2` 就是 √z）；幂函数本体在
  **`ComplexColor.PowFraction(z, num, den)`**（纯数学、引擎外可测；`den=1` 走循环乘、
  与以前逐位一致）；每个幂次的贴图**按需生成并缓存**；`SetComplexPower()` 一处同时换两张。
- 验证数字：引擎外断言全过（含 √z 的 4 条：`√z·√z = z`、负实轴两侧差 **2.000000i**、
  两侧分别是 ±i、辐角只转 **1.570796 rad**）· headless `Generate exit 0` · `Verify OK`
  （图版 9409 顶点 / UV 9409 / 贴图 True；地砖 16641 / 16641 / True；Teleport_Math 4 个目标）

### 掉进虚空：已修（2026-10-17，foilo 报的）

**症状**：踩到新展品（Slot_2/3/4）上面会掉下去。

**两个原因，都修了**：

1. **台子太小**：展位台面原来直径 2.2 m（半径 1.1），而展品有 2.1 m 宽、黎曼面带直径 3.2 m ——
   踩到悬空那半边必掉。→ 台子放大到 **直径 3.6 m**（半径 1.8，展位间距 7.5 m 不重叠）。
2. **圆柱原语的碰撞体是胶囊**，非均匀缩放（2.2, 0.25, 2.2）后顶面覆盖不全。
   → **换掉胶囊、改挂 `BoxCollider`**，顶面才是平的。

**另外加了"虚空安全网"**（`SurfaceWalker.voidRespawnY = -3`）：
掉到 y < -3 就送回**最后一次站稳的位置**（地面/台子上），速度清零。
以后再有什么缝，也不会无限下落只能重开。

**硬检查（防回归）**：`Verify` 现在逐个检查 Slot_1..4 —— 直径必须 ≥ 3.4 且必须是 `BoxCollider`，
否则 `FAILED`。当前输出：`Slot_1..4 直径=3.6 方块碰撞=True`。

### 一次事故，两个症状：FBX 轴转换（2026-10-17，foilo 复现后确认已修）

**现象**：① 展位圆盘"立起来"（像拱门）② 直着走会往右偏。

**根因只有一个**：美术资产接进来时，我在 `Instantiate` 之后写了
`slot.transform.localRotation = Quaternion.identity` —— 而 FBX 的 **Z-up → Y-up 转换
就存在那根根节点旋转里**，被我抹掉了。于是圆柱轴从 Y 变成 Z（症状①）；
踩在这种躺倒圆盘的**斜面**上，`SurfaceWalker` 会把 `up` 掰向斜面法线，
前方向投影到斜面上就变成弧线（症状②）。

**修法**：不再动那根旋转；碰撞体改挂 Renderer 那一层、用 `localBounds` 自动贴合。
批处理下另外主动打开 `ModelImporter.bakeAxisConversion`（`[InitializeOnLoad]` 的 delayCall
在 `-executeMethod` 里来不及跑，所以写进 `BuildScene.EnsureArtImportSettings()`）。

**防回归**：`Verify` 新增**高度断言** —— 台子高 > 1.2 m 就判定"躺倒"并 `FAILED`。
现在 `Slot_1..4 宽=3.58m 高=0.50m（模型）`。

**经验**：**一个 bug 修好可以带走两个症状**。当时差点去改移动代码（症状②），
幸好先让 HUD 打出「上向量/输入轴」才看清是斜面的锅。→ **先量，再改**（老规矩又赢一次）。


### Slot_3 / Slot_4 也摆上了（2026-10-17，A 方案「先试水」）

**Slot_3 · 分数地砖**（`Exhibit_Fractions`）：三行**一样长**的地砖，分别切成 **2 / 3 / 4 份**
（暖橙 / 青 / 紫），份与份之间压深缝。走一遍、数一数缝，就懂"分母越大，每份越小"。
可走（MeshCollider），走近按 E 有 5 句讲解。

**Slot_4 · 一次函数斜坡**（`Exhibit_Slopes`）：三条并排的可走斜坡，斜率 **k = 0.25 / 0.5 / 0.75**
（蓝 / 青 / 橙）。y = k·x 的 k 在这里就是"每往右 1 米升 k 米"——脚知道哪条费劲。
实现要点：`ParametricSurface((px,py) => k*(px+L/2))` 生成斜面，再**只压窄 Z 方向的 localScale**
（高度与 y 无关，所以缩放不会改变坡度）。

验证数字：`Verify OK` —— `Exhibit_Fractions 顶点=625 UV=625 贴图=True`、
`Exhibit_Slopes 斜坡=3 带碰撞=3`（新增一条硬检查：三条斜坡少一条或没碰撞就 FAILED）；
objects=230 meshes=200。

**下一件候选**：把「小学 → 初中 → 高中」做成一条**知识阶梯走廊**（新开 `District_Basics`），
现在四个 Slot 已经分别代表：复变图版(1) · 黎曼面(2) · 分数地砖(3) · 一次函数斜坡(4)。

**并行的另一条线：美术**（2026-10-17 立，见 [`art-plan.md`](art-plan.md)）
—— foilo 开始学 Blender，30~60 分钟/天，从道具开始；第 1 练就是「用自己做的台子替换 Slot 的圆柱」。
素材版权规矩也写在里面：**只用 CC0 / CC-BY，CC-BY-NC 和"游戏提取模型"一律不碰**，
每引入一个第三方素材都要在 `unity/Assets/Art/CREDITS.md` 登记。

**Unity 基础对照清单**：[`unity-basics.md`](unity-basics.md)
—— 14 个概念，每条都指到项目里真实位置 + 一个"改一行就能验"的小实验 + 四周节奏。
foilo 说下一步先学 Unity 基础、再把模型按类归置，这份就是给他对着学的。

**原画起步计划**：[`concept-art-plan.md`](concept-art-plan.md)
—— foilo 2026-10-17 定的方向：**先手绘原画 → 再 Blender 建模 → 打包卖（闲鱼）**。
8 周计划（每周一主题、周末一张成品），每周产出都要求能进这个世界（第 6 周画台子 → 建模替换）；
第 5 周起接小额单（头像/插画 ¥30~150）。第一周只用纸笔，**别先买设备**。


### Slot_2 已开张（2026-10-17）：黎曼面（√z 的两片叶子）

- 形态：一条**绕两圈的螺旋带**（`MeshMath.RiemannHelix`），绕一圈换到另一片叶子、绕两圈回到原来那片。
  半径 0.35–1.60 m、每圈升 0.35 m、共两圈；贴在 Slot_2 台面上，**挂了 MeshCollider 能站上去**。
- 颜色：贴图逐像素算 `z = r·e^{iu} → w = √z → ComplexColor 取色`（与 Slot_1 同一套规则）。
  两圈下来色相正好转一整圈 → **接缝处不跳色**（有断言钉着）。
- UV：螺旋的绕角参数**自带 UV**（`MeshData.Uvs`），**不能**再用 `SetPlanarUVs` —— 平面投影会把它抹平。
- 验证数字：引擎外断言新增 7 条（顶点/三角形/UV/半径/高度/接缝回到同点/接缝不跳色/另一片叶子颜色不同）·
  headless `Generate exit 0` · `Verify OK`：**`Exhibit_RiemannSqrt 顶点=3133 UV=3133 贴图=True`**
  （3133 = 241×13）· objects=207 meshes=180

**Backlog（明确以后再做，现在不碰）**：
- **语音通话模式的"连机 / 线上"**（foilo 2026-10-17 定：**等有服务器、人多了再做**）。
  现状只能本机用：GUI 在 `127.0.0.1`、识别走 Host 侧 speech 服务、播报地址写死在客户端。
  将来第一步：把 TTS/STT 地址变成配置项 + 服务加 token（别裸奔在公网）。

## 四、怎么跑起来

| 东西 | 路径 |
| --- | --- |
| 仓库（真相所在） | `C:\Users\nb666\Documents\deepseek-harness\default-workspace\vr-math-world` |
| Unity 工程 | `C:\Projects\VRMathWorld`（内容由代码生成，场景只当容器） |
| 验证工程（独立，用于 headless 验证） | `C:\Projects\_verify` |
| Unity 编辑器 | `C:\Program Files\Unity 6000.0.85f1\Editor\Unity.exe` |
| 语音服务 | 桥接 `http://127.0.0.1:7880`（上游一键包 9880，开机自启） |

### 仓库与工程是**同一份文件**（2026-10-17 起，junction 穿透）

以前仓库里只放 `Scripts`/`Editor` 两份副本，每次改代码都要手工同步一遍
（2026-10-17 那天同步了两次、逐哈希核对 —— 这种"靠人记住"的步骤迟早会漏）。现在：

| 仓库里的 | 实际是 | 指向 |
| --- | --- | --- |
| `unity/Assets` | **目录 junction** | `C:\Projects\VRMathWorld\Assets` |
| `unity/ProjectSettings` | **目录 junction** | `C:\Projects\VRMathWorld\ProjectSettings` |
| `unity/Packages` | **目录 junction** | `C:\Projects\VRMathWorld\Packages` |

于是：**改代码 = 改工程；改完直接提交推送，没有"同步"这一步了。**
`C:\Projects\_verify\Assets\{Scripts,Editor}` 也是指向主工程同样两个目录的 junction ——
所以 headless 验证**永远吃当前代码**，同样不需要同步。

**唯一不进库的是 `unity/Assets/Scenes/`**：`Sandbox.unity` 有 3.9 MB，而且内容 100% 由代码生成，
提交它只会让每次生成都造一个几 MB 的二进制 diff。
`.meta` 反过来**必须**进库（缺了它，别人 clone 后 GUID 重排、场景里挂的组件会连错）。

**重新 clone / 换机器后要重建 junction**（git 不记 junction，只会给出真实的文件夹）：

```powershell
$t = 'C:\Projects\VRMathWorld'; $r = '<仓库>'
New-Item -ItemType Junction -Path "$r\unity\Assets"          -Target "$t\Assets"
New-Item -ItemType Junction -Path "$r\unity\ProjectSettings" -Target "$t\ProjectSettings"
New-Item -ItemType Junction -Path "$r\unity\Packages"        -Target "$t\Packages"
New-Item -ItemType Junction -Path "C:\Projects\_verify\Assets\Scripts" -Target "$t\Assets\Scripts"
New-Item -ItemType Junction -Path "C:\Projects\_verify\Assets\Editor"  -Target "$t\Assets\Editor"
# 2026-10-17 补：美术资产走 Resources.Load，验证工程也必须能看见它，
# 否则 headless Verify 会静默退回程序化占位（"（程序化）"）而看不出问题。
New-Item -ItemType Junction -Path "C:\Projects\_verify\Assets\Resources" -Target "$t\Assets\Resources"
```

⚠️ **绝不带 `-Recurse` 去删 junction**（`Remove-Item -Recurse` / `rm -rf`）—— 那会删到**工程本体**。
要拆就 `Remove-Item <junction 路径>`（不带 `-Recurse`）或 `cmd /c rmdir <junction 路径>`。

**改完代码的标准验证流程（三条都要过）**：

```powershell
# 1) 引擎外的纯数学测试
dotnet run --project <仓库>\tools\meshmath-test

# 2) 生成场景（_verify 吃的就是主工程的脚本，不用同步）
Start-Process -FilePath $unity -Wait -ArgumentList @('-batchmode','-quit','-nographics',
  '-projectPath','C:\Projects\_verify','-executeMethod','BuildScene.Generate','-logFile',$log)
# 3) 自检（硬检查 SurfaceWalker/吉祥物/展品 UV/传送点）
... '-executeMethod','BuildScene.Verify' ...
```

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

**复变函数展品在这几处**：幂次 `complexPower` / 键位 `complexCycleKey` 在 `ExhibitScene` 顶部；
颜色规则在 `Meshes/ComplexColor.cs`（**唯一真相**，贴图与测试都从这里取色；
`ComplexColor.Pow(z,n)` 是幂函数本体）；两处摆放与贴图缓存在 `ExhibitScene.BuildComplexColorMap()`
与 `SetComplexPower()`（按 Q 时走这里）。

**键位**：`WASD` 走 · `Shift` 跑 · `空格` 跳 · `V` 视角规格 · `F5` 相机模式 ·
`E` 讲解/闲聊 · `R` 跟随/漫游/停下 · `Q` 换复变展品幂次（z^1→z^2→z^3→z^4→z^1）·
`1/2/3/4` 传送（**`4` = 数学区**：落在彩色地砖上、面朝 Slot_1 的图版；数学区离出生点 92 米，走过去太久）

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
13. **junction 不能带 `-Recurse` 删**：仓库里的 `unity/Assets` 是指向工程本体的 junction，
    `Remove-Item -Recurse` / `rm -rf` 会**直接删掉 `C:\Projects\VRMathWorld\Assets`**（真文件）。
    拆 junction 用 `Remove-Item <junction 路径>`（不带 -Recurse）或 `cmd /c rmdir <junction 路径>`。
    同理：`Get-ChildItem -Recurse` 会穿透进工程，扫仓库时要记得这一点。
14. **别用 PowerShell 的 `Get-Content -Raw` + `WriteAllText` 去改带中文的源码**（2026-10-17 真翻车）：
    这个 shell 读取 UTF-8 中文会按老代码页解，再写回去整份文件就变乱码、甚至把两行粘成一行；
    正则替换里 `$` 也会被当成替换模式（`$"..."` 插值直接碎掉）。
    → **改源码一律用文件编辑工具**（read/edit）；要批量改就先备份、并逐行按字节处理。
    那天是靠 `git checkout -- <file>` 救回来的 —— **动手前先确认改动可回滚**。
15. **Unity 原生不认 `.glb`**（2026-10-17）：把 Blender 的 glb 丢进 `Assets/`，日志里是
    `DefaultImporter`（而不是 `FBXImporter`），`Resources.Load` 拿不到 → 场景静默退回程序化占位。
    **美术导出用 FBX**；要用 glb 得额外装 `glTFast`。判断办法：看导入日志里的 importer 名字，
    或用 `Verify` 里那条"有资产却没用上就 FAILED"。
16. **`_verify` 工程要把 `Assets/Resources` 也 junction 过来**，否则 headless Verify 看不到美术资产，
    会"看起来通过、其实是占位"。已在第四节补进 junction 清单。

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

