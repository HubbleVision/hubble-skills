# User Research Agent 创建流程交付文档

> **版本**: v1.0  
> **日期**: 2026-04-10  
> **目标读者**: 需要基于此流程开发相关 Skill 的开发人员

---

## 1. 架构概述

User Research Agent 采用 **双写代理架构**：

```
前端 → Market Server (FastAPI) → Research Creator Service (独立服务)
              ↓                           ↓
         Market DB (PostgreSQL)    CF Worker (Cloudflare)
```

- **Market Server**: 网关/代理层，负责用户鉴权、参数校验、本地 DB 双写
- **Research Creator**: 独立服务，负责代码生成、CF Worker 部署
- Market Server **不直接**调用交易所 API 或运行 Agent 逻辑

---

## 2. API 端点总览

基础路径: `POST /api/v1/agents/user-research`

| 方法 | 路径 | 说明 | 状态码 |
|------|------|------|--------|
| `POST` | `/` | 创建 Agent | 202 |
| `GET` | `/` | 列出当前用户的 Agent（分页） | 200 |
| `GET` | `/data-sources` | 获取可用数据源列表 | 200 |
| `GET` | `/jobs/{job_id}` | 查询部署任务状态 | 200 |
| `GET` | `/jobs/{job_id}/logs` | 流式获取部署日志 | 200 (SSE) |
| `GET` | `/{agent_id}` | 获取 Agent 详情 | 200 |
| `PUT` | `/{agent_id}` | 更新 Agent | 202/200 |
| `DELETE` | `/{agent_id}` | 删除 Agent | 204 |
| `GET` | `/{agent_id}/versions` | 版本历史列表 | 200 |
| `POST` | `/{agent_id}/versions` | 部署新版本 | 202 |
| `GET` | `/{agent_id}/versions/{version}` | 版本详情 | 200 |
| `POST` | `/{agent_id}/versions/{version}/rollback` | 回滚到指定版本 | 202 |

**认证方式**: 所有端点需要 JWT Token 或 API Key，通过 `get_current_user` 依赖注入当前用户。

---

## 3. 创建 Agent — 完整流程

### 3.1 请求参数 (UserResearchCreateRequest)

```json
POST /api/v1/agents/user-research
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "name": "BTC 技术分析 Agent",           // 必填, 1-160 字符
  "description": "每日 BTC 技术分析报告",   // 可选
  "prompt": "分析 BTC 的日线趋势...",       // 必填, 研究提示词
  "datasource_ids": ["000000000001", "000000000003"],  // 必填, 至少 1 个, 12 字符十六进制
  "datasource_config_version": "v1",       // 可选, 数据源配置版本
  "data_sources": null,                    // 可选, 旧版数据源配置 (legacy)
  "llm_provider_id": "gemini_vertex",      // 必填, 见 §3.2
  "llm_model": "gemini-3-flash-preview",   // 必填, 见 §3.2
  "asset_type": "crypto",                  // 必填, 动态验证
  "analysis_type": "technical_analysis",   // 必填, 由 Creator 验证
  "is_public": false                       // 可选, 是否公开到市场
}
```

**兼容性**: 前端可传 `llm_provider` 代替 `llm_provider_id`，后端自动映射。

### 3.2 LLM Provider 可选值

当前支持的 provider 和 model 组合（硬编码在 `src/app/schemas/agent.py`）：

| llm_provider_id | llm_model | 说明 |
|-----------------|-----------|------|
| `gemini_vertex` | `gemini-3-flash-preview` | Google Gemini |
| `minimax` | `MiniMax-M2.7` | MiniMax |

校验逻辑：provider 和 model 必须匹配，不可跨 provider 选 model。

### 3.3 asset_type 验证

- 从 Creator 服务动态获取有效值（`GET /api/v1/config/asset-types`）
- 本地缓存 TTL: 5 分钟
- Creator 不可达时放行（fail-open），由 Creator 做最终校验

### 3.4 创建响应 (UserResearchCreateResponse)

```json
HTTP 202 Accepted

{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",  // UUID, 与 Creator 一致
  "job_id": "abc123def456",                              // Creator 部署任务 ID
  "status": "pending"                                    // 初始状态
}
```

### 3.5 创建流程时序图

