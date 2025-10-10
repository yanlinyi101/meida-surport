# 美大客服支持中心 - 前端部署说明

这是美大客服支持中心的前端部分，包含静态页面和模板文件，支持独立部署或与后端集成使用。

## 📋 项目概述

本项目采用现代化的客服支持系统架构，提供：
- 🎨 **Apple 风格设计** - 简洁优雅的用户界面
- 📱 **响应式布局** - 完美适配移动端和桌面端
- 🔍 **智能搜索** - 支持产品名称和拼音首字母搜索
- 📝 **在线预约** - 完整的服务预约功能
- 👨‍💼 **管理后台** - 功能完善的管理系统
- ♿ **无障碍访问** - 支持键盘操作和 ARIA 标签

## 📁 目录结构

```
frontend/
├── index.html                    # 首页 - 产品选择
├── booking.html                  # 预约页面
├── _headers                      # Cloudflare Pages 安全头部配置
├── _redirects                    # Cloudflare Pages 重定向规则
├── wrangler.toml                 # Cloudflare Pages 部署配置
├── package.json                  # 项目配置和脚本
├── admin/
│   └── login.html                # 管理员登录页面
├── issues/                       # 产品问题列表页面
│   ├── integrated-stove/         # 集成灶问题
│   ├── disinfection-cabinet/     # 消毒柜问题
│   ├── range-hood/               # 油烟机问题
│   ├── gas-stove/                # 燃气灶问题
│   └── water-heater/             # 热水器问题
├── solution/                     # 解决方案详情页面
│   ├── integrated-stove/         # 集成灶解决方案 (E01, E02, E03, other)
│   ├── disinfection-cabinet/     # 消毒柜解决方案 (D01, D02, D03, other)
│   ├── range-hood/               # 油烟机解决方案 (H01, H02, H03, other)
│   ├── gas-stove/                # 燃气灶解决方案 (G01, G02, G03, other)
│   └── water-heater/             # 热水器解决方案 (W01, W02, W03, other)
├── templates/                    # Jinja2 模板文件（用于后端渲染）
│   ├── base.html                 # 基础模板
│   ├── index.html                # 首页模板
│   ├── issues.html               # 问题列表模板
│   ├── solution.html             # 解决方案模板
│   ├── booking.html              # 预约表单模板
│   ├── admin_login.html          # 管理员登录模板
│   ├── admin_home.html           # 管理员首页模板
│   ├── admin_tickets.html        # 工单管理模板
│   ├── admin_roles.html          # 角色管理模板
│   ├── admin_permissions.html    # 权限管理模板
│   ├── user_home.html            # 用户中心模板
│   └── technician_jobs.html      # 技师工单模板
└── static/                       # 静态资源
    ├── styles.css                # 自定义样式
    └── app.js                    # 前端交互脚本
```

## 🚀 部署方式

### 方式一：Cloudflare Pages 部署（推荐）

#### 使用 Git 连接部署

1. **连接 Git 仓库**
   ```bash
   # 推送代码到 GitHub/GitLab
   git add .
   git commit -m "Update frontend"
   git push origin main
   ```

2. **配置 Cloudflare Pages**
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - 进入 **Pages** → 点击 **"创建应用程序"**
   - 选择 **"连接到 Git"**
   - 选择您的仓库

3. **构建设置**
   - **项目名称**: `meidasupport-frontend`
   - **生产分支**: `main`
   - **构建命令**: 留空（静态文件无需构建）
   - **构建输出目录**: `frontend`
   - **根目录**: `/frontend`

4. **环境变量**（可选）
   ```
   ENVIRONMENT=production
   ```

#### 使用 Wrangler CLI 部署

```bash
# 安装 Wrangler CLI
npm install -g wrangler

# 登录 Cloudflare
wrangler login

# 部署项目
cd frontend
wrangler pages publish . --project-name=meidasupport-frontend
```

### 方式二：静态文件服务器部署

#### 使用 Python HTTP Server（开发环境）

```bash
cd frontend
python -m http.server 8080
# 访问 http://localhost:8080
```

#### 使用 Node.js Live Server（开发环境）

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

#### 使用 Nginx（生产环境）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/meidasupport/frontend;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # 静态资源缓存
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 安全头部
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}
```

### 方式三：与后端集成部署

将前端文件放置在后端项目中，通过 FastAPI 提供服务：

```bash
# 启动后端服务（会自动提供前端页面）
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 访问 http://localhost:8000
```

## ⚙️ 配置说明

### 1. _headers 文件

配置了安全响应头和缓存策略：

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/static/*
  Cache-Control: public, max-age=31536000
```

### 2. _redirects 文件

配置了路由重定向规则：

```
# 管理员页面重定向
/admin/* /admin/login.html 200

# API 代理（需要配置实际后端地址）
/api/* https://your-backend-api.com/api/:splat 200
```

**重要**: 部署时请修改后端 API 地址为实际地址。

### 3. wrangler.toml 配置

Cloudflare Pages 部署配置文件：

```toml
name = "meidasupport-frontend"
compatibility_date = "2023-08-01"

[env.production]
account_id = "your-account-id"  # 需要替换为实际的 Cloudflare Account ID

[env.production.vars]
ENVIRONMENT = "production"
```

## 🎨 技术栈

- **HTML5** - 语义化标记
- **CSS3** - 现代样式（Flexbox, Grid）
- **TailwindCSS** - 实用优先的 CSS 框架（CDN 引入）
- **JavaScript (ES6+)** - 原生 JavaScript，无框架依赖
- **Jinja2 模板** - 用于后端渲染（可选）

## 📱 页面功能说明

### 用户端页面

| 页面 | 路径 | 功能描述 |
|------|------|----------|
| 首页 | `/` 或 `/index.html` | 产品选择、搜索功能、产品分类展示 |
| 问题列表 | `/issues/[产品]/` | 显示特定产品的常见问题、故障代码 |
| 解决方案 | `/solution/[产品]/[代码]/` | 详细的故障排除步骤、安全提示 |
| 预约服务 | `/booking.html` | 在线预约表单、服务信息收集 |

### 管理端页面

| 页面 | 路径 | 功能描述 |
|------|------|----------|
| 管理员登录 | `/admin/login.html` | 管理员身份验证 |
| 管理后台 | 需要后端支持 | 工单管理、数据统计、权限管理 |

## 🔧 后端 API 集成

### 配置后端地址

**方法一：修改 `_redirects` 文件**

```
/api/* https://api.yourdomain.com/api/:splat 200
```

**方法二：修改 `static/app.js` 中的 API 地址**

```javascript
const API_BASE_URL = 'https://api.yourdomain.com';
```

### API 接口

前端需要以下后端接口支持：

- `POST /api/auth/login` - 用户登录
- `POST /api/public/booking` - 提交预约
- `GET /api/admin/appointments/stats` - 预约统计
- `GET /api/admin/appointments/download` - 下载预约数据

详细的 API 文档请参考后端项目的 [APPOINTMENTS_FEATURE_README.md](../docs/APPOINTMENTS_FEATURE_README.md)。

## 🎯 功能特性

### 搜索功能
- ✅ 产品名称搜索
- ✅ 拼音首字母搜索
- ✅ 实时搜索结果
- ✅ 模糊匹配

### 预约功能
- ✅ 完整的表单验证
- ✅ 日期时间选择
- ✅ 实时提交反馈
- ✅ 预约编号生成

### 管理功能
- ✅ 角色权限管理
- ✅ 工单管理系统
- ✅ 数据统计和导出
- ✅ 预约记录查看

### 用户体验
- ✅ 响应式设计（移动端优先）
- ✅ 面包屑导航
- ✅ 键盘可访问性
- ✅ ARIA 无障碍支持
- ✅ 加载状态提示

## 🔍 SEO 优化

- ✅ 语义化 HTML5 标签
- ✅ Meta 标签优化（描述、关键词）
- ✅ Open Graph 标签（社交分享）
- ✅ 结构化数据标记
- ✅ 面包屑导航
- ✅ 合理的标题层级（H1-H6）
- ✅ 图片 Alt 属性
- ✅ 友好的 URL 结构

## 📊 浏览器兼容性

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ 移动端浏览器（iOS Safari, Chrome Mobile）

## 🚨 注意事项

### 部署前检查清单

- [ ] 修改 `_redirects` 文件中的后端 API 地址
- [ ] 修改 `wrangler.toml` 中的 `account_id`
- [ ] 检查所有静态资源路径是否正确
- [ ] 确认后端 API 已部署并可访问
- [ ] 配置 CORS 允许前端域名访问

### 安全建议

1. **HTTPS**: 生产环境必须使用 HTTPS
2. **API 密钥**: 不要在前端代码中暴露敏感密钥
3. **输入验证**: 前后端都需要进行数据验证
4. **CSP**: 考虑添加内容安全策略（Content Security Policy）

### 性能优化

1. **静态资源缓存**: 已通过 `_headers` 配置
2. **图片优化**: 使用适当的图片格式和尺寸
3. **代码压缩**: 生产环境建议压缩 CSS 和 JS
4. **CDN**: Cloudflare Pages 自动提供 CDN 加速

## 🛠️ 开发指南

### 本地开发

```bash
# 克隆项目
git clone https://github.com/yourusername/meidasupport.git
cd meidasupport/frontend

# 启动开发服务器
npm run dev

# 或使用 Python
python -m http.server 8080
```

### 修改样式

编辑 `static/styles.css` 文件，或在 HTML 中使用 Tailwind CSS 类。

### 修改脚本

编辑 `static/app.js` 文件，添加或修改前端交互逻辑。

### 添加新页面

1. 在相应目录下创建 HTML 文件
2. 引入必要的 CSS 和 JS 文件
3. 遵循现有页面的结构和样式
4. 更新导航链接

## 🔗 相关文档

- [后端 API 文档](../docs/APPOINTMENTS_FEATURE_README.md)
- [认证系统文档](../docs/AUTH_SYSTEM_README.md)
- [项目架构文档](../docs/architecture_dify_v1.1.md)
- [主项目 README](../README.md)

## 📞 技术支持

如需技术支持或有任何问题，请：

1. 查看项目 [Issues](https://github.com/yourusername/meidasupport/issues)
2. 提交新的 Issue
3. 联系开发团队

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

**最后更新**: 2025-10-10  
**版本**: 1.0.0 