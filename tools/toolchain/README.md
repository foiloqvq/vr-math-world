# toolchain/ — 开发工具链

**分工**：C/C++/C# 与引擎侧（Unity / Unreal）由 **foilo qvq** 主写；工具链安装、脚本与文档由 **大肥鱼** 负责。

## 已装（2026-10-16，winget）

| 工具 | 版本 | 位置 | 用途 |
| --- | --- | --- | --- |
| **MSVC BuildTools + C++ 工作负载** | VS 2022 17.14 | `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools` | C/C++ 编译器 + Windows SDK —— **UE / Unity 原生插件的地基** |
| .NET SDK | 8.0.426 | `C:\Program Files\dotnet` | C# 编译（Unity 脚本、工具） |
| CMake | 4.4.4 | `C:\Program Files\CMake` | 跨平台构建系统 |
| Ninja | 1.13.2 | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ninja-build.Ninja_*` | 快速构建器 |
| Unity Hub | 3.22.3 | `C:\Program Files\Unity Hub\Unity Hub.exe` | 引擎管理器（Editor 需登录后装） |
| Git | — | `C:\Program Files\Git` | 版本控制 |
| VS Code | — | `%LOCALAPPDATA%\Programs\Microsoft VS Code` | 编辑器 |
| Epic Games Launcher | 已存在 | `C:\Program Files\Epic Games\Launcher` | Unreal Engine 的入口（登录后装 UE） |

## 一键自检

```powershell
powershell -ExecutionPolicy Bypass -File toolchain\verify-toolchain.ps1
```

它做的不是"看目录在不在"，而是：找 `vcvars64.bat` → **编译并运行**一个 C++ 程序 → **建并运行**一个 C# 程序 → 打印各工具版本。
全部通过时退出码 0，任何一项失败退出码 1（可以挂进将来的 CI）。

## 还没装（需要你自己登录 / 决定）

| 东西 | 体量 | 怎么装 |
| --- | --- | --- |
| Unity Editor（+ XR / Android 模块） | 约 15~25GB | Unity Hub 登录 → Installs → 选 LTS → 勾 XR 模块 |
| Unreal Engine 5.x（含 C++ 支持） | 约 100~130GB | Epic Games Launcher 登录 → Unreal Engine → 安装（勾 C++） |
| Visual Studio 完整 IDE（可选） | 约 15GB | 想在 IDE 里写 C++/C# 再装；现在 BuildTools + VS Code 已经够编 |

磁盘：C: 可用 205GB。**UE 一个就吃掉一半**，建议引擎别同时装两个。

## 常用命令

```bat
:: 先加载 MSVC 环境（每个新终端都要）
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

:: 直接编
cl /nologo /EHsc /std:c++20 /Zc:__cplusplus hello.cpp && hello.exe

:: CMake + Ninja
cmake -G Ninja -B build && cmake --build build

:: C#
dotnet run
```

**两个坑记在这里**：

1. `/Zc:__cplusplus` 必须加 —— 否则 MSVC 永远把 `__cplusplus` 报成 `199711`（看起来像 C++98，其实标准是生效的）。
2. 新装的工具（cmake / ninja）不会出现在**已经打开**的终端里 —— 要么重开终端，要么在脚本开头重新读注册表里的 PATH：
   `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`
3. **`.ps1` 必须带 UTF-8 BOM** —— `powershell.exe`(5.1) 对没有 BOM 的脚本按 GBK 解码，
   中文会变乱码、引号也会被撑破（我写这个脚本时正好踩了，报错里出现 `'鏈畨瑁?` 就是"未安装"被读坏了）。
   修法：`[IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($true))`。
   （`pwsh` 7 默认 UTF-8 无此问题；本仓库脚本都带 BOM，方便两种 PowerShell 都能跑。）

## Unity Hub 的坑（winget 包是坏的）

winget 的 `Unity.UnityHub` **会报"Successfully installed"但一个文件都不落地**（重装两次、全盘扫深度 3 都找不到 exe）。
正确装法：从官方 CDN 拿带版本号的安装包并校验，

```powershell
# 官方清单（含版本、大小、sha512）：https://public-cdn.cloud.unity3d.com/hub/prod/latest.yml
$url = 'https://public-cdn.cloud.unity3d.com/hub/prod/3.22.3/UnityHubSetup-3.22.3-x64.exe'
Invoke-WebRequest $url -OutFile "$env:TEMP\UnityHubSetup.exe"
# 校验 sha512（值取自上面的 latest.yml）后静默安装
Start-Process "$env:TEMP\UnityHubSetup.exe" -ArgumentList '/S' -Wait
```

装机结果：`C:\Program Files\Unity Hub\Unity Hub.exe`（3.22.3，184MB，sha512 已核对一致）。
规律：**凡是 winget 报成功但文件不见的，都别信它的报告，去官方清单拿 URL + 哈希自己装**。