```
Client                Market Server              Creator Service
  |                        |                           |
  |-- POST /user-research->|                           |
  |                        |-- validate asset_type     |
  |                        |-- validate llm provider   |
  |                        |                           |
  |                        |-- POST /api/v1/agents --->|
  |                        |   {name, prompt, user_id, |
  |                        |    datasource_ids,         |
  |                        |    llm_config, asset_type, |
  |                        |    analysis_type,          |
  |                        |    skip_codegen: true}     |
  |                        |                           |
  |                        |<-- 201/202 {agent_id,  ---|
  |                        |            job_id}        |
  |                        |                           |
  |                        |-- Agent.create() to DB    |
  |                        |   (deploy_status=PENDING) |
  |                        |                           |
  |                        |-- assign_icon() (非阻塞)  |
  |                        |                           |
  |<-- 202 {agent_id, ----|                           |
  |        job_id, status} |                           |
```

### 3.6 转发给 Creator 的请求体

Market Server 组装后发给 Creator 的实际 body：

```json
{
  "name": "BTC 技术分析 Agent",
  "prompt": "分析 BTC 的日线趋势...",
  "user_id": "user-uuid-from-jwt",        // 从 JWT 注入
  "datasource_ids": ["000000000001"],
  "skip_codegen": true,                    // 固定为 true
  "datasource_config_version": "v1",       // 可选
  "description": "每日 BTC 技术分析报告",   // 可选
  "data_sources": null,                    // 可选 legacy
  "llm_config": {                          // 嵌套格式
    "provider": "gemini_vertex",
    "model": "gemini-3-flash-preview"
  },
  "asset_type": "crypto",
  "analysis_type": "technical_analysis"
}
```

注意：Creator 使用嵌套 `llm_config` 对象，Market Server 接收扁平字段后转换。

### 3.7 Market DB 写入字段

创建成功后写入 `agents` 表：

| 字段 | 值 | 说明 |
|------|-----|------|
| `id` | Creator 返回的 agent_id | 与 Creator 保持一致 |
| `owner_id` | JWT 中的 user_id | 所有权 |
| `owner_wallet` | 从 UserAuthProvider 提取 | 钱包地址 |
| `name` | 请求中的 name | |
| `agent_type` | `USER_RESEARCH` | 固定 |
| `hosting_type` | `INTERNAL` | 固定 |
| `pricing_model` | `FREE` | 固定 |
| `deploy_status` | `PENDING` | 初始状态 |
| `is_public` | 请求中的值 | 默认 false |
| `type_metadata` | 见下方 | JSON 字段 |

**type_metadata 结构**:

```json
{
  "schema_version": "2.0",
  "prompt": "...",
  "datasource_ids": ["000000000001"],
  "job_id": "current-job-id",
  "job_ids": ["job-id-1"],           // 历史 job_id 列表，用于所有权查找
  "skip_codegen": true,
  "asset_type": "crypto",
  "analysis_type": "technical_analysis",
  "llm_provider_id": "gemini_vertex",
  "llm_model": "gemini-3-flash-preview",
  "data_sources": null,              // legacy, 可选
  "creator_agent_name": "..."        // Creator 返回的 agent_name, 可选
}
```

---

## 4. 部署状态查询

创建后前端通过 **轮询** `job_id` 获取部署进度。

### 4.1 DeployStatus 枚举

| 值 | 含义 |
|----|------|
| `pending` | 已提交，等待 Creator 处理 |
| `deploying` | Creator 正在生成代码/部署 CF Worker |
| `deployed` | 部署成功，endpoint_url 可用 |
| `failed` | 部署失败 |

### 4.2 轮询部署状态

```
GET /api/v1/agents/user-research/jobs/{job_id}
Authorization: Bearer <jwt_token>
```

**响应示例（进行中）**:
```json
{
  "status": "deploying",
  "job_id": "abc123def456"
}
```

**响应示例（成功）**:
```json
{
  "status": "completed",
  "endpoint_url": "https://agent-xxx.workers.dev",
  "version": 1,
  "datasource_call_array": [
    {"id": "000000000001", "name": "glassnode", "params": {...}}
  ],
  "worker_template_version": "v2.0.1",
  "llm_provider": "gemini_vertex",
  "llm_model": "gemini-3-flash-preview"
}
```

**响应示例（失败）**:
```json
{
  "status": "failed",
  "error": "Worker deployment timeout"
}
```

