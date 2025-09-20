# 美大客服支持中心

一个极简、Apple 风格的客服支持网站，使用 Python(FastAPI) + Jinja2 + TailwindCSS(CDN) + 原生JS 实现。

## 功能特点

- 两步式支持流程：①选择产品 ②选择问题
- 移动端优先，自适应布局
- Apple 风格设计：大余白、对齐网格、圆角卡片
- 搜索功能：支持产品名称和拼音首字母搜索
- 键盘可访问性与 ARIA 标签
- 面包屑导航

## 技术栈

- 后端：Python FastAPI
- 模板引擎：Jinja2
- 前端样式：TailwindCSS (CDN)
- 交互：原生 JavaScript

## 安装与运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动服务器：

```bash
uvicorn main:app --reload
```

3. 访问网站：

```
http://127.0.0.1:8000/
```

## Cloudflare Pages部署

本项目已配置为可在Cloudflare Pages上部署。按照以下步骤操作：

### 1. 准备工作

确保你已经：
- 注册了Cloudflare账号
- 拥有一个GitHub账号
- 将项目代码推送到GitHub仓库

### 2. 连接GitHub仓库

1. 登录[Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 在左侧导航栏中选择"Pages"
3. 点击"创建应用程序"按钮
4. 选择"连接到Git"
5. 授权Cloudflare访问你的GitHub账号
6. 选择包含本项目的仓库

### 3. 配置构建设置

在构建设置页面，配置以下选项：

- **项目名称**：输入你想要的项目名称（例如：meida-support）
- **生产分支**：选择你的主分支（通常是`main`或`master`）
- **构建命令**：`pip install -r requirements.txt`
- **构建输出目录**：`.`（点号，表示项目根目录）
- **环境变量**：
  - 点击"环境变量"部分
  - 添加变量 `PYTHON_VERSION` 值为 `3.9`

### 4. 高级设置

在"高级设置"部分：

- **Python版本**：确保设置为3.9
- **包管理器缓存**：可以启用以加快后续部署

### 5. 部署

1. 点击"保存并部署"按钮
2. Cloudflare Pages将开始构建和部署你的应用
3. 构建完成后，你将看到"部署成功"的消息
4. 点击提供的URL（通常是`https://你的项目名称.pages.dev`）访问你的网站

### 6. 自定义域名（可选）

如果你想使用自己的域名：

1. 在项目详情页面，点击"自定义域"
2. 点击"设置自定义域"
3. 输入你想要使用的域名
4. 按照提示完成DNS配置

### 7. 持续部署

设置完成后，每当你推送更改到GitHub仓库的主分支时，Cloudflare Pages将自动重新构建和部署你的应用。

### 8. 使用部署脚本（可选）

本项目提供了一个便捷的部署脚本，可以快速部署到Cloudflare Pages：

1. 确保脚本有执行权限：
```bash
chmod +x deploy.sh
```

2. 运行部署脚本：
```bash
./deploy.sh
```

脚本会自动安装依赖并部署到Cloudflare Pages。首次运行时，可能需要登录Cloudflare账户。

### 故障排除

如果部署失败，请检查：

1. `requirements.txt` 文件是否包含所有必要的依赖
2. 构建日志中是否有错误信息
3. 确保项目结构符合预期（静态文件在`static`目录，模板在`templates`目录）
4. 检查`_redirects`文件是否正确配置

## 项目结构

```
美大客服独立站/
├── main.py              # FastAPI 路由、模板渲染、内置数据
├── functions/           # Cloudflare Pages函数
│   └── api.py           # API处理函数
├── requirements.txt     # 项目依赖
├── templates/           # HTML模板
│   ├── base.html        # 通用布局：导航/面包屑/容器/页脚
│   ├── index.html       # 产品选择页
│   ├── issues.html      # 问题选择页
│   └── solution.html    # 解决方案页
└── static/              # 静态资源
    ├── app.js           # 前端交互
    └── styles.css       # 补充样式
```

## 数据结构

项目目前使用内置数据，后续可扩展为数据库或 JSON 文件：

- 产品数据：名称、图标、标识符
- 问题数据：按产品分组的问题列表，包含标题和故障码 
