@echo off
title Video Creator GUI
echo ========================================
echo   Saabor AI Builds - Video Creator GUI
echo ========================================
echo.
echo 正在启动视频创作GUI应用程序...
echo.

python video_creator_gui.py

if %errorlevel% neq 0 (
    echo.
    echo 错误：应用程序启动失败
    echo 请检查：
    echo 1. Python是否已正确安装
    echo 2. 必要的依赖库是否已安装
    echo 3. auto_video_maker.py文件是否存在
    echo.
    pause
)