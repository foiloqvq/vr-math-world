@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set /p TK=<"%~dp0bridge\token.txt"
set TSUKUYOMI_TOKEN=%TK%
set TSUKUYOMI_INSTANCE=%RANDOM%%RANDOM%
start "yachiyo-upstream" /min "%~dp0runtime\python\python.exe" -I "%~dp0app\bootstrap.py" nvidia serve 9880
timeout /t 60 /nobreak >nul
start "yachiyo-bridge" /min "%~dp0runtime\python\python.exe" "%~dp0bridge\server.py"
timeout /t 6 /nobreak >nul
start "yachiyo-warmup" /min "%~dp0runtime\python\python.exe" "%~dp0bridge\warmup.py"