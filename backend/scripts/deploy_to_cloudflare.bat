@echo off
echo 🚀 美大客服支持中心 - Cloudflare Pages 部署脚本
echo.

echo 📋 步骤 1: 构建静态网站...
python build_static_site.py

if %errorlevel% neq 0 (
    echo ❌ 构建失败！请检查错误信息。
    pause
    exit /b 1
)

echo.
echo ✅ 构建完成！
echo.

echo 📁 生成的文件位于 site/ 目录中
echo 📊 统计信息:
for /f %%i in ('dir site /s /b ^| find /c /v ""') do echo    - 总文件数: %%i
for /f %%i in ('dir site\*.html /s /b ^| find /c /v ""') do echo    - HTML 文件: %%i

echo.
echo 🌐 部署选项:
echo    1. 直接上传: 将 site/ 目录内容打包上传到 Cloudflare Pages
echo    2. Git 部署: 将 site/ 目录推送到 Git 仓库，然后连接到 Cloudflare Pages
echo.

echo 📋 下一步操作:
echo    1. 访问 https://dash.cloudflare.com/
echo    2. 进入 Pages 页面
echo    3. 创建新项目
echo    4. 上传 site/ 目录内容或连接 Git 仓库
echo.

echo 🔧 配置提醒:
echo    - 记得在 _redirects 文件中配置正确的后端 API 地址
echo    - 可在 Cloudflare Pages 设置中配置自定义域名
echo.

echo ✨ 部署准备完成！
pause 