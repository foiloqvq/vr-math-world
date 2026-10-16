# unity/ — Unity 侧

**这个目录是"引擎侧"的起点**：网格数学、展品组件、场景搭建脚本。
设计上刻意分了两层，好处是**装 Unity 之前就能验证**。

## 结构

```
Assets/Scripts/Meshes/    纯数学，不引用 UnityEngine（可在引擎外用 dotnet 测试）
  MeshMath.cs             函数曲面 / 莫比乌斯带的顶点与索引生成
  ParametricSurface.cs    ↑ 的 Unity 组件封装（默认 z = sin(r)/r）
  MobiusStrip.cs          ↑ 的 Unity 组件封装
Assets/Scripts/Scene/
  ExhibitScene.cs         一键搭场景：地面 + 光照 + 展品（Built-in / URP / HDRP 通吃）
  FirstPersonWalker.cs    WASD + 鼠标环视（传统输入）
docs/setup.md             Editor 安装、模块选择、XR 接入、命令行构建
```

## 现在就能验证的部分（不需要 Unity）

```powershell
dotnet run --project ..\tools\meshmath-test
```

它会检查：顶点/三角形数量、索引越界、包围盒、中心尖峰高度，
以及**莫比乌斯带的单面性不变量**（绕 u 一圈闭合到 -v 侧）。当前 11 项全通过。

## 等 Editor 装好后（三步）

1. Unity Hub 里用 **3D (Built-in) 或 URP 模板**新建工程（推荐 URP，VR 性能更好）
2. 把 `Assets/Scripts/` 整个拷进工程的 `Assets/` 下（或直接把这个目录当工程根目录用）
3. 新建空场景 → 建一个空 GameObject → 挂 `ExhibitScene` → 再挂 `FirstPersonWalker`
   （后者需要 `CharacterController` 组件）→ **按 Play**

## 版本相关的注意

| 项 | 说明 |
| --- | --- |
| 输入系统 | 脚本用传统 `Input.GetAxis`。若工程只启用新 Input System，把 Active Input Handling 设为 **Both**（见 docs/setup.md） |
| 渲染管线 | `ExhibitScene` 里材质用"探测属性名"的方式创建，Built-in / URP / HDRP 都能出正确颜色（否则会变粉红） |
| 网格索引 | 顶点超过 65535 时自动切 `IndexFormat.UInt32`（曲面 400 段时会用到） |
| 文字标签 | **暂未加** —— TMP 需要先在 Editor 里导入 Essentials，等你工程建好我按版本加 |
| 柏拉图立体 | **待办** —— Unity 没有四/八/十二/二十面体的内置图元，需要像曲面那样自己生成网格（下一轮做，同样先在引擎外测试） |

## 和网页原型的关系

`prototype/`（Three.js）定位是**数学内容的快速试验田**：改个函数、刷新浏览器就能看。
Unity 是**正式引擎**：PC + VR、UGC、社交、性能都走它。展品数学两边共享同一套公式，
Unity 侧用 `MeshMath.cs`，网页侧用 `main.js` 里对应的生成函数。