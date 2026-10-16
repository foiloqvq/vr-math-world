@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || (echo cannot find vcvars64.bat & exit /b 1)
cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release || exit /b 1
cmake --build build || exit /b 1
build\hello.exe