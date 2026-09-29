@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0daily-services.ps1" status
set "daily_result=%errorlevel%"
if /I not "%~1"=="--no-pause" pause
exit /b %daily_result%
