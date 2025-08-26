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

1. 在GitHub上创建仓库并上传代码
2. 登录Cloudflare Dashboard，进入Pages
3. 创建新项目，连接到GitHub仓库
4. 配置构建设置：
   - 构建命令：`pip install -r requirements.txt`
   - 构建输出目录：`.`
   - 环境变量：`PYTHON_VERSION=3.9`
5. 部署项目

部署完成后，您可以通过Cloudflare分配的域名访问应用。

## 项目结构

```
美大客服独立站/
├── main.py              # FastAPI 路由、模板渲染、内置数据
├── wsgi.py              # WSGI入口点（用于Cloudflare部署）
├── requirements.txt     # 项目依赖
├── functions/           # Cloudflare Pages函数
│   └── api.py           # API处理函数
├── templates/
│   ├── base.html        # 通用布局：导航/面包屑/容器/页脚
│   ├── index.html       # 产品选择页
│   └── issues.html      # 问题选择页
└── static/
    ├── app.js           # 前端交互
    └── styles.css       # 补充样式
```

## 数据结构

项目目前使用内置数据，后续可扩展为数据库或 JSON 文件：

- 产品数据：名称、图标、标识符
- 问题数据：按产品分组的问题列表，包含标题和故障码 