@echo off
chcp 65001 >nul
echo.
echo  =====================================
echo   SZTU_Code  v0.2.0  -  一键配置
echo  =====================================
echo.
echo  正在启动配置脚本...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
echo.
pause