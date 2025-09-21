# 客服项目·技术结构规划（Dify 版本 v1.1）

## 0. 目标与范围
- 目标：为美大客服项目提供**可扩展**、**可观测**、**可集成**的服务枢纽，支撑智能客服、工单、定位/上门、保修校验、**Dify 工作流**编排。
- 当前关键能力：
  1) 连接定位地图 API（用户定位/服务范围判定/就近网点）  
  2) **连接 Dify API**（触发工作流或对话：建单、分流、生成提示、知识检索）  
  3) 查询服务器**本地文档**以确认客户是否在保修期内（离线资料→结构化索引→查询）

---

## 1. 总体架构

```
[Web/前端(页面与客服UI)]
     │  HTTPS
     ▼
[FastAPI BFF 层]  ────▶  [Geo Service(地图适配层)]
     │                     ├─ AMapAdapter / MapboxAdapter / OSM+Nominatim
     │
     ├──────────────▶  [Dify Connector] ─▶ [Dify App(s): Workflow/Chatflow]
     │                                         ├─ Workflow: 工单创建/分诊/回访
     │                                         └─ Chatflow: 对话+知识检索
     │
     ├──────────────▶  [Warranty Service]
     │                    ├─ File Watcher(可选) + ETL
     │                    ├─ SQLite/PostgreSQL 索引
     │                    └─ 文档仓(本地目录/SMB/NAS)
     │
     ├──────────────▶  [AuthN/Z & Audit]
     │
     └──────────────▶  [Observability: Logs/Metrics/Tracing]
```

**部署建议**
- 前端静态：Cloudflare Pages；  
- 后端 FastAPI：VPS/K8s + Cloudflare Tunnel/Proxy；  
- **Dify**：自托管或 Dify Cloud；后端通过服务端密钥调用。  
- 存储：开发期 SQLite，生产 Postgres；Redis 作为缓存/异步队列（可选）。

---

## 2. 技术栈与约定

- **后端**：FastAPI + Uvicorn；Pydantic v2；SQLAlchemy；httpx；loguru。  
- **前端**：React/Next/Vite；地图用 Leaflet/Mapbox GL JS/AMap JS SDK。  
- **AI 编排**：Dify Workflow/Chatflow，通过 **服务端**代理访问：  
  - Workflow 执行：`POST /v1/workflows/run`，携带 `inputs`、`user`、`response_mode`（streaming | blocking）。
  - 对话应用：`POST /v1/chat-messages`，可维护 `conversation_id` 会话。
  - Dify 知识库（Dataset）可通过 API 维护文件/文本，便于后台同步。
- **工具调用**：在 Dify Workflow 中使用 **HTTP Request** 节点回调你的 BFF（如保修查询/服务范围校验）。
- **安全**：Dify App/API Key 仅保存在后端；前端绝不直曝密钥。
- **可观测**：结构化日志(JSON)、/healthz、/metrics；Dify 侧可查询 Run 详情与日志。

---

## 3. 配置与环境变量（.env 示例）

```env
# Map
MAP_PROVIDER=amap              # amap | mapbox | osm
AMAP_KEY=xxx
MAPBOX_TOKEN=xxx

# Dify (服务端保管)
DIFY_BASE_URL=https://your-dify-host-or-cloud
DIFY_API_KEY=sk-xxxx-workflow-or-app-key
DIFY_RESPONSE_MODE=blocking     # blocking | streaming（边缘代理建议≤100s）
DIFY_USER_PREFIX=web            # 拼接 user 标识 (e.g., web:{customer_id})

# Dify Dataset（如需后台同步知识库）
DIFY_DATASET_API_KEY=sk-xxxx    # 与应用服务API分离

# Warranty
WARRANTY_DATA_DIR=/data/warranty
WARRANTY_DB_URL=sqlite:///./data/warranty.db
WARRANTY_ALLOWED_EXT=.csv,.xlsx,.json

# Server
SECRET_KEY=change_me
DATABASE_URL=sqlite:///./data/app.db
```

> 说明：Workflow 的 **blocking** 模式受边缘代理超时影响，建议 100 秒内完成；长流程用 **streaming**（SSE）或异步回查运行状态/日志。

---

## 4. 关键域模型（ERD 摘要）

```
Customers(id, name, phone_hash, address_region, created_at)
Products(id, model_code, name, warranty_months_default)
WarrantyRecords(id, serial_number, model_code, purchase_date, warranty_months, invoice_id, customer_name_hash, expires_on, source_file, checksum)
ServiceCenters(id, name, lat, lng, service_polygon_geojson, city)
Tickets(id, customer_id, serial_number, issue_code, status, assigned_center_id, created_at, ai_run_id)  # 原 n8n_run_id → ai_run_id
```

> 隐私字段仅存**哈希**（如 phone_hash / customer_name_hash），原始值不落库。

