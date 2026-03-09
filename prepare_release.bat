@echo off
chcp 65001 >nul
echo ========================================
echo 准备发布版本
echo ========================================
echo.

cd /d "%~dp0"

set VERSION=3.1.0
set OUTPUT_DIR=release_v%VERSION%

echo 版本: %VERSION%
echo.

if exist "%OUTPUT_DIR%" (
    echo 清理旧的发布目录...
    rmdir /s /q "%OUTPUT_DIR%"
)

echo 创建发布目录: %OUTPUT_DIR%
mkdir "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%\logs"

echo.
echo 复制必需文件...

copy /Y "dist\12306余票监控.exe" "%OUTPUT_DIR%\12306余票监控.exe" >nul
echo   ✓ 12306余票监控.exe

copy /Y "dist\station_codes.json" "%OUTPUT_DIR%\station_codes.json" >nul
echo   ✓ station_codes.json

echo.
echo 复制文档文件...

copy /Y "打包说明.md" "%OUTPUT_DIR%\打包说明.md" >nul
echo   ✓ 打包说明.md

copy /Y "FEATURE_IMPROVEMENTS.md" "%OUTPUT_DIR%\功能改进说明.md" >nul
echo   ✓ 功能改进说明.md

echo.
echo 创建使用说明...

(
echo # 12306 余票监控工具
echo.
echo ## 版本信息
echo.
echo - 版本: %VERSION%
echo - 打包日期: %date%
echo.
echo ## 快速开始
echo.
echo 1. 双击 `12306余票监控.exe` 启动程序
echo 2. 输入出发站和到达站
echo 3. 选择日期，点击"查询"
echo.
echo ## 功能特性
echo.
echo - ✅ 余票实时查询
echo - ✅ 车次类型筛选（高铁/动车/直达/特快/快速）
echo - ✅ 出发站/到达站筛选（同城车站）
echo - ✅ 席别筛选（商务座/一等座/二等座等）
echo - ✅ 时段筛选（00:00-24:00 等）
echo - ✅ 表格排序（开点/到点/历时）
echo - ✅ 车次收藏
echo - ✅ 收藏车次高亮显示（黄色背景）
echo - ✅ 实时监控（自动刷新）
echo - ✅ 车站自动补全
echo - ✅ 余票高亮显示（绿色背景）
echo.
echo ## 文件说明
echo.
echo - `12306余票监控.exe` - 程序主文件
echo - `station_codes.json` - 车站数据（必需）
echo - `config.json` - 配置文件（首次运行自动生成）
echo - `favorites.json` - 收藏列表（首次运行自动生成）
echo - `logs\` - 日志目录（首次运行自动生成）
echo.
echo ## 系统要求
echo.
echo - Windows 7/8/10/11
echo - .NET Framework 4.0 或更高版本
echo - 网络连接（查询车票需要）
echo.
echo ## 常见问题
echo.
echo ### Q: 程序启动报错"车站数据加载失败"
echo A: 确保 `station_codes.json` 与 exe 文件在同一目录
echo.
echo ### Q: 程序闪退
echo A: 1. 检查 `station_codes.json` 是否存在
echo    2. 查看 `logs\` 目录下的错误日志
echo    3. 将程序添加到杀毒软件白名单
echo.
echo ### Q: 如何更新车站数据？
echo A: 替换 `station_codes.json` 文件即可
echo.
echo ## 更新日志
echo.
echo ### v3.1.0 ^(2026-03-09^)
echo - ✨ 新增表格排序功能（点击表头排序）
echo - ✨ 车次类型筛选实时生效
echo - ✨ 出发站/到达站筛选优化（只显示同城站）
echo - ✨ 修复筛选 bug（全选时显示全部）
echo - ✨ 修复收藏高亮显示（黄色背景）
echo - 🐛 优化筛选逻辑和性能
echo.
echo ## 版权信息
echo.
echo Copyright ^(c^) 2026 BH7GUL
echo 仅供个人学习使用，请勿用于商业用途
) > "%OUTPUT_DIR%\README.md"

echo   ✓ README.md

echo.
echo 打包为压缩文件...

powershell -Command "Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath '12306余票监控_v%VERSION%.zip' -Force"

if exist "12306余票监控_v%VERSION%.zip" (
    echo.
    echo ✅ 发布版本准备完成！
    echo.
    echo 压缩包位置: 12306余票监控_v%VERSION%.zip
    dir /b "12306余票监控_v%VERSION%.zip"
    echo.
    echo 压缩包内容:
    echo   - 12306余票监控.exe
    echo   - station_codes.json
    echo   - README.md
    echo   - 打包说明.md
    echo   - 功能改进说明.md
    echo   - logs\ (空目录)
    echo.
    explorer "%OUTPUT_DIR%"
) else (
    echo.
    echo ❌ 压缩失败，请手动压缩 %OUTPUT_DIR% 目录
)

pause
