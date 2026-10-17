# Unity 基础对照清单（学一样，改一处，验一次）

> 2026-10-17 立。为什么这么做：Unity 教程里 90% 的例子跟我们没关系（角色控制器、地形、
> 网络同步…）。这份清单只挑**这个世界真的用到的**，每条都写清「在项目里的哪个位置」
> 和「你可以动手改的那一行」。**学完一条就改一行、按 Play 看变化**，比看十集视频快。

## 一、先搞清这套世界的特殊结构（很重要）

**我们的场景是"空的"**：`Assets/Scenes/Sandbox.unity` 里只有 `World` 和 `Player` 两个空物体，
**其余所有内容都是代码在 `Awake` 里生成的**（`ExhibitScene`）。

- 好处：改代码就生效，不用手摆场景，也没有"场景文件和代码不一致"的坑。
- 代价：**在 Hierarchy 里手拖的东西，一按 Play 就会被清空重建**（`ClearGenerated()`）。
  所以别在场景里手动摆东西 —— 要加东西就改代码。

## 二、清单（按建议顺序）

### 1. GameObject / Transform / 父级

- **概念**：每个物体都有 Transform；`SetParent(other, false)` 的第二个参数是
  "保持本地坐标不变"。
- **项目里**：`ExhibitScene.BuildMathDistrict()` 里 `slot.transform.SetParent(root.transform, false)`。
- **动手**：把某个展品的 `localPosition` 的 y 从 0.95 改成 1.6，按 Play 看它飘起来。
- **验证**：位置变了但没跑偏 = 父子关系没搞错。

### 2. 组件（Component）与 GetComponent

- **概念**：GameObject 是空壳，能力来自组件；`MeshFilter`(形状) + `MeshRenderer`(外观)
  + `Collider`(碰撞) 是 3D 物体的三件套。
- **项目里**：`MeshUtil.Spawn()` 就是加这三件套的地方。
- **动手**：给某个展品加一句 `go.AddComponent<BoxCollider>()`，看你能不能站上去。
- **验证**：能站上去 = Collider 生效；不能 = 你加错物体了。

### 3. 生命周期：Awake / Start / Update / OnGUI

- **概念**：`Awake` 最早（建世界）、`Start` 第一帧前、`Update` 每帧、`OnGUI` 画界面。
- **项目里**：`ExhibitScene.Awake()` 建世界；`SurfaceWalker.Update()` 走/跳/贴地；
  `SpeedHud.OnGUI()` 画左上角那些字。
- **动手**：在 `SurfaceWalker.Update()` 里加一行 `if (Input.GetKeyDown(KeyCode.P)) Debug.Log(transform.position);`
- **验证**：按 P 控制台有输出 = 你打通了"输入 → 脚本"。

### 4. Prefab 与 Instantiate（美术资产的入口）

- **概念**：Prefab 是"能复制的模板"；`Instantiate(prefab, parent)` 生成实例。
- **项目里**：`ExhibitScene.BuildMathDistrict()` 里 `Instantiate(pedestalArt, root.transform)`
  —— 就是把你 Blender 做的台子放进去。
- **动手**：把 `Resources/Art/SlotPedestal.fbx` 换成你自己做的（同尺寸），按 Play。
- **验证**：台子变了 = 美术流水线通了。

### 5. 资源导入与 Resources.Load

- **概念**：`Assets/Resources/` 下的东西可以在运行时按名字加载（`Resources.Load`）。
- **项目里**：`Resources.Load<GameObject>("Art/SlotPedestal")`；找不到就退回程序化圆柱。
- **动手**：把文件改个名，按 Play —— 会发现台子变回灰色圆柱（**这就是"优雅降级"**）。
- **验证**：改回去，台子又回来了。理解"缺资源不崩"的设计。

### 6. 材质与光照（MaterialKit）

- **概念**：材质决定"看起来是什么"；自发光（Emission）让暗场里的展品自己发亮。
- **项目里**：`MaterialKit.MakeMaterial(color, smoothness, metallic)`、
  `SetEmissionTexture(mat, tex, intensity)`。
- **动手**：把复变图版的 `complexMapGlow` 从 0.85 改成 0.2，按 Play。
- **验证**：图版变暗 = 你摸到了"材质参数"这个旋钮。

### 7. 碰撞体与物理查询（最容易踩坑的一块）

- **概念**：`MeshCollider` 贴合任意网格（我们的曲面靠它）；`BoxCollider` 是盒子；
  `Physics.Raycast` 从一点往下打射线找地面。
- **项目里**：`SurfaceWalker.Update()` 里那两句 `Physics.Raycast(..., playerLayerMask)` 决定
  "站在什么上面"；`SlotPedestal` 必须用 `BoxCollider`（圆柱原始碰撞体是胶囊，顶面盖不全）。
- **动手**：把某个台子的 `BoxCollider` 删掉，按 Play 站上去 —— 会掉下去。
- **验证**：加上就站得住。**这一条你亲手试过，就再也不会困惑"为什么掉虚空"。**