---

## 5. API 设计（BFF/后端）

### 5.1 地图与服务范围
- `POST /api/geo/reverse-geocode`
  - body: `{ "lat": number, "lng": number }`
  - resp: `{ "address": "...", "city": "...", "district": "..." }`

- `GET /api/geo/in-service?lat=..&lng=..`
  - resp: `{ "in_service": bool, "center_id": str|null, "center_name": str|null, "distance_km": number }`

- `GET /api/geo/centers/nearest?lat=..&lng=..&limit=3`
  - resp: `[{ "id": "...", "name": "...", "lat": ..., "lng": ..., "distance_km": ... }]`

> 后端用 Shapely 进行点是否在多边形内判断；前端可用 turf.js 进行预校验。

### 5.2 Dify 执行网关（后端代理 Dify API）
- `POST /api/ai/workflow/run`
  - body:
    ```json
    {
      "flow": "create_ticket",
      "inputs": {
        "customer_phone": "****",
        "serial_number": "SN123",
        "issue_code": "E2",
        "geo": {"lat": 22.84, "lng": 108.37}
      },
      "user": "web:uid-123"                 
    }
    ```
  - resp（blocking 示例）：
    ```json
    { "ok": true, "workflow_run_id": "uuid", "task_id": "uuid", "data": { "status": "running", "outputs": {} } }
    ```
  - 说明：后端读取 `DIFY_API_KEY`，转发到 `{DIFY_BASE_URL}/v1/workflows/run`，透传 `inputs/user/response_mode`；保存 `workflow_run_id` → `Tickets.ai_run_id`。

- `GET /api/ai/workflow/runs/{id}`
  - resp：返回运行详情（后端代理 Dify 的运行详情/日志接口）。

- `POST /api/ai/chat`
  - body：
    ```json
    {
      "query": "预约上门支持",
      "inputs": {"city": "南宁"},
      "conversation_id": null,
      "user": "web:uid-123",
      "stream": false
    }
    ```
  - 行为：代理 `{DIFY_BASE_URL}/v1/chat-messages`；后端维护 `conversation_id`；前端如需流式则走 SSE。

### 5.3 保修查询
- `POST /api/warranty/query`
  - body（任一关键字段即可，优先级：serial_number > invoice_id > phone_hash）：  
    ```json
    { "serial_number": "SN123", "purchase_date": "2024-03-01" }
    ```
  - resp：  
    ```json
    {
      "found": true,
      "record": {
        "serial_number": "SN123",
        "model_code": "MD-001",
        "purchase_date": "2024-03-01",
        "warranty_months": 24,
        "expires_on": "2026-03-01",
        "source_file": "2024Q1_warranty.csv"
      },
      "in_warranty": true,
      "days_left": 533
    }
    ```

- `POST /api/warranty/reindex`（受限接口）
  - resp: `{ "ok": true, "files_indexed": 12, "records": 10234, "skipped": 3 }`

---

## 6. 适配层设计

### 6.1 MapProvider（Python后端抽象）
```python
from abc import ABC, abstractmethod
from typing import Dict, Tuple

class MapProvider(ABC):
    @abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> Dict: ...
    @abstractmethod
    async def geocode(self, address: str) -> Tuple[float, float]: ...
```
- **AMapAdapter**：使用高德逆/正地理编码；**MapboxAdapter**：Mapbox Geocoding；**OSMAdapter**：Nominatim（注意速率限制，需自建或缓存）。
- **服务范围判定**：后端加载 `service_zones/*.geojson`（各区/服务半径），用 Shapely `polygon.contains(point)` 做命中；最近网点基于 Haversine 距离排序。

### 6.2 Dify Connector
- `DifyClient.run_workflow(flow: str, inputs: dict, user: str, mode='blocking') -> RunMeta`
  - 读取 `DIFY_BASE_URL`/`DIFY_API_KEY`；自动填 `response_mode`；5s 超时，2 次重试；记录 `workflow_run_id` 与 `task_id`。
- `DifyClient.chat(query: str, inputs: dict, user: str, conversation_id: str|None, stream=False)`
  - 非流：直接返回；流：SSE 事件转发；支持多轮与 `conversation_id` 续聊。
- **工作流内工具调用**：在 Dify Workflow 中使用 **HTTP Request** 节点回调本项目 API（如 `/api/warranty/query`、`/api/geo/in-service`）。

### 6.3 Dataset 同步（可选）
- 后端管理页或定时任务使用 **Dataset API** 将 FAQ/政策文档同步到 Dify 知识库（新增/更新/删除/进度查询），与 RAG 检索结合。

---

## 7. 前端集成要点
- 定位与地图同前。  
- 触发工作流：表单提交后 `POST /api/ai/workflow/run`；需要进度时轮询 `/api/ai/workflow/runs/{id}` 或使用流式模式在后端转发 SSE。  
- 对话入口：/help 或工单创建引导页接入 `/api/ai/chat`，后端管理 `conversation_id` 与会话策略。

