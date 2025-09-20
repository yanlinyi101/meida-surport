# 美大客服支持系统 - RBAC v2 权限管理系统

## 🎯 系统概览

本系统实现了完整的基于角色的访问控制（RBAC v2）权限管理系统，包含后端API、前端管理界面、权限守卫、审计日志等功能。

## 🚀 快速启动

```bash
# 启动RBAC v2系统
start_rbac_v2.bat
```

系统将自动执行：
- 数据库迁移
- 权限和角色初始化
- 基础功能测试
- 服务器启动

## 📍 访问地址

- **用户端首页**: http://127.0.0.1:8000/
- **管理后台**: http://127.0.0.1:8000/admin
- **角色管理**: http://127.0.0.1:8000/admin/roles
- **权限管理**: http://127.0.0.1:8000/admin/permissions
- **API文档**: http://127.0.0.1:8000/api/docs

## 🔑 默认账号

- **邮箱**: admin@meidasupport.com
- **密码**: admin123456
- ⚠️ **请首次登录后立即修改密码！**

## 🏗️ 系统架构

### 后端组件

#### 1. 数据模型 (`backend/app/models/`)
- **Permission**: 权限模型，支持分类管理
- **Role**: 角色模型，支持系统角色保护
- **User**: 用户模型，多角色支持
- **AuditLog**: 审计日志模型

#### 2. 服务层 (`backend/app/services/`)
- **RBACService**: 权限聚合计算、角色CRUD、系统保护
- **AuthService**: 认证服务，返回有效权限
- **AuditService**: 审计日志记录

#### 3. API接口 (`backend/app/api/`)
- **权限管理**: `GET /api/admin/permissions`
- **角色管理**: `GET/POST/PATCH/DELETE /api/admin/roles`
- **用户角色分配**: `POST /api/admin/users/{id}/roles`
- **用户信息**: `GET /api/auth/me` (包含effective_permissions)

#### 4. 权限依赖 (`backend/app/core/deps.py`)
- **require_perms()**: 多权限检查依赖
- **require_permission()**: 单权限检查依赖
- **预定义依赖**: require_users_read, require_roles_write等

### 前端组件

#### 1. 管理界面 (`templates/`)
- **admin_roles.html**: 角色管理页面
- **admin_permissions.html**: 权限管理页面
- **admin_home.html**: 管理后台首页
- **user_home.html**: 用户端首页

#### 2. 功能特性
- 响应式设计，支持移动端
- 实时搜索和分页
- 权限分类展示
- 系统角色保护提示
- 操作确认对话框

## 🔐 权限系统

### 权限分类

| 分类 | 权限代码 | 描述 |
|------|----------|------|
| **用户管理** | users.read, users.write | 用户查看和编辑权限 |
| **角色权限** | roles.read, roles.write | 角色查看和编辑权限 |
| **权限管理** | permissions.read | 权限查看权限 |
| **审计日志** | audit.read | 审计日志查看权限 |
| **工单管理** | tickets.read, tickets.write | 工单查看和编辑权限 |
| **保修管理** | warranty.read, warranty.reindex | 保修查看和重建索引权限 |
| **服务中心** | centers.write | 服务中心管理权限 |
| **AI功能** | ai.workflow.run, ai.chat | AI工作流和聊天权限 |
| **地理位置** | geo.read | 地理位置查看权限 |
| **系统管理** | system.admin | 系统管理权限 |

### 系统角色

| 角色 | 类型 | 权限范围 | 说明 |
|------|------|----------|------|
| **admin** | 系统角色 | 所有权限 | 系统管理员，不可删除和重命名 |
| **agent** | 系统角色 | tickets.*, warranty.read | 客服代理，处理工单和保修查询 |
| **viewer** | 系统角色 | *.read | 只读用户，仅查看权限 |
| **ops_manager** | 系统角色 | users.read, tickets.read, warranty.reindex, centers.write | 运营经理，用户管理和运营权限 |

### 权限聚合

系统支持权限聚合计算，用户的有效权限是其所有角色权限的并集：

```python
effective_permissions = rbac_service.aggregate_permissions(user)
```

## 🛡️ 安全特性

### 1. 系统角色保护
- 系统角色不可删除
- 系统角色不可重命名
- 系统角色核心权限不可移除

