@echo off
chcp 65001 >nul
echo ========================================
echo 12306 余票监控工具 - 打包脚本
echo ========================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

echo [1/4] 检查 Python 版本...
python --version

echo.
echo [2/4] 安装/更新 PyInstaller...
pip install pyinstaller -q

echo.
echo [3/4] 清理旧文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [4/4] 开始打包...
echo 这可能需要几分钟，请耐心等待...
pyinstaller --clean CRTicketMonitor.spec

if exist "dist\CRTicketMonitor.exe" (
    echo.
    echo ========================================
    echo [成功] 打包完成！
    echo 可执行文件位置：dist\CRTicketMonitor.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo [失败] 打包失败，请检查错误信息
    echo ========================================
)

pause