---

## 8. 安全、合规与审计
- **密钥管理**：Dify App/API Key、Dataset Key 仅存后端；分权最小化（服务 API 与 Dataset API 分离）。  
- **鉴权**：BFF 颁发短期 JWT；管理端接口要求角色 `admin`。  
- **数据最小化**：客户电话/姓名仅存哈希，日志脱敏。  
- **審計**：对 `/api/ai/*` 调用写 `AuditLog`，保存 `workflow_run_id`/`conversation_id`。

---

## 9. 可观测性与运维
- `/healthz` 检查 DB/地图/Dify 可用性；  
- `/metrics` 暴露：AI 调用时延、成功率、流式超时/中断率；  
- Dify 侧可通过运行详情/日志排查异常。

---

## 10. 测试策略
- **单测**：DifyClient 使用 httpx mock；Workflow/Chat 请求/响应契约校验；  
- **集成**：启动一条 Dify Workflow（发布为 API）→ 走 `/api/ai/workflow/run` 全链路；  
- **契约**：OpenAPI 校验与前端 contract 测试；  
- **数据回归**：保修索引重复导入/坏行/空值全覆盖。

---

## 11. OpenAPI 片段（AI 执行网关）

```yaml
paths:
  /api/ai/workflow/run:
    post:
      summary: Run Dify Workflow via server gateway
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [flow, inputs, user]
              properties:
                flow: { type: string }
                inputs: { type: object, additionalProperties: true }
                user: { type: string }
                stream: { type: boolean, default: false }
      responses:
        "200":
          description: blocking mode response
          content:
            application/json:
              schema:
                type: object
                properties:
                  ok: { type: boolean }
                  workflow_run_id: { type: string, format: uuid }
                  task_id: { type: string, format: uuid }
                  data: { type: object }
        "202":
          description: streaming accepted (SSE)
```

---

## 12. 实施清单（以 Dify 为核心）

### A. 连接定位地图 API（同前，2–3 天）
1) `MapProvider` 接口与 AMapAdapter；  
2) 导入 `service_zones/*.geojson` + Shapely；  
3) `/api/geo/*` 三接口 + 缓存。

### B. 接入 Dify API（2–4 天）
1) 后端实现 `DifyClient`（httpx）：`/v1/workflows/run`、`/v1/chat-messages`；支持 blocking 与 SSE 流式；  
2) 新增 BFF 路由：`/api/ai/workflow/run`、`/api/ai/chat`、`/api/ai/workflow/runs/{id}`；  
3) Dify 端搭建 **Workflow：create_ticket**（示例编排）  
   - 节点1：意图/分诊 → 节点2（需要上门？）  
   - 节点2：**HTTP Request** 调用 `/api/warranty/query`  
   - 节点3：**HTTP Request** 调用 `/api/geo/in-service`  
   - 节点4：生成结果（上门建议/到店建议/转人工）  
   - 输出：结构化 JSON（供前端渲染与建单入库）  
4) 审计/日志打点：记录 `workflow_run_id`、耗时、状态；  
5) （可选）长流程使用 `streaming` 并在前端显示逐步反馈。

### C. 本地文档保修期查询（3–5 天）
1) 规范 CSV/XLSX/JSON 字段；  
2) `Warranty ETL`：扫描→checksum→解析→UPSERT→`expires_on`；  
3) `/api/warranty/query` 与管理页 `/api/warranty/reindex`；  
4) （可选）将政策/FAQ 通过 **Dataset API** 同步到 Dify 知识库，用于对话检索引用。

---

## 13. 目录结构建议

```
backend/
  app/
    api/
      geo.py
      warranty.py
      ai_dify.py        # ← 新增：Dify 网关
    core/
      config.py
      security.py
      logging.py
    services/
      map/
        base.py
        amap.py
        mapbox.py
        osm.py
      warranty/
        etl.py
        query.py
      ai/
        dify_client.py  # ← 新增：Dify Client
    models/
      __init__.py
      warranty.py
      center.py
      ticket.py
    db/
      base.py
    main.py
  tests/
docs/
  architecture.md
  service_zones/*.geojson
frontend/
  ...
data/
  warranty/
  app.db
  warranty.db
```

---

## 14. 风险与缓解
- **阻塞时长限制**：blocking 模式建议 ≤100s；超过改用 streaming 或异步回查。  
- **密钥泄露**：只在后端调用 Dify；分离服务 API Key 与 Dataset API Key。  
- **知识库一致性**：采用 Dataset API 做增量同步与状态轮询，避免 UI 手工操作失配。  
- **外部依赖稳定性**：HTTP 节点失败时 Dify 工作流启用错误分支/重试；后端也做重试与降级。
