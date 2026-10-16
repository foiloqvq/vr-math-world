# Unity 环境搭建（人类操作清单）

> 工具链（MSVC / .NET / CMake / Ninja）已经装好并自检通过；这里只剩引擎本身。

## 1. 安装 Editor

1. 开始菜单 → **Unity Hub** → 右上角 **Sign in**（没有账号就注册，个人版免费）
2. 左侧 **Installs** → **Install Editor** → 选 **Unity 6 LTS**（认准 LTS，别选 beta / tech stream）
3. 勾模块：

| 模块 | 现在 | 说明 |
| --- | --- | --- |
| **Windows Build Support (IL2CPP)** | ✅ 必勾 | PC 版构建 |
| Android Build Support + OpenXR | ⏳ 等 VR 设备到了再加 | 模块可随时补装（Hub 里点齿轮 → Add modules） |
| iOS / WebGL / Linux | ❌ | 用不上，别占空间 |

4. 装完激活 **Personal** 许可证（这一步只有你能点）

## 2. 建工程

- 模板：**Universal 3D (URP)** —— VR 性能更好，材质也现代
- 工程名建议：`VRMathWorld`
- 位置建议：`C:\Projects\VRMathWorld`（**不要**放在 `My_Library` 仓库里，Unity 工程太大；
  只把 `Assets/Scripts` 和 `ProjectSettings` 之类纳入版本控制，见 unity/.gitignore）

## 3. 把脚本挂进工程

1. 新建空场景，命名 `Sandbox`
2. 建空 GameObject → 命名 `World`
3. 加组件 `ExhibitScene`（会生成地面、光照、两件展品）
4. 建空 GameObject → 命名 `Player` → 加 `CharacterController` + `FirstPersonWalker`，
   在其下建一个 `Camera` 子物体（高度约 1.7）
5. 按 **Play**，用 WASD + 鼠标走一圈

## 4. 输入系统的坑

`FirstPersonWalker` 用传统 `Input.GetAxis`。若工程报 `InvalidOperationException`，
到 **Edit → Project Settings → Player → Active Input Handling** 改成 **Both**，重启 Editor。

## 5. 命令行构建（等工程建好后可用）

```bat
"C:\Program Files\Unity\Hub\Editor\<版本>\Editor\Unity.exe" ^
  -batchmode -quit -nographics ^
  -projectPath "C:\Projects\VRMathWorld" ^
  -executeMethod BuildScript.BuildWindows ^
  -logFile build.log
```

配合一个 `Assets/Editor/BuildScript.cs`（下一轮我给）就能一条命令出包，也方便以后挂 CI。

## 6. XR（VR 设备到货后再做）

1. Hub 里给 Editor 补装 **Android Build Support**（Quest 类）或装 PCVR 对应模块
2. Package Manager 装 **XR Interaction Toolkit** 与 **XR Plugin Management**
3. Project Settings → XR Plug-in Management 勾选目标平台（Quest / SteamVR / OpenXR）
4. 把 `Player` 换成 `XR Origin`，相机改 `Camera Offset` —— 现有 `ExhibitScene` 不用改
   （展品是普通 GameObject，跟 XR 无关）