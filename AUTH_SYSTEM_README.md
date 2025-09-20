# 美大客服支持系统 - 认证管理后台

基于 FastAPI 的完整账号体系，包含登录/登出/刷新、角色权限（RBAC）、用户管理、审计日志、2FA（双因素认证）、邮件找回密码等功能。

## 🚀 功能特性

### 🔐 认证系统
- **JWT Cookie 认证**：使用 HttpOnly Cookie 存储 Access/Refresh Token
- **自动刷新**：前端无感知的 Token 自动更新
- **安全性**：跨域同源安全，防止 XSS 攻击
- **登录限流**：基于 IP 和邮箱的登录频率限制

### 🛡️ 权限控制 (RBAC)
- **角色管理**：支持多角色分配
- **权限控制**：细粒度的权限管理
- **内置角色**：
  - `admin` - 系统管理员（全部权限）
  - `ops_manager` - 运营经理（用户管理、工单查看）
  - `agent` - 客服专员（工单处理、保修查询）
  - `viewer` - 只读用户（仅查看权限）

### 👥 用户管理
- **用户CRUD**：完整的用户增删改查
- **角色分配**：灵活的用户角色管理
- **账户状态**：激活/停用用户账户
- **批量操作**：支持批量用户操作

### 🔒 双因素认证 (2FA)
- **TOTP支持**：基于时间的一次性密码
- **QR码生成**：支持扫码设置
- **备用码**：提供备用恢复码
- **灵活开关**：用户可自主启用/禁用

### 📧 邮件服务
- **密码重置**：安全的邮件重置链接
- **欢迎邮件**：新用户注册欢迎
- **安全通知**：2FA状态变更通知
- **美观模板**：响应式HTML邮件模板

### 📊 审计日志
- **全面记录**：记录所有关键操作
- **详细信息**：包含用户、IP、时间、详情
- **查询过滤**：支持多维度查询
- **合规支持**：满足审计要求

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI** - 现代化的 Python Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **Alembic** - 数据库迁移管理
- **Pydantic v2** - 数据验证和序列化
- **passlib[bcrypt]** - 密码哈希
- **PyJWT** - JWT 令牌处理
- **pyotp** - 2FA TOTP 实现
- **qrcode** - QR码生成
- **aiosmtplib** - 异步邮件发送
- **slowapi** - API 限流

### 数据模型
- **User** - 用户信息（邮箱、密码、2FA等）
- **Role** - 角色定义
- **Permission** - 权限定义
- **UserRole** - 用户角色关联
- **RolePermission** - 角色权限关联
- **SessionToken** - 会话令牌（刷新令牌）
- **AuditLog** - 审计日志

## 🚀 快速开始

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv new_venv

# 激活虚拟环境 (Windows)
new_venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境配置
创建 `.env` 文件（参考 `.env.example`）：
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./data/app.db
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=1209600
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
ALLOW_SELF_REGISTER=false
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=no-reply@example.com
SMTP_PASS=your-smtp-password
FRONTEND_URL=http://localhost:5173
```

### 3. 数据库初始化
```bash
# 创建数据目录
mkdir data

# 运行种子数据脚本
python -m backend.app.db.seed
```

### 4. 启动服务
```bash
# 使用启动脚本（推荐）
start_auth_server.bat

# 或手动启动
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. 访问系统
- **主页**: http://127.0.0.1:8000/
- **API文档**: http://127.0.0.1:8000/api/docs
- **健康检查**: http://127.0.0.1:8000/health

### 6. 默认账号
- **邮箱**: admin@meidasupport.com
- **密码**: admin123456
- ⚠️ **请首次登录后立即修改密码！**

## 📚 API 接口文档

### 认证接口 (`/api/auth/`)
- `POST /login` - 用户登录
- `POST /logout` - 用户登出
- `POST /refresh` - 刷新令牌
- `GET /me` - 获取当前用户信息
- `POST /register` - 用户注册（可选）
- `POST /password/forgot` - 忘记密码
- `POST /password/reset` - 重置密码
- `POST /password/change` - 修改密码
- `POST /2fa/setup` - 设置2FA
- `POST /2fa/verify` - 验证2FA
- `POST /2fa/disable` - 禁用2FA