### 4.3 Lazy Update 机制

当 `GET /jobs/{job_id}` 检测到终态（completed/deployed/failed）时，**自动更新** Market DB：

- `deployed` → `deploy_status = DEPLOYED`，写入 `type_metadata.url`、`datasource_call_array`、`worker_template_version`、`llm_provider_id`、`llm_model`
- `failed` → `deploy_status = FAILED`，写入 `type_metadata.last_error`

### 4.4 后台同步任务

除了前端轮询触发的 lazy update，还有 Celery Beat 后台定时同步：

- **任务名**: `sync_user_research_deploy_status`
- **频率**: 每 30 秒（可配置 `RESEARCH_CREATOR_SYNC_INTERVAL`）
- **范围**: 扫描所有 `deploy_status` 为 `PENDING` 或 `DEPLOYING` 的 Agent
- **锁**: Redis 分布式锁，防止多 Worker 并发执行
- **锁超时**: 300 秒
- **Phase 1**: 逐个查询 Creator，更新终态
- **Phase 2**: 孤儿检测（Creator 有但 Market DB 缺失的 Agent）

### 4.5 部署日志流

```
GET /api/v1/agents/user-research/jobs/{job_id}/logs
Authorization: Bearer <jwt_token>
```

返回 `StreamingResponse`，代理 Creator 的日志流。

---

## 5. 获取数据源列表

创建前需获取可用数据源，供用户选择 `datasource_ids`。

```
GET /api/v1/agents/user-research/data-sources
Authorization: Bearer <jwt_token>
```

代理请求到 Creator `GET /api/v1/data-sources`，返回 YAML/Redis 中的外部平台 API 数据源（如 Glassnode、CoinGlass 等）。

---

## 6. 更新 Agent

```
PUT /api/v1/agents/user-research/{agent_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### 6.1 更新请求参数 (UserResearchUpdateRequest)

```json
{
  "name": "新名称",                        // 可选
  "description": "新描述",                  // 可选
  "prompt": "新的研究提示词",               // 可选, 触发重新部署
  "datasource_ids": ["000000000002"],       // 可选, 触发重新部署
  "datasource_config_version": "v2",       // 可选
  "data_sources": null,                    // 可选 legacy, 触发重新部署
  "llm_provider_id": "minimax",           // 可选, 触发重新部署
  "llm_model": "MiniMax-M2.7",            // 可选, 触发重新部署
  "is_public": true,                       // 可选, 不触发重新部署
  "allow_public_test": true                // 可选, 不触发重新部署
}
```

### 6.2 是否触发重新部署

| 字段变更 | 是否触发重新部署 |
|----------|:---:|
| `name` | 否 |
| `description` | 否 |
| `is_public` | 否 |
| `allow_public_test` | 否 |
| `prompt` | **是** |
| `datasource_ids` | **是** |
| `data_sources` | **是** |
| `llm_provider_id` | **是** |
| `llm_model` | **是** |

- 不触发部署 → 返回 `200 {"needs_deploy": false}`，仅更新本地 DB
- 触发部署 → 转发 Creator `PUT /api/v1/agents/{agent_id}` → 返回 `202 {"needs_deploy": true, "job_id": "..."}`
- 重新部署时 `deploy_status` 回到 `PENDING`，需要重新轮询 job_id

---

## 7. 列表查询

```
GET /api/v1/agents/user-research?page=1&page_size=20&asset_type=crypto&analysis_type=technical_analysis
Authorization: Bearer <jwt_token>
```

### 7.1 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码，≥1 |
| `page_size` | int | 20 | 每页条数，1-100 |
| `asset_type` | string | null | 按资产类型过滤 |
| `analysis_type` | string | null | 按分析类型过滤 |

### 7.2 响应格式

```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "550e8400-...",
      "name": "BTC 技术分析 Agent",
      "description": "...",
      "deploy_status": "deployed",
      "is_public": false,
      "type_metadata": {
        "schema_version": "2.0",
        "prompt": "...",
        "url": "https://agent-xxx.workers.dev",
        "llm_provider_id": "gemini_vertex",
        "llm_model": "gemini-3-flash-preview",
        "asset_type": "crypto",
        "analysis_type": "technical_analysis",
        "datasource_ids": ["000000000001"]
      },
      "created_at": "2026-04-10T08:00:00+00:00"
    }
  ]
}
```

---

## 8. 删除 Agent

```
DELETE /api/v1/agents/user-research/{agent_id}
Authorization: Bearer <jwt_token>
```

- 先调用 Creator `DELETE /api/v1/agents/{agent_id}`
- Creator 返回 2xx 或 404/410（已删除）→ 本地软删除 `is_deleted = True`
- Creator 返回其他 4xx → 抛异常，不执行本地删除
- 同时释放分配的系统图标

---

## 9. 版本管理

### 9.1 部署新版本

```
POST /api/v1/agents/user-research/{agent_id}/versions
Authorization: Bearer <jwt_token>

