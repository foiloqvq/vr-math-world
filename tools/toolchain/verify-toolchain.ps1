# 工具链一键自检：MSVC / CMake / Ninja / .NET 是否真的能用
# 规矩：不看"目录存在"，只看"能不能编译并跑出结果"。
$ErrorActionPreference = 'Stop'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$tmp = Join-Path $env:TEMP 'toolchain-selfcheck'
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$pass = 0; $fail = 0

function Report($name, $ok, $detail) {
  if ($ok) { $script:pass++; Write-Host ("  [OK]   {0}  {1}" -f $name, $detail) -ForegroundColor Green }
  else     { $script:fail++; Write-Host ("  [FAIL] {0}  {1}" -f $name, $detail) -ForegroundColor Red }
}

Write-Host "== 版本 ==" -ForegroundColor Cyan
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
$vs = if (Test-Path $vswhere) {
  (& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
} else { '' }
$vcvars = if ($vs) { Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat' } else { '' }
Report 'MSVC BuildTools' ([bool]($vcvars -and (Test-Path $vcvars))) $vcvars
foreach ($c in 'cmake','ninja','dotnet','git') {
  $g = Get-Command $c -ErrorAction SilentlyContinue
  $ver = if ($g) { (& $g.Source --version 2>&1 | Select-Object -First 1) } else { '未安装' }
  Report $c ([bool]$g) $ver
}

Write-Host "== 真的编一个 C++ 程序 ==" -ForegroundColor Cyan
$cpp = @'
#include <cstdio>
#include <numeric>
#include <vector>
int main() {
    std::vector<int> v(10); std::iota(v.begin(), v.end(), 1);
    int s = 0; for (int x : v) s += x;
    std::printf("C++ OK  sum=%d  std=%ld\n", s, (long)__cplusplus);
    return s == 55 ? 0 : 1;
}
'@
Set-Content -Path (Join-Path $tmp 'hello.cpp') -Value $cpp -Encoding UTF8
if ($vcvars -and (Test-Path $vcvars)) {
  # /Zc:__cplusplus 必须带上，否则 MSVC 永远报 199711（C++98）
  $r = cmd /c "call `"$vcvars`" >nul 2>&1 && cd /d `"$tmp`" && cl /nologo /EHsc /std:c++20 /Zc:__cplusplus hello.cpp && hello.exe" 2>&1
  $line = ($r | Where-Object { $_ -match 'C\+\+ OK' } | Select-Object -First 1)
  Report 'C++ 编译并运行' ([bool]$line) $line
} else {
  Report 'C++ 编译并运行' $false '找不到 vcvars64.bat'
}

Write-Host "== 真的跑一个 C# 程序 ==" -ForegroundColor Cyan
$cs = Join-Path $tmp 'cs'
New-Item -ItemType Directory -Force -Path $cs | Out-Null
$proj = '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable></PropertyGroup></Project>'
Set-Content -Path (Join-Path $cs 'cs.csproj') -Value $proj -Encoding UTF8
$prog = @'
using System; using System.Linq;
class P { static int Main() { var s = Enumerable.Range(1,10).Sum();
  Console.WriteLine($"C# OK  sum={s}  .NET {Environment.Version}"); return s == 55 ? 0 : 1; } }
'@
Set-Content -Path (Join-Path $cs 'Program.cs') -Value $prog -Encoding UTF8
$r2 = & dotnet run --project $cs 2>&1
$line2 = ($r2 | Where-Object { $_ -match 'C# OK' } | Select-Object -First 1)
Report 'C# 编译并运行' ([bool]$line2) $line2

Write-Host ""
Write-Host ("结果: {0} 通过 / {1} 失败" -f $pass, $fail) -ForegroundColor Cyan
exit $(if ($fail -eq 0) { 0 } else { 1 })
