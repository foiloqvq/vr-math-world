@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || (echo cannot find vcvars64.bat & exit /b 1)
cl /nologo /EHsc /std:c++20 /Zc:__cplusplus hello.cpp || exit /b 1
hello.exe