### 2. 权限验证
- API接口级权限检查
- 前端页面访问控制
- 操作按钮权限显示

### 3. 审计日志
- 所有写操作记录审计日志
- 包含操作者、目标、IP、User-Agent
- 详细的变更记录（diff）

### 4. 数据验证
- 权限代码有效性检查
- 角色名称唯一性验证
- 用户角色引用完整性

## 📊 API文档

### 权限管理

```http
GET /api/admin/permissions
Authorization: Cookie (access_token)
Permissions: permissions.read

Response:
[
  {
    "category": "users",
    "items": [
      {
        "id": 1,
        "code": "users.read",
        "description": "查看用户信息",
        "category": "users"
      }
    ]
  }
]
```

### 角色管理

```http
GET /api/admin/roles?q=admin&page=1&page_size=20
Authorization: Cookie (access_token)  
Permissions: roles.read

Response:
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 4,
  "total_pages": 1
}
```

```http
POST /api/admin/roles
Authorization: Cookie (access_token)
Permissions: roles.write

Request:
{
  "name": "custom_role",
  "description": "Custom role description", 
  "permission_codes": ["users.read", "tickets.read"]
}
```

### 用户信息扩展

```http
GET /api/auth/me
Authorization: Cookie (access_token)

Response:
{
  "id": 1,
  "email": "admin@meidasupport.com",
  "display_name": "系统管理员",
  "roles": ["admin"],
  "permissions": [...],  // 兼容字段
  "effective_permissions": ["users.read", "users.write", ...] // 新字段
}
```

## 🧪 测试

### 运行测试

```bash
# 运行RBAC v2测试
python -m pytest backend/tests/test_rbac_v2.py -v

# 运行所有测试
python -m pytest backend/tests/ -v
```

### 测试覆盖

- ✅ 权限API测试
- ✅ 角色CRUD测试  
- ✅ 系统角色保护测试
- ✅ 用户角色分配测试
- ✅ 权限依赖测试
- ✅ 完整生命周期测试

## 🔧 开发指南

### 添加新权限

1. 在 `backend/app/services/rbac_service.py` 中的 `PERMISSIONS` 字典添加新权限
2. 运行种子脚本更新数据库: `python backend/scripts/seed_rbac_v2.py`
3. 在需要的API接口添加权限依赖

### 创建权限依赖

```python
# 单个权限
require_new_permission = require_permission("new.permission")

# 多个权限（全部需要）
require_multiple_perms = require_perms("perm1", "perm2", mode="all")

# 多个权限（任一即可）
require_any_perms = require_perms("perm1", "perm2", mode="any")
```

### 前端权限检查

```javascript
// 检查用户权限
fetch('/api/auth/me', {credentials: 'include'})
  .then(response => response.json())
  .then(user => {
    if (user.effective_permissions.includes('roles.write')) {
      // 显示编辑按钮
    }
  });
```

## 📋 数据库迁移

### 创建迁移

```bash
# 自动生成迁移
alembic revision --autogenerate -m "description"

# 手动创建迁移
alembic revision -m "description"
```

### 应用迁移

```bash
# 应用所有迁移
alembic upgrade head

# 应用到特定版本
alembic upgrade revision_id
```

## 🚨 故障排除

### 常见问题

1. **权限依赖导入错误**
   ```python
   # 确保正确导入
   from backend.app.core.deps import require_roles_read
   ```

2. **系统角色修改失败**
   - 检查是否尝试修改系统角色名称
   - 确认系统角色核心权限未被移除

3. **权限聚合不正确**
   - 确认用户角色分配正确
   - 检查角色权限绑定

4. **前端权限检查失败**
   - 确认用户已登录
   - 检查 `/api/auth/me` 返回的 `effective_permissions`

### 日志调试

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 版本历史

### v2.0.0 (当前版本)
- ✅ 完整RBAC权限管理系统
- ✅ 权限分类和聚合计算
- ✅ 系统角色保护机制
- ✅ 前端管理界面
- ✅ 审计日志记录
- ✅ 完整的API文档和测试

### v1.0.0 (基础版本)
- 基础用户认证
- 简单角色权限
- Cookie-JWT认证

## 📞 支持

如有问题或建议，请联系开发团队或查看：
- API文档: http://127.0.0.1:8000/api/docs
- 系统日志: 检查控制台输出
- 测试结果: 运行测试套件 