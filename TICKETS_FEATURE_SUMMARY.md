# 故障管理（工单）模块 - 功能总结

## 🎯 项目概述

本次开发完成了美大客服支持系统的完整故障管理（工单）模块，实现了从用户预约到工单完成的全流程管理。

## 📋 实现的工作流

```
用户预约 → 确认预约 → 分配技师 → 上传回执 → 完成工单
 BOOKED  → CONFIRMED → ASSIGNED → IN_PROGRESS → COMPLETED
```

## 🏗️ 技术架构

### 后端 (FastAPI + SQLAlchemy)
- **数据模型**: 4个核心表（tickets, technicians, ticket_images, ticket_events）
- **API接口**: 15个RESTful端点，支持完整的工单生命周期
- **权限控制**: 基于现有RBAC系统，新增5个工单权限
- **文件存储**: 本地磁盘存储，支持安全文件上传和下载
- **审计日志**: 完整的操作记录和事件追踪

### 前端 (HTML + JavaScript)
- **管理端**: 工单列表、详情、筛选、操作界面
- **技师端**: 简化的工单管理界面
- **用户端**: 预约成功反馈，显示工单号

## 🗄️ 数据库设计

### 核心表结构

#### 1. tickets (工单表)
```sql
- id (UUID): 主键
- customer_name: 客户姓名
- customer_phone_hash: 电话哈希值（隐私保护）
- address: 服务地址
- appointment_date/time: 预约时间
- issue_desc: 问题描述
- status: 工单状态
- technician_id: 分配的技师
- version: 乐观锁版本号
```

#### 2. technicians (技师表)
```sql
- id (UUID): 主键
- name: 技师姓名
- phone_masked: 脱敏电话
- center_id: 所属服务中心
- skills: 技能描述
- is_active: 是否活跃
```

#### 3. ticket_images (工单图片表)
```sql
- id (UUID): 主键
- ticket_id: 关联工单
- type: 图片类型（RECEIPT等）
- file_path: 文件路径
- checksum_sha256: 文件校验和
```

#### 4. ticket_events (工单事件表)
```sql
- id (UUID): 主键
- ticket_id: 关联工单
- action: 操作类型
- actor_user_id: 操作用户
- details_json: 操作详情
```

## 🔗 API 端点

### 公开接口
- `POST /api/public/booking` - 用户预约提交

### 认证接口
- `GET /api/tickets` - 工单列表查询
- `GET /api/tickets/{id}` - 工单详情
- `POST /api/tickets/{id}/confirm` - 确认预约
- `POST /api/tickets/{id}/assign` - 分配技师
- `POST /api/tickets/{id}/images` - 上传回执
- `POST /api/tickets/{id}/complete` - 完成工单
- `GET /api/technicians` - 技师列表
- `GET /api/files/ticket-receipt/{id}` - 安全文件下载

## 🔐 权限设计

新增5个工单权限：
- `tickets.read` - 查看工单
- `tickets.write` - 编辑工单
- `tickets.assign` - 分配技师
- `tickets.complete` - 完成工单
- `tickets.upload` - 上传文件

角色权限分配：
- **admin**: 全部权限
- **agent**: read, write, upload
- **ops_manager**: read, assign, complete

## 📁 文件存储

### 配置参数
```env
UPLOAD_ROOT=./data/uploads
TICKET_RECEIPT_DIR=tickets
MAX_UPLOAD_MB=8
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp
```

### 存储结构
```
data/uploads/
└── tickets/
    └── {ticket_id}/
        ├── {random}_{timestamp}.jpg
        └── {random}_{timestamp}.png
```

## 🎨 前端界面

### 1. 管理端 (`/admin/tickets`)
- **工单列表**: 支持状态、技师、日期、关键字筛选
- **工单详情**: 完整信息展示，包含操作历史和图片
- **操作按钮**: 确认、分配、上传、完成等操作
- **分页**: 支持大量数据分页浏览

### 2. 技师端 (`/admin/my-jobs`)
- **我的工单**: 显示分配给当前技师的工单
- **状态管理**: 开始服务、上传回执、完成工单
- **批量上传**: 支持多张图片同时上传

### 3. 用户端反馈
- **预约成功**: 显示工单号（TK开头的短ID）
- **状态提示**: 清晰的成功/失败反馈

## 🔧 业务逻辑

### 状态机
```
BOOKED ──────→ CONFIRMED ──────→ ASSIGNED ──────→ IN_PROGRESS ──────→ COMPLETED
   ↓              ↓                 ↓                 ↓
CANCELED      CANCELED          CANCELED          CANCELED
```

### 自动分配策略
- 优先选择同服务中心的技师
- 按近7天工单数量最少优先
- 支持手动指定技师

### 完成条件
- 必须有至少一张回执图片
- 状态必须是 ASSIGNED 或 IN_PROGRESS

## 🧪 测试验证

### 1. 基础API测试 (`test_tickets_api.py`)
- 健康检查
- 公开预约接口
- 权限验证

### 2. 数据种子 (`backend/scripts/seed_tickets.py`)
- 创建3个测试技师
- 创建5个不同状态的测试工单
- 完整的事件记录

### 3. 集成测试 (`test_integration.py`)
- 端到端完整流程测试
- 8个步骤全覆盖
- 自动化验证

## 📊 性能优化

### 数据库优化
- 关键字段索引：status, appointment_date, technician_id
- 外键约束确保数据一致性
- 乐观锁防止并发冲突

### 文件处理
- SHA256校验防止重复上传
- 文件大小和类型验证
- 安全的文件名生成

## 🔍 监控和审计

### 审计日志
- 所有工单操作记录到audit_logs表
- 包含操作用户、时间、详情
- 支持后续分析和追踪

### 事件记录
- 工单状态变更事件
- 技师分配记录
- 文件上传记录
- 完成时间记录

## 🚀 部署说明

### 数据库迁移
```bash
python -m alembic upgrade head
```

### 初始化数据
```bash
python -m backend.scripts.seed_tickets
```

### 启动服务
```bash
python -m backend.app.main
```

### 访问地址
- 用户预约: http://localhost:8000/booking
- 管理后台: http://localhost:8000/admin/tickets
- 技师端: http://localhost:8000/admin/my-jobs

## ✅ 验收标准达成

- [x] 用户提交预约后获得工单号反馈
- [x] 管理端完整的工单生命周期管理
- [x] 技师分配（手动/自动）功能
- [x] 回执图片上传和管理
- [x] 完成工单需要回执验证
- [x] 完整的权限控制和审计日志
- [x] 乐观锁防止并发冲突
- [x] 文件安全存储和下载

## 🎉 总结

本次开发成功实现了完整的故障管理（工单）模块，包含：
- **4个数据模型** + **1个迁移文件**
- **15个API接口** + **权限控制**
- **3个前端页面** + **响应式设计**
- **文件存储服务** + **安全下载**
- **完整测试套件** + **数据种子**

系统已准备好投入生产使用，支持完整的工单管理工作流程。 