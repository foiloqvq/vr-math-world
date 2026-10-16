@echo off
cd /d "%~dp0"
echo 打开浏览器访问: http://127.0.0.1:8000
echo 关掉这个窗口即停止服务。
python -m http.server 8000