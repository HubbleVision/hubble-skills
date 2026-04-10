---
name: hubble_agents
description: Manage agents (PM agents, User Research agents, and generic agents) on Hubble Market Server using an API key.
---

# Hubble Agents Skill

Version: v0.3.0

## When to use

Use this skill when the user asks about:

- Listing PM agents
- Viewing an agent's details
- Creating a PM agent
- Updating a PM agent
- Deleting an agent
- Creating / updating / deleting User Research Agents
- Checking deploy job status for User Research Agents
- Managing User Research Agent versions

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Treat `agent_id` as untrusted input. Validate it before calling the API.
- For write actions (`POST`/`PUT`/`PATCH`/`DELETE`), repeat the action summary and wait for explicit user confirmation before calling the API.
- Do not accept arbitrary JSON from the user. Ask for the minimal fields required by the endpoint.
- Validation rules:
  - `agent_id` must be UUID-like: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`

## Tools

Use the `bash` tool to call the API.

---

## PM Agent Routes

PM agents are trading agents managed by CF Worker. These are the primary agent type for users.

### Action: List PM agents

Call:

- `GET /api/v1/agents/pm`

Summarize key fields: `id`, `name`, `created_at`, `agent_type`, status fields if present.

Supports optional query params: `limit`, `offset`, `search`.

### Action: Create PM agent

Call:

- `POST /api/v1/agents/pm`

Before calling:

- Ask for required fields: `name`, `exchange` (e.g. `weex`/`aster`/`mock`), `exchange_auth_type` (e.g. `api_key`/`web3`), `exchange_keys` (dict with API credentials).
- Optional fields: `description`, `symbols` (list of trading symbols), `risk_limit` (0-1), `interval_ms`, `auto_start_scheduler`, `llm_provider_id`, `llm_model`, `system_prompt`, `risk_config`, `research_agent_ids`.
- Show a brief summary of the request body and ask for confirmation.

Error codes:
- `409`: Symbol conflict with an existing PM agent on the same exchange.
- `502`: CF Worker upstream error.

### Action: Update PM agent

Call:

- `PUT /api/v1/agents/pm/{agent_id}`

Before calling:

- Validate `agent_id` format.
- Note: `exchange`, `exchange_auth_type`, and `exchange_keys` are **not updatable**.
- Updatable fields: `name`, `description`, `symbols`, `risk_limit`, `interval_ms`, `system_prompt`, `risk_config`, `llm_provider_id`, `llm_model`, `research_agent_ids`.
- Summarize intended changes and ask for confirmation.

---

## Generic Agent Routes

### Action: Get agent

Call:

- `GET /api/v1/agents/{agent_id}`

Before calling:

- Validate `agent_id` format.

Note: Public agents do not require authentication. Unpublished agents require ownership.

### Action: Update agent (generic)

Call:

- `PUT /api/v1/agents/{agent_id}` (full update)
- `PATCH /api/v1/agents/{agent_id}` (partial update)

Before calling:

- Validate `agent_id` format.
- Summarize intended changes and ask for confirmation.

### Action: Delete agent

Call:

- `DELETE /api/v1/agents/{agent_id}`

Before calling:

- Validate `agent_id` format.
- Ask for confirmation.

---

## User Research Agent Routes

User Research Agents 是部署在 Cloudflare 上的自定义研究 Worker。创建和更新均为**异步操作**，完成后需轮询 job 状态确认部署结果。

API 前缀：`/api/v1/agents/user-research`

> **已废弃**：`POST /agents/research` 和 `PUT /agents/research/{id}` 禁止使用，一律改用上方路径。

### LLM 供应商与模型

`llm_provider_id` 与 `llm_model` 必须配对，不可混用：

| `llm_provider_id` | `llm_model` | 说明 |
|---|---|---|
| `gemini_vertex` | `gemini-3-flash-preview` | Google Gemini，适合通用分析场景 |
| `minimax` | `MiniMax-M2.7` | MiniMax，适合中文内容场景 |

---

### Action: Create User Research Agent

Call:

- `POST /api/v1/agents/user-research`

**创建是异步的**：成功后返回 `202` + `agent_id` + `job_id`，Agent 并未立刻可用。必须用 job_id 轮询状态（见"Action: 查询部署进度"）直到 `completed`/`deployed`。

#### 参数说明

| 参数 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `name` | ✅ | Agent 的显示名称，最长 160 字符 | `"BTC 技术分析 Agent"` |
| `prompt` | ✅ | 核心分析指令。描述 Agent 要分析什么、关注哪些指标、输出什么结论。越具体越好 | `"分析 BTC 的 RSI、MACD 和布林带，判断趋势，给出做多/做空建议"` |
| `asset_type` | ✅ | 分析的资产类别 | `"crypto"`（加密货币）/ `"forex"`（外汇） |
| `analysis_type` | ✅ | 分析类型，影响分析框架 | `"technical_analysis"` / `"on_chain"` / `"sentiment"` |
| `datasource_ids` | ✅ | 数据源 ID 列表（12 位 hex 字符串），至少一个。先调 `GET /api/v1/agents/user-research/data-sources` 查询可选列表 | `["a1b2c3d4e5f6"]` |
| `llm_provider_id` | ✅ | LLM 供应商，见上方表格 | `"gemini_vertex"` |
| `llm_model` | ✅ | LLM 模型，须与 `llm_provider_id` 配对 | `"gemini-3-flash-preview"` |
| `description` | ❌ | Agent 的简短说明，展示给用户看 | `"每小时分析一次 BTC 技术面"` |
| `is_public` | ❌ | 是否公开到市场，默认 `false` | `false` |
| `datasource_config_version` | ❌ | 数据源配置版本，留空使用最新版 | `"v1"` |

#### 自适应收集参数

根据用户提供的信息量决定行为：

- 用户已提供全部必填字段 → 直接展示请求体摘要，确认后执行。
- 用户提供了部分字段 → 只追问缺失的必填项。
- 用户未提供任何字段 → 先询问：
  > "要我一步步引导你填写，还是你直接告诉我所有参数？"

**引导模式提问顺序（每次只问一个）**：

1. 这个 Research Agent 叫什么名字？
2. 描述它要做什么分析（将成为 Agent 的核心指令）。越具体越好，比如关注哪些指标、输出什么结论。
3. 分析哪类资产？`crypto`（加密货币）/ `forex`（外汇）/ 其他（请说明）
4. 分析类型？`technical_analysis`（技术分析）/ `on_chain`（链上数据）/ `sentiment`（情绪分析）/ 其他（请说明）
5. 调 `GET /api/v1/agents/user-research/data-sources` 列出可用数据源，展示给用户选择
6. 使用哪个 LLM？`gemini_vertex`（gemini-3-flash-preview）/ `minimax`（MiniMax-M2.7）
7. 是否公开到市场？（可选，默认 `false`，可跳过）

全部收集完毕后，展示完整 JSON body，等用户确认后再执行。

#### 示例请求体

```json
{
  "name": "BTC 技术分析 Agent",
  "description": "每小时分析一次 BTC 技术面，给出趋势判断",
  "prompt": "分析 BTC 的 RSI、MACD 和布林带，判断当前趋势方向，给出做多/做空建议及主要理由",
  "asset_type": "crypto",
  "analysis_type": "technical_analysis",
  "datasource_ids": ["a1b2c3d4e5f6", "0a1b2c3d4e5f"],
  "llm_provider_id": "gemini_vertex",
  "llm_model": "gemini-3-flash-preview",
  "is_public": false
}
```

成功响应（202）：

```json
{ "agent_id": "<uuid>", "job_id": "<string>", "status": "pending" }
```

创建成功后，立即引导用户轮询部署状态（见下方）。

---

### Action: 查询部署进度

Call:

- `GET /api/v1/agents/user-research/jobs/{job_id}`

创建或触发重新部署后，用 `job_id` 轮询状态，直到出现终态。建议每 5–10 秒轮询一次。

| 状态值 | 含义 |
|---|---|
| `pending` | 等待处理 |
| `running` | 正在构建/部署 |
| `completed` / `deployed` | ✅ 部署成功，Agent 可用 |
| `failed` | ❌ 部署失败，查看响应中的 `error` 字段 |

---

### Action: 查看部署日志（流式）

Call:

- `GET /api/v1/agents/user-research/jobs/{job_id}/logs`

输出为流式日志，可实时查看构建过程。

---

### Action: 查询可用数据源

Call:

- `GET /api/v1/agents/user-research/data-sources`

在创建 Agent 前调用，列出平台支持的所有数据源，供用户选择 `datasource_ids`。每条记录包含 `id`（填入请求体）、`name`（展示名）和 `params`（配置参数）。

---

### Action: List User Research Agents

Call:

- `GET /api/v1/agents/user-research`

支持查询参数：

| 参数 | 说明 | 示例 |
|---|---|---|
| `page` | 页码，从 1 开始 | `1` |
| `page_size` | 每页条数，最大 100 | `20` |
| `asset_type` | 按资产类型筛选 | `crypto` |
| `analysis_type` | 按分析类型筛选 | `technical_analysis` |

展示字段：`id`、`name`、`description`、`deploy_status`、`is_public`、`created_at`。

---

### Action: Get User Research Agent detail

Call:

- `GET /api/v1/agents/user-research/{agent_id}`

Before calling:

- Validate `agent_id` format.

---

### Action: Update User Research Agent

Call:

- `PUT /api/v1/agents/user-research/{agent_id}`

Before calling:

- Validate `agent_id` format.
- 询问用户要修改哪些字段。

所有字段均为可选，只传需要修改的字段。**是否触发重新部署**取决于修改的字段：

| 字段 | 是否触发重新部署 | 说明 |
|---|---|---|
| `prompt` | ✅ 是 | 核心指令变更需重新构建 |
| `datasource_ids` | ✅ 是 | 数据源变更需重新构建 |
| `data_sources` | ✅ 是 | 同上（旧格式） |
| `llm_provider_id` | ✅ 是 | 切换供应商需重新构建 |
| `llm_model` | ✅ 是 | 切换模型需重新构建 |
| `name` | ❌ 否 | 仅更新显示名称 |
| `description` | ❌ 否 | 仅更新描述 |
| `is_public` | ❌ 否 | 仅更新公开状态 |
| `allow_public_test` | ❌ 否 | 是否允许他人公开测试 |

触发重新部署时返回 `202` + 新 `job_id`，需重新轮询部署状态；否则返回 `200`。

- 确认修改内容后执行。

---

### Action: Delete User Research Agent

Call:

- `DELETE /api/v1/agents/user-research/{agent_id}`

Before calling:

- Validate `agent_id` format.
- 明确告知用户删除后不可恢复，等待确认。

---

### Action: 列出版本历史

Call:

- `GET /api/v1/agents/user-research/{agent_id}/versions`

Before calling:

- Validate `agent_id` format.

支持 `page`、`page_size` 查询参数。

---

### Action: 查看某版本详情

Call:

- `GET /api/v1/agents/user-research/{agent_id}/versions/{version}`

Before calling:

- Validate `agent_id` format.

---

### Action: 部署新版本

Call:

- `POST /api/v1/agents/user-research/{agent_id}/versions`

Before calling:

- Validate `agent_id` format.
- 询问要更新的内容（只传需要变更的字段）：

| 参数 | 说明 | 示例 |
|---|---|---|
| `prompt` | 新的分析指令 | `"重点关注 MACD 金叉死叉信号"` |
| `data_sources` | 新的数据源配置 | `[...]` |
| `llm_provider_id` | 更换 LLM 供应商 | `"minimax"` |
| `llm_model` | 更换模型（须与新供应商配对） | `"MiniMax-M2.7"` |

- 展示请求体摘要，确认后执行。

返回新 `job_id`，引导用户轮询部署状态。

---

### Action: 回滚到历史版本

Call:

- `POST /api/v1/agents/user-research/{agent_id}/versions/{version}/rollback`

Before calling:

- Validate `agent_id` format.
- 明确告知用户：回滚会以目标版本的配置创建一个新版本（不会覆盖现有版本），然后部署。
- 目标版本必须曾经成功部署，否则返回 `400`。
- 等待确认后执行。

返回新 `job_id`，引导用户轮询部署状态。

---

## Error handling (summary)

- `401`: API key missing/invalid/expired/disabled. Ask user to rotate key.
- `403`: Authenticated but not allowed (not owner / permission). Ask user to check agent ownership.
- `404`: Agent not found. Ask user to verify `agent_id`.
- `409`: Conflict (symbol conflict for PM agents). Report the conflicting agents and symbols.
- `5xx`: Server error. Retry once with backoff; if still failing, stop and report response body.

## Curl templates (copy-paste)

Normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Validate agent_id:

- `if [[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then echo "Invalid agent_id"; exit 2; fi`

List PM agents:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/pm"`

Get agent:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/$AGENT_ID"`

Create PM agent:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json" -X POST "$BASE/api/v1/agents/pm" -d "$BODY"`

Update PM agent:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json" -X PUT "$BASE/api/v1/agents/pm/$AGENT_ID" -d "$BODY"`

Update generic agent (PATCH):

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json" -X PATCH "$BASE/api/v1/agents/$AGENT_ID" -d "$BODY"`

Delete:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -X DELETE "$BASE/api/v1/agents/$AGENT_ID"`

List data sources:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/user-research/data-sources"`

Create User Research Agent:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json" -X POST "$BASE/api/v1/agents/user-research" -d "$BODY"`

Get deploy job status:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/user-research/jobs/$JOB_ID"`

List User Research Agents:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/user-research?page=1&page_size=20"`

Get User Research Agent detail:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/user-research/$AGENT_ID"`

Update User Research Agent:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json" -X PUT "$BASE/api/v1/agents/user-research/$AGENT_ID" -d "$BODY"`

Delete User Research Agent:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -X DELETE "$BASE/api/v1/agents/user-research/$AGENT_ID"`

List versions:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/agents/user-research/$AGENT_ID/versions"`

Deploy new version:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json" -X POST "$BASE/api/v1/agents/user-research/$AGENT_ID/versions" -d "$BODY"`

Rollback:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" -X POST "$BASE/api/v1/agents/user-research/$AGENT_ID/versions/$VERSION/rollback"`