### 管理接口 (`/api/admin/`)
- `GET /users` - 获取用户列表
- `POST /users` - 创建用户
- `GET /users/{id}` - 获取用户详情
- `PATCH /users/{id}` - 更新用户
- `POST /users/{id}/deactivate` - 停用用户
- `POST /users/{id}/reactivate` - 激活用户
- `POST /users/{id}/reset-password` - 重置用户密码
- `POST /users/{id}/roles` - 分配用户角色
- `GET /roles` - 获取角色列表
- `POST /roles` - 创建角色
- `GET /roles/{id}` - 获取角色详情
- `PATCH /roles/{id}` - 更新角色
- `DELETE /roles/{id}` - 删除角色
- `GET /permissions` - 获取权限列表
- `GET /audit-logs` - 获取审计日志

## 🔒 安全特性

### Cookie 安全
- **HttpOnly**: 防止 XSS 攻击
- **Secure**: HTTPS 环境下启用
- **SameSite**: 防止 CSRF 攻击
- **自动过期**: Access Token 短期，Refresh Token 长期

### 密码安全
- **bcrypt 哈希**: 安全的密码存储
- **密码强度**: 最少8位字符要求
- **重置安全**: 一次性重置令牌，1小时过期

### 会话管理
- **令牌撤销**: 支持主动撤销会话
- **多设备**: 支持多设备同时登录
- **过期清理**: 自动清理过期令牌

### 限流保护
- **登录限流**: 5次/分钟（可配置）
- **IP级别**: 基于IP地址限制
- **邮箱级别**: 基于邮箱地址限制

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_auth.py

# 运行带覆盖率的测试
pytest --cov=backend
```

### 测试覆盖
- ✅ 用户认证流程
- ✅ 权限检查
- ✅ API 端点
- ✅ 数据模型
- ✅ 错误处理

## 🔧 配置说明

### 环境变量
| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT 签名密钥 | `please_change_me` |
| `DATABASE_URL` | 数据库连接URL | `sqlite:///./data/app.db` |
| `JWT_ACCESS_TTL_SECONDS` | Access Token 过期时间 | `900` (15分钟) |
| `JWT_REFRESH_TTL_SECONDS` | Refresh Token 过期时间 | `1209600` (14天) |
| `COOKIE_SECURE` | Cookie Secure 标志 | `true` |
| `COOKIE_SAMESITE` | Cookie SameSite 策略 | `lax` |
| `ALLOW_SELF_REGISTER` | 允许自注册 | `false` |
| `SMTP_HOST` | SMTP 服务器地址 | `smtp.example.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` | SMTP 用户名 | `no-reply@example.com` |
| `SMTP_PASS` | SMTP 密码 | `` |
| `FRONTEND_URL` | 前端URL | `http://localhost:5173` |

### 内置权限
| 权限代码 | 描述 |
|----------|------|
| `users.read` | 查看用户信息 |
| `users.write` | 创建和编辑用户 |
| `users.delete` | 删除用户 |
| `roles.read` | 查看角色信息 |
| `roles.write` | 创建和编辑角色 |
| `roles.delete` | 删除角色 |
| `tickets.read` | 查看工单信息 |
| `tickets.write` | 创建和编辑工单 |
| `tickets.delete` | 删除工单 |
| `tickets.assign` | 分配工单 |
| `warranty.read` | 查看保修信息 |
| `warranty.write` | 编辑保修信息 |
| `warranty.reindex` | 重建保修索引 |
| `centers.read` | 查看服务中心信息 |
| `centers.write` | 编辑服务中心信息 |
| `audit.read` | 查看审计日志 |
| `system.admin` | 系统管理权限 |

## 🚀 部署建议

### 生产环境
1. **更改默认密钥**: 设置强随机 `SECRET_KEY`
2. **使用HTTPS**: 启用 `COOKIE_SECURE=true`
3. **配置SMTP**: 设置真实的邮件服务
4. **数据库**: 使用 PostgreSQL 或 MySQL
5. **反向代理**: 使用 Nginx 或 Apache
6. **监控**: 配置日志和监控系统

### Docker 部署
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📝 更新日志

### v1.0.0 (2024-01-XX)
- ✨ 完整的JWT Cookie认证系统
- ✨ RBAC角色权限控制
- ✨ 用户和角色管理
- ✨ 双因素认证(2FA)
- ✨ 邮件密码重置
- ✨ 审计日志记录
- ✨ API限流保护
- ✨ 完整的单元测试

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请：
1. 查看 [API文档](http://127.0.0.1:8000/api/docs)
2. 创建 [Issue](https://github.com/your-repo/issues)
3. 联系开发团队

---

**美大客服支持系统** - 让客服管理更简单、更安全、更高效！ 🎉 