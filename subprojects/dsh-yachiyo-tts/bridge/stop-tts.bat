@echo off
setlocal
for %%P in (9880 7880) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P" ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>nul
)