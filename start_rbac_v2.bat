@echo off
echo 🚀 启动美大客服支持系统 - RBAC v2 版本
echo.
echo 🔐 RBAC v2 新特性:
echo   - 完整的角色权限管理系统
echo   - 权限分类和聚合计算
echo   - 系统角色保护机制
echo   - 审计日志记录
echo   - 前端管理界面
echo.
echo 📍 管理界面:
echo   - 角色管理: http://127.0.0.1:8000/admin/roles
echo   - 权限管理: http://127.0.0.1:8000/admin/permissions
echo   - 用户管理: http://127.0.0.1:8000/admin/users
echo   - 管理后台: http://127.0.0.1:8000/admin
echo   - 用户首页: http://127.0.0.1:8000/
echo.

REM 激活虚拟环境
call new_venv\Scripts\activate.bat

REM 运行数据库迁移
echo 📋 运行数据库迁移...
python -c "
from alembic.config import Config
from alembic import command
import os

try:
    if os.path.exists('alembic/versions/001_rbac_v2_add_category_and_system_roles.py'):
        alembic_cfg = Config('alembic.ini')
        command.upgrade(alembic_cfg, 'head')
        print('✅ 数据库迁移完成')
    else:
        print('⚠️  迁移文件不存在，跳过迁移')
except Exception as e:
    print(f'⚠️  迁移失败: {e}')
"

REM 初始化RBAC v2数据
echo.
echo 🗄️ 初始化RBAC v2数据...
python backend/scripts/seed_rbac_v2.py

REM 运行基础测试
echo.
echo 🧪 运行基础功能测试...
python -m pytest backend/tests/test_rbac_v2.py -v --tb=short

echo.
echo ✅ 启动服务器...
echo.
echo 🔑 默认管理员账号:
echo   邮箱: admin@meidasupport.com
echo   密码: admin123456
echo.
echo 📋 系统角色:
echo   - admin: 系统管理员 (所有权限)
echo   - agent: 客服代理 (工单和保修)
echo   - viewer: 只读用户 (查看权限)
echo   - ops_manager: 运营经理 (用户和运营)
echo.
echo ⚠️  注意: 请首次登录后立即修改默认密码！
echo.

REM 启动服务器
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload 