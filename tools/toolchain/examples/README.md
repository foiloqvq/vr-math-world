# examples/ — 能双击就跑的示例

三个都**实测跑通**（2026-10-16，编译并运行，退出码 0）。用来确认工具链可用，也当作起手模板。

| 目录 | 做什么 | 怎么跑 |
| --- | --- | --- |
| `hello-cpp/` | 最简 C++：`cl` 直接编 | 双击 `build.bat` |
| `hello-cs/` | C# 控制台 | 双击 `run.bat` |
| `cmake-ninja/` | **真实工程的样子**：CMake + Ninja + MSVC | 双击 `build.bat` |

实测输出：

```
hello-cpp    -> hello-cpp OK  sum(1..10)=55  __cplusplus=202002
hello-cs     -> hello-cs OK   sum(1..10)=55  .NET 8.0.32
cmake-ninja  -> CMake + Ninja + MSVC 链路通了
```

## 起自己的工程

**C++（CMake + Ninja，推荐）**：照抄 `cmake-ninja/` 的结构 —— `CMakeLists.txt` + `src/`，改个名字就是你的工程。

**C#**：`dotnet new console -o 我的工具` 建模板，然后 `dotnet run`。

**Unity / Unreal**：等引擎装好，工程由引擎自己生成（Unity 里选 Built-in 或 URP 模板；UE 选 C++ 模板），
这边的 MSVC / CMake / Ninja 就是它们编译时用的那套，不用再配。

## `.bat` 为什么都是英文

`.bat` 用 GBK 存中文最稳，但跨机器容易乱码。这几个脚本命令很短，就统一写成纯 ASCII —— **少一个编码坑**。
（`.ps1` 则相反，必须带 UTF-8 BOM，见上级目录 README。）