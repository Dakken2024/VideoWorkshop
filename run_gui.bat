@echo off
chcp 65001 >nul
title Video Workshop GUI

echo ============================================
echo  Video Workshop - 智能视频创作工具
echo ============================================
echo.

REM 检查 Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo 正在启动 GUI...
python video_gen\gui_launcher.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 启动失败，请检查上述错误信息
    pause
)