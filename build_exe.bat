@echo off
chcp 65001 >nul
echo ========================================
echo CRTicketMonitor v3.3.0 打包脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 清理旧的打包文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [2/3] 使用 PyInstaller 打包...
pyinstaller --clean CRTicketMonitor.spec

echo [3/3] 检查打包结果...
if exist "dist\CRTicketMonitor.exe" (
    echo.
    echo 打包成功！
    echo.
    echo 可执行文件位置：dist\CRTicketMonitor.exe
    echo.
    echo 复制必需的数据文件...
    if exist "station_codes.json" copy /Y "station_codes.json" "dist\station_codes.json" >nul && echo   - station_codes.json
    if exist "config.json" copy /Y "config.json" "dist\config.json" >nul && echo   - config.json
    echo.
    echo 打包完成！
    echo.
    echo 按任意键打开 dist 目录...
    pause >nul
    explorer "dist"
) else (
    echo.
    echo 打包失败！请检查错误信息
    pause
)
