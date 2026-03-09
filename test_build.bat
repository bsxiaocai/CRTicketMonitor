@echo off
chcp 65001 >nul
echo ========================================
echo 测试打包的 12306 余票监控程序
echo ========================================
echo.

cd /d "%~dp0\dist"

if not exist "12306余票监控.exe" (
    echo ❌ 错误：未找到 12306余票监控.exe
    echo 请先运行 build_exe.bat 进行打包
    pause
    exit /b 1
)

if not exist "station_codes.json" (
    echo ❌ 错误：未找到 station_codes.json
    echo 这是必需的车站数据文件
    pause
    exit /b 1
)

echo ✅ 检测到必需文件
echo   - 12306余票监控.exe (53 MB)
echo   - station_codes.json
echo.

echo 正在启动程序进行测试...
echo.
echo 注意：
echo - 如果程序正常启动，说明打包成功
echo - 测试基本功能：查询、筛选、排序、收藏
echo - 按 Ctrl+C 或关闭窗口停止测试
echo.
echo 按任意键开始测试...
pause >nul

start "" "12306余票监控.exe"

echo.
echo 程序已启动！
echo.
echo 请手动测试以下功能：
echo 1. 输入出发站和到达站，点击"查询"
echo 2. 测试表头排序（点击"开点"、"到点"、"历时"）
echo 3. 测试筛选功能（勾选/取消车次类型）
echo 4. 测试收藏功能
echo 5. 测试车站筛选（查询后查看筛选面板的车站列表）
echo.
echo 测试完成后，可以关闭程序窗口
echo.
pause