{
  "prompt": "更新后的研究提示词",       // 可选
  "data_sources": [...],               // 可选
  "llm_provider_id": "minimax",        // 可选
  "llm_model": "MiniMax-M2.7"          // 可选
}
```

- 返回 `202` + 新 `job_id`
- `deploy_status` 回到 `PENDING`
- 新 job_id 追加到 `type_metadata.job_ids` 历史

### 9.2 查看版本列表

```
GET /api/v1/agents/user-research/{agent_id}/versions?page=1&page_size=20
```

### 9.3 回滚

```
POST /api/v1/agents/user-research/{agent_id}/versions/{version}/rollback
```

- Creator 内部创建新版本（使用旧版本配置）
- Market DB 同步恢复 prompt、datasource_ids、llm_provider_id、llm_model
- `deploy_status` 回到 `PENDING`

---

## 10. 错误码映射

| 场景 | HTTP 状态码 | 说明 |
|------|:---:|------|
| 请求参数校验失败 | 400 | asset_type 无效、llm provider/model 不匹配 |
| 非 Agent 所有者 | 403 | permission denied |
| Agent 不存在 | 404 | |
| Creator 鉴权失败 | 502 | Market → Creator 的 `X-Hubble-Auth-Key` 错误 |
| Creator 服务错误 | 502 | Creator 5xx 或连接失败 |
| Creator 未配置 | 503 | `RESEARCH_CREATOR_BASE_URL` 未设置 |
| Creator 请求超时 | 504 | 默认 30 秒 |

---

## 11. 关键配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `RESEARCH_CREATOR_BASE_URL` | — | Creator 服务地址 |
| `RESEARCH_CREATOR_AUTH_KEY` | — | Creator 鉴权密钥，降级用 `HUBBLE_AUTH_KEY` |
| `RESEARCH_CREATOR_SYNC_INTERVAL` | 30 | 后台同步间隔（秒） |
| `RESEARCH_CREATOR_REQUEST_TIMEOUT` | 30 | HTTP 请求超时（秒） |

---

## 12. 关键源码位置

| 文件 | 说明 |
|------|------|
| `src/app/api/user_research.py` | API 路由，完整的 CRUD + 版本管理 |
| `src/app/schemas/user_research.py` | 请求/响应 Schema 定义 |
| `src/app/schemas/agent.py:484-492` | LLM Provider 常量（`LLM_PROVIDER_DEFAULT_MODELS`、`LLM_PROVIDER_ALLOWED_MODELS`） |
| `src/app/services/research_creator_client.py` | Creator HTTP 客户端，统一鉴权/错误处理 |
| `src/app/services/asset_type_cache.py` | asset_type 缓存校验 |
| `src/app/tasks/research_sync.py` | Celery 后台同步任务 |
| `src/app/services/user_research_cleanup.py` | 删除逻辑（Creator + 本地双删） |
| `src/app/models/enums.py:111-117` | `DeployStatus` 枚举定义 |
| `src/app/models/agent.py` | Agent 数据库模型 |

---

## 13. 典型前端集成流程

```
1. GET  /data-sources                          → 获取可用数据源
2. POST /user-research                         → 创建 Agent，拿到 agent_id + job_id
3. GET  /jobs/{job_id}  (轮询, 间隔 2-5 秒)     → 等待 status 变为 deployed/failed
4. GET  /user-research/{agent_id}              → 获取完整 Agent 详情
5. PUT  /user-research/{agent_id}              → 更新配置（可能触发重新部署）
   └─ 如果 needs_deploy=true → 回到步骤 3 轮询新 job_id
```
