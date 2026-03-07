@echo off
echo ========================================
echo FFmpeg 自动安装脚本
echo ========================================

echo 正在下载 FFmpeg...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z' -OutFile 'ffmpeg-full.7z'}"

echo 正在解压 FFmpeg...
if exist "C:\Program Files\7-Zip\7z.exe" (
    "C:\Program Files\7-Zip\7z.exe" x ffmpeg-full.7z -o"C:\ffmpeg"
) else (
    echo 请先安装 7-Zip 或手动解压 ffmpeg-full.7z 到 C:\ffmpeg
    pause
    exit /b 1
)

echo 正在配置环境变量...
setx PATH "%PATH%;C:\ffmpeg\bin"

echo 安装完成！请重启命令行窗口后运行: ffmpeg -version
pause