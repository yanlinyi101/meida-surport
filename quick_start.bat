@echo off
echo 🚀 启动美大客服支持系统 - 认证管理后台
echo.

REM 激活虚拟环境
call new_venv\Scripts\activate.bat

REM 初始化数据库（如果需要）
echo 初始化数据库...
python simple_seed.py

echo.
echo ✅ 启动服务器...
echo 访问地址: http://127.0.0.1:8000/
echo API文档: http://127.0.0.1:8000/api/docs
echo.
echo 默认管理员账号:
echo   邮箱: admin@meidasupport.com
echo   密码: admin123456
echo.

REM 启动服务器
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload 