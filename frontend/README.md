# 美大客服支持中心 - 静态网站部署说明

这是美大客服支持中心的静态网站版本，已经过优化，可以直接部署到 Cloudflare Pages。

## 📁 目录结构

```
site/
├── index.html              # 首页
├── booking.html            # 预约页面
├── _headers                # Cloudflare Pages 头部配置
├── _redirects              # Cloudflare Pages 重定向配置
├── admin/
│   └── login.html          # 管理员登录页面
├── issues/                 # 问题页面
│   ├── integrated-stove/   # 集成灶问题
│   ├── disinfection-cabinet/ # 消毒柜问题
│   ├── range-hood/         # 油烟机问题
│   ├── gas-stove/          # 燃气灶问题
│   └── water-heater/       # 热水器问题
├── solution/               # 解决方案页面
│   └── [产品]/[问题代码]/  # 具体解决方案
└── static/                 # 静态资源
    ├── styles.css          # 样式文件
    └── app.js              # JavaScript 文件
```

## 🚀 部署到 Cloudflare Pages

### 方法一：通过 Git 连接（推荐）

1. 将 `site/` 目录内容推送到 Git 仓库
2. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
3. 进入 Pages 页面，点击 "创建项目"
4. 选择 "连接到 Git"
5. 选择您的仓库
6. 配置构建设置：
   - **构建命令**: 留空（已经是静态文件）
   - **构建输出目录**: `/`
   - **根目录**: `/site` （如果整个仓库不只是静态文件）

### 方法二：直接上传

1. 将 `site/` 目录内容打包为 ZIP 文件
2. 登录 Cloudflare Dashboard
3. 进入 Pages，点击 "上传资产"
4. 上传 ZIP 文件

## ⚙️ 配置说明

### _headers 文件
设置了安全头部和缓存策略：
- 安全头部：防止 XSS、点击劫持等攻击
- 静态资源缓存：1年缓存期

### _redirects 文件
配置了重定向规则：
- `/admin/*` → 重定向到登录页面
- `/api/*` → 代理到后端 API（需要配置实际后端地址）

## 🔧 自定义配置

### 更新后端 API 地址

编辑 `_redirects` 文件，将 `https://your-backend-api.com` 替换为实际的后端 API 地址：

```
/api/* https://your-actual-backend.com/api/:splat 200
```

### 自定义域名

1. 在 Cloudflare Pages 项目设置中添加自定义域名
2. 配置 DNS 记录指向 Cloudflare Pages

### 环境变量（如需要）

在 Cloudflare Pages 项目设置中可以添加环境变量，用于不同环境的配置。

## 🎨 样式和功能

- **响应式设计**: 支持桌面和移动设备
- **搜索功能**: 产品和问题搜索
- **现代 UI**: 使用 Tailwind CSS 框架
- **中文支持**: 完整的中文界面

## 📱 页面功能

### 首页 (`/`)
- 产品选择界面
- 搜索功能
- 产品分类展示

### 问题页面 (`/issues/[产品]`)
- 显示特定产品的常见问题
- 问题搜索功能
- 故障代码显示

### 解决方案页面 (`/solution/[产品]/[问题代码]`)
- 详细的解决步骤
- 安全提示
- 联系客服选项

### 预约页面 (`/booking.html`)
- 服务预约表单
- 联系信息收集

### 管理员页面 (`/admin/login.html`)
- 管理员登录界面
- 现代化设计

## 🔍 SEO 优化

- 语义化 HTML 结构
- Meta 标签优化
- 面包屑导航
- 合适的标题层级

## 🚨 注意事项

1. **API 集成**: 当前为静态版本，需要配置后端 API 地址来实现动态功能
2. **数据更新**: 产品和问题数据当前是硬编码的，实际使用时需要连接数据库
3. **表单提交**: 预约表单需要配置后端处理逻辑
4. **认证**: 管理员登录需要后端认证支持

## 📞 支持

如需技术支持或有任何问题，请联系开发团队。 