### 8. 输入（Input）

- **概念**：`GetKey/GetKeyDown`（键盘）、`GetAxis/GetAxisRaw`（轴，-1..1）、
  `Input.GetMouseButton`。
- **项目里**：`SurfaceWalker` 用 `GetAxisRaw("Vertical")` 走、`GetKeyDown(jumpKey)` 跳、
  `GetKeyDown(Alpha4)` 传送；`ExhibitScene.Update` 用 `Q` 换幂次。
- **动手**：把 `complexCycleKey` 从 `Q` 改成 `T`。
- **验证**：按 T 才换幂次 = 你理解了"按键 → 行为"的绑定。

### 9. 脚本间通信（三种，各有用途）

- **概念**：`GetComponent<T>()`（同一物体）、`FindObjectOfType<T>()`（全场景找一个）、
  **静态字段**（最省事但最脏）、`SerializedField`/引用（编辑器里拖）。
- **项目里**：`SpeedHud.ComplexStatus` 是静态字符串（展品写、HUD 读）；
  `walker = FindFirstObjectByType<SurfaceWalker>()`。
- **动手**：在 `SpeedHud.OnGUI` 里把 `ComplexStatus` 换成你自己的文字。
- **验证**：屏幕上的字变了 = 你改了"两个脚本之间的数据"。

### 10. 编辑器扩展（Editor 脚本）

- **概念**：放在 `Assets/Editor/` 的脚本只在编辑器里跑，可以加菜单、批处理。
- **项目里**：`BuildScene`（菜单 VRMathWorld/生成沙盒场景 + `-executeMethod` 批处理）、
  `ArtImportSettings`（自动打开 FBX 的轴转换）。
- **动手**：给自己加一个菜单项，点一下 `Debug.Log("hello")`。
  ```csharp
  using UnityEditor;
  public static class MyTool { [MenuItem("VRMathWorld/打个招呼")] static void Hi() { UnityEngine.Debug.Log("hello"); } }
  ```
- **验证**：菜单里出现你那一项 = 你会写编辑器工具了。

### 11. 批处理与日志（我们的"自动验证"）

- **概念**：Unity 能不开界面跑：`-batchmode -quit -nographics -executeMethod 类.方法 -logFile 文件`。
- **项目里**：`BuildScene.Generate` 生成场景、`BuildScene.Verify` 检查十几种"必须成立"的条件。
- **动手**：跑一次 Verify，故意把某个尺寸改错，看它怎么 `FAILED`。
- **验证**：看到 `[BuildScene] Verify FAILED: ...` 并退出码非 0 = 你理解了"断言式验证"。

### 12. 性能的基本概念（够用就行）

- **概念**：顶点数、材质数（材质越多越慢）、Draw Call、每帧别做重活。
- **项目里**：复变贴图 512² 算一次 40ms —— 所以**缓存**（`ComplexTextureFor`）；
  黎曼面带 3133 顶点、分数地砖 625 顶点。
- **动手**：把 `RiemannSegU` 从 240 改成 120，看顶点数减半。
- **验证**：Verify 报的顶点数从 3133 变成 1573（约）= 你摸到了"细分段数=精度/成本"。

### 13. UI：为什么现在用 OnGUI

- **概念**：`OnGUI` 是即时模式 UI，最简单、不依赖任何 UI 包；Canvas/TMP 是正式 UI，功能强但重。
- **项目里**：`SpeedHud` 全部用 `OnGUI` —— 因为"左上角几行字"用 Canvas 是杀鸡用牛刀。
- **动手**：在 `OnGUI` 里加一行显示 `Time.time.ToString("F1")`。
- **验证**：屏幕上多一个秒数 = 你会画最简单的 UI 了。

### 14. 音频（下一站会用）

- **概念**：`AudioSource.PlayOneShot`；运行时可以用 `AudioClip.Create` 或加载 wav。
- **项目里**：讲解已经走本机 TTS（`POST 127.0.0.1:7880` 拿 wav），但**播放**还没接进 Unity。
- **动手（下一步功能）**：把 TTS 返回的 wav 变成一个 AudioClip 播出来。
- **验证**：按 E 能听到八千代念讲解 = 语音进世界了。

## 三、四周节奏建议（和美术计划对齐）

| 周 | Unity 学什么 | 对应清单 |
| --- | --- | --- |
| 第 1 周 | 物体/组件/生命周期 + 输入 | 1–3、8 |
| 第 2 周 | 美术资产进 Unity（Prefab/Resources/材质/光照） | 4–6 |
| 第 3 周 | 碰撞体与物理查询（重点，直接对应"掉虚空"那个坑） | 7 |
| 第 4 周 | 编辑器扩展 + 批处理验证 + 性能概念 | 10–12 |

**每天只做一件事**：改一行 → 按 Play 或跑 Verify → 看数字/画面变了 → 记一句在 `journal` 里。
