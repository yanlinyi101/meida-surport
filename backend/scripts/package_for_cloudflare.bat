@echo off
setlocal enabledelayedexpansion

echo 📦 美大客服支持中心 - Cloudflare Pages 打包脚本
echo.

:: 检查site目录是否存在
if not exist "site" (
    echo ❌ site 目录不存在！请先运行构建脚本。
    echo    运行命令: python build_static_site.py
    pause
    exit /b 1
)

:: 创建部署目录
set DEPLOY_DIR=cloudflare_deploy
set ZIP_NAME=meidasupport-frontend.zip

if exist "%DEPLOY_DIR%" (
    echo 🧹 清理旧的部署文件...
    rmdir /s /q "%DEPLOY_DIR%"
)

mkdir "%DEPLOY_DIR%"

echo 📋 复制文件到部署目录...
xcopy "site\*" "%DEPLOY_DIR%\" /E /I /Y > nul

echo 📊 统计信息:
for /f %%i in ('dir "%DEPLOY_DIR%" /s /b ^| find /c /v ""') do set file_count=%%i
echo    - 总文件数: !file_count!

echo.
echo 📦 创建 ZIP 压缩包...

:: 使用PowerShell创建ZIP文件
powershell -Command "Compress-Archive -Path '%DEPLOY_DIR%\*' -DestinationPath '%ZIP_NAME%' -Force"

if %errorlevel% neq 0 (
    echo ❌ ZIP 创建失败！
    pause
    exit /b 1
)

:: 获取ZIP文件大小
for %%A in ("%ZIP_NAME%") do set zip_size=%%~zA

echo ✅ 打包完成！
echo    - ZIP 文件: %ZIP_NAME%
echo    - 文件大小: %zip_size% 字节
echo.

echo 🚀 部署步骤:
echo    1. 访问 https://dash.cloudflare.com/
echo    2. 进入 Pages 页面
echo    3. 点击 "创建项目"
echo    4. 选择 "上传资产"
echo    5. 上传 %ZIP_NAME% 文件
echo.

echo 📁 部署目录: %DEPLOY_DIR%\
echo 📦 ZIP 文件: %ZIP_NAME%
echo.

echo ✨ 准备完成！可以上传到 Cloudflare Pages 了。
pause 