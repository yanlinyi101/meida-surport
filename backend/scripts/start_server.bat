@echo off
echo 正在启动美大客服支持网站...
echo.
echo 确保已安装以下依赖：
echo - Python 3.7+
echo - uvicorn
echo - fastapi
echo - jinja2
echo.
echo 如果未安装，请运行: pip install uvicorn fastapi jinja2
echo.
echo 启动服务器...
uvicorn main:app --reload --host 127.0.0.1 --port 8000
echo.
echo 服务器已启动！
echo 请在浏览器中访问: http://127.0.0.1:8000/
pause 