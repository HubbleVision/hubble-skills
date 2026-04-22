---
name: hubble_agents
description: Use when the user asks to list, view, create, update, or delete agents (PM agents, User Research agents, or generic agents) on the Hubble Market API.
---

# Hubble Agents Skill

Version: v0.5.0

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

Read from environment:

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY` — must start with `hb_sk_`

## Safety rules

- **Never print `HUBBLE_API_KEY`**.
- Validate `agent_id` format before use: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
- For all write actions (`POST`/`PUT`/`PATCH`/`DELETE`), summarize the action and wait for explicit user confirmation.

## Setup

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
# Validate agent_id
[[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] && echo "Invalid agent_id" && exit 2
```

---

## PM Agent Routes

PM agents are trading agents managed by Cloudflare Worker. Primary agent type for users.

### List PM agents

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/pm"
```

Optional query params: `limit`, `offset`, `search`.

Summarize: `id`, `name`, `created_at`, `agent_type`, status fields if present.

---

### Create PM agent — requires confirmation

Required fields: `name`, `exchange` (e.g. `weex`/`aster`/`mock`), `exchange_auth_type` (e.g. `api_key`/`web3`), `exchange_keys` (dict).

Optional: `description`, `symbols`, `risk_limit` (0-1), `interval_ms`, `auto_start_scheduler`, `llm_provider_id`, `llm_model`, `system_prompt`, `risk_config`, `research_agent_ids`.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm" \
  -d "$BODY"
```

Errors: `409` = symbol conflict on same exchange (report conflicting agents); `502` = CF Worker upstream error.

---

### Update PM agent — requires confirmation

Not updatable: `exchange`, `exchange_auth_type`, `exchange_keys`.

Updatable: `name`, `description`, `symbols`, `risk_limit`, `interval_ms`, `system_prompt`, `risk_config`, `llm_provider_id`, `llm_model`, `research_agent_ids`.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/pm/$AGENT_ID" \
  -d "$BODY"
```

---

## Generic Agent Routes

### Get agent

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/$AGENT_ID"
```

Note: public agents do not require authentication; unpublished agents require ownership.

---

### Update agent (generic) — requires confirmation

```bash
# Full update
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/$AGENT_ID" \
  -d "$BODY"

# Partial update
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PATCH \
  "$BASE/api/v1/agents/$AGENT_ID" \
  -d "$BODY"
```

---

### Delete agent — requires confirmation

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -X DELETE \
  "$BASE/api/v1/agents/$AGENT_ID"
```

---

## User Research Agent Routes

User Research Agents 是部署在 Cloudflare 上的自定义研究 Worker，由 Creator 服务负责构建和部署。
API 前缀：`/api/v1/agents/user-research`。

> **已废弃**：`POST /agents/research` 和 `PUT /agents/research/{id}` 已标记为 Deprecated，禁止使用。

### LLM 供应商与模型

| `llm_provider_id` | `llm_model` | 说明 |
|---|---|---|
| `gemini_vertex` | `gemini-3-flash-preview` | Google Gemini，适合通用分析场景 |
| `minimax` | `MiniMax-M2.7` | MiniMax，适合中文内容场景 |

`llm_provider_id` 与 `llm_model` 必须配对使用，不可混用。

---

### Create User Research Agent — requires confirmation

**创建是异步的**：请求成功返回 `202`，同时返回 `agent_id` 和 `job_id`。Agent 并未立刻可用，需轮询 job 状态直到 `completed`/`deployed`（见"查询部署进度"）。

#### 参数说明

| 参数 | 必填 | 类型 | 说明 | 示例 |
|---|---|---|---|---|
| `name` | ✅ | string | Agent 的显示名称，最长 160 字符 | `"BTC 技术分析 Agent"` |
| `prompt` | ✅ | string | 核心分析指令，描述 Agent 要分析什么、关注哪些指标、输出什么结论。写得越具体，分析质量越高 | `"分析 BTC 的 RSI、MACD 和布林带，判断当前趋势方向，给出做多/做空建议及主要理由"` |
| `asset_type` | ✅ | string | 分析的资产类别 | `"Crypto"`（加密货币）/ `"A-shares"`（A股）/ `"HK stocks"`（港股）/ `"US stocks"`（美股） |
| `analysis_type` | ✅ | string | 分析类型，影响 Agent 的分析框架 | `"Technical Analysis"`（技术分析）/ `"Fundamental Research"`（基本面）/ `"Capital Flow Analysis"`（资金流向）/ `"Macro Analysis"`（宏观） |
| `datasource_ids` | ✅ | string[] | 选用的数据源 ID 列表（12 位 hex 字符串）。先调 `GET /api/v1/agents/user-research/data-sources` 查看平台支持的数据源 | `["a1b2c3d4e5f6", "0a1b2c3d4e5f"]` |
| `llm_provider_id` | ✅ | string | LLM 供应商，见上方表格 | `"gemini_vertex"` |
| `llm_model` | ✅ | string | LLM 模型，必须与 `llm_provider_id` 配对 | `"gemini-3-flash-preview"` |
| `description` | ❌ | string | Agent 的简短说明，展示给用户看 | `"每小时分析一次 BTC 技术面"` |
| `is_public` | ❌ | boolean | 是否公开到市场，默认 `false` | `false` |
| `datasource_config_version` | ❌ | string | 数据源配置版本，留空则使用最新版 | `"v1"` |

#### 自适应创建流程

根据用户提供的信息量决定行为：

- **用户已提供全部必填字段** → 直接展示请求体摘要，确认后执行。
- **其他情况** → 先问：
  > "要从模板快速创建，还是手动配置所有参数？"
  - **模板** → 进入模板创建路径（见下方）
  - **手动** → 进入引导模式（每次只问一个）

**引导模式提问顺序（每次只问一个）**：

1. 这个 Research Agent 叫什么名字？
2. 描述它要做什么分析——这将成为 Agent 的核心指令（prompt）。写得越具体越好，比如关注哪些指标、输出什么结论。
3. 分析哪类资产？`Crypto`（加密货币）/ `A-shares`（A股）/ `HK stocks`（港股）/ `US stocks`（美股）/ 其他（请说明，值需与 Creator 配置一致）
4. 分析类型是？`Technical Analysis`（技术分析）/ `Fundamental Research`（基本面研究）/ `Capital Flow Analysis`（资金流向）/ `Macro Analysis`（宏观分析）/ 其他（请说明，值需与 Creator 配置一致）
5. 先调 `GET /api/v1/agents/user-research/data-sources` 列出可用数据源，展示给用户选择
6. 使用哪个 LLM？`gemini_vertex`（gemini-3-flash-preview，通用）/ `minimax`（MiniMax-M2.7，中文场景）
7. 是否公开到市场？（可选，默认 `false`，直接回车跳过）

收集完毕后，展示完整 JSON body，等用户确认后再执行。

**模板创建路径（5 步）**：

1. 调用 `GET /api/v1/config/indicator-templates`，按 `asset_type` 分组展示模板列表（序号、名称、分析类型），等用户输入序号选择。
2. 询问：这个 Agent 叫什么名字？
3. 询问：使用哪个 LLM？`gemini_vertex`（gemini-3-flash-preview，通用）/ `minimax`（MiniMax-M2.7，中文场景）
4. 展示模板 prompt 前两行预览，询问："要直接使用模板指令，还是在模板基础上补充说明？"
   - 直接使用 → prompt 不变
   - 补充说明 → 将用户输入追加到模板 prompt 末尾（不覆盖原始指令）
5. 展示完整 JSON body，等用户确认后执行创建请求。

从模板提取的字段：`datasource_ids` ← `selected_indicator_ids`，`prompt`、`asset_type`（如 `"Crypto"`）、`analysis_type`（如 `"Technical Analysis"`）直接使用，无需转换格式。

#### 完整示例请求体

```json
{
  "name": "BTC 技术分析 Agent",
  "description": "每小时分析一次 BTC 技术面，给出趋势判断",
  "prompt": "分析 BTC 的 RSI、MACD 和布林带，判断当前趋势方向，给出做多/做空建议及主要理由",
  "asset_type": "Crypto",
  "analysis_type": "Technical Analysis",
  "datasource_ids": ["a1b2c3d4e5f6", "0a1b2c3d4e5f"],
  "llm_provider_id": "gemini_vertex",
  "llm_model": "gemini-3-flash-preview",
  "is_public": false
}
```

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/user-research" \
  -d "$BODY"
```

成功响应（202）：

```json
{ "agent_id": "<uuid>", "job_id": "<string>", "status": "pending" }
```

**创建成功后，必须轮询部署状态**（见下方"查询部署进度"）确认 Agent 真正可用。

---

### 查询部署进度

创建或更新触发重新部署后，用 `job_id` 轮询，直到出现终态。建议每 5–10 秒轮询一次。

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research/jobs/$JOB_ID"
```

| 状态值 | 含义 |
|---|---|
| `pending` | 等待处理 |
| `deploying` | 正在构建/部署 |
| `completed` / `deployed` | ✅ 部署成功，Agent 可用 |
| `failed` | ❌ 部署失败，查看响应中的 `error` 字段 |

---

### 查看部署日志（流式）

```bash
curl -sS \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research/jobs/$JOB_ID/logs"
```

---

### 查询可用数据源

创建 Agent 前调用，列出平台支持的所有数据源，供用户选择 `datasource_ids`。

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research/data-sources"
```

每条记录包含 `id`（填入请求体）、`name`（展示名）和 `params`（配置参数）。

---

### 查询 Indicator 模板

获取预设分析模板，每条模板已内置 `selected_indicator_ids`（对应创建请求的 `datasource_ids`）和专业 `prompt`，可直接用于创建 User Research Agent。

```bash
curl -sS --fail-with-body \
  "$BASE/api/v1/config/indicator-templates"
```

无需认证。每条模板字段：

| 字段 | 说明 |
|---|---|
| `name` | 模板显示名称 |
| `asset_type` | 资产类型（如 `"Crypto"`、`"A-shares"`、`"HK stocks"`、`"US stocks"`） |
| `analysis_type` | 分析类型（如 `"Technical Analysis"`、`"Fundamental Research"`） |
| `selected_indicator_ids` | 12 位 hex ID 列表，直接用作 `datasource_ids` |
| `prompt` | 完整分析指令，可直接使用 |

---

### 列出 User Research Agents

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research?page=1&page_size=20"
```

| 查询参数 | 含义 | 示例 |
|---|---|---|
| `page` | 页码，从 1 开始 | `1` |
| `page_size` | 每页条数，最大 100 | `20` |
| `asset_type` | 按资产类型筛选 | `"Crypto"` |
| `analysis_type` | 按分析类型筛选 | `"Technical Analysis"` |

---

### 查看 User Research Agent 详情

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research/$AGENT_ID"
```

---

### Update User Research Agent — requires confirmation

所有字段均为可选，只传需要修改的字段。

**是否触发重新部署**（区别很重要）：

| 字段 | 是否触发重新部署 | 说明 |
|---|---|---|
| `prompt` | ✅ 是 | 核心指令变更需重新构建 |
| `datasource_ids` | ✅ 是 | 数据源变更需重新构建 |
| `data_sources` | ✅ 是 | 同上（旧格式） |
| `llm_provider_id` | ✅ 是 | 切换 LLM 供应商需重新构建 |
| `llm_model` | ✅ 是 | 切换模型需重新构建 |
| `name` | ❌ 否 | 仅更新显示名称 |
| `description` | ❌ 否 | 仅更新描述 |
| `is_public` | ❌ 否 | 仅更新公开状态 |
| `allow_public_test` | ❌ 否 | 仅更新是否允许公开测试 |

触发重新部署时返回 `202` + 新 `job_id`，需重新轮询部署状态；否则返回 `200`。

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/user-research/$AGENT_ID" \
  -d "$BODY"
```

---

### Delete User Research Agent — requires confirmation

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -X DELETE \
  "$BASE/api/v1/agents/user-research/$AGENT_ID"
```

---

### 版本管理

#### 列出版本历史

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research/$AGENT_ID/versions?page=1&page_size=20"
```

#### 查看某版本详情

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/user-research/$AGENT_ID/versions/$VERSION"
```

#### 部署新版本 — requires confirmation

只传需要变更的字段：

| 参数 | 说明 | 示例 |
|---|---|---|
| `prompt` | 新的分析指令 | `"重点关注 MACD 金叉死叉信号"` |
| `data_sources` | 新的数据源配置（旧格式） | `[...]` |
| `llm_provider_id` | 更换 LLM 供应商 | `"minimax"` |
| `llm_model` | 更换模型（需与新供应商配对） | `"MiniMax-M2.7"` |

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/user-research/$AGENT_ID/versions" \
  -d "$BODY"
```

返回新 `job_id`，需轮询部署状态。

#### 回滚到历史版本 — requires confirmation

将 Agent 回滚到指定版本（该版本必须曾经成功部署）。回滚会创建一个新版本，而非覆盖现有版本。

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -X POST \
  "$BASE/api/v1/agents/user-research/$AGENT_ID/versions/$VERSION/rollback"
```

返回 `400` 表示目标版本未曾成功部署，无法回滚。返回新 `job_id`，需轮询部署状态。

---

## Error reference

| Code | Meaning |
|------|---------|
| `401` | API key missing/invalid/expired. Ask user to rotate key. |
| `403` | Not owner or no permission. |
| `404` | Agent not found. Verify `agent_id`. |
| `409` | Symbol conflict for PM agents. Report conflicting agents/symbols. |
| `502` | (User Research) Creator auth failure (`X-Hubble-Auth-Key` wrong) or Creator returned 5xx/connection error. |
| `503` | (User Research) `RESEARCH_CREATOR_BASE_URL` not configured on server. |
| `504` | (User Research) Creator request timed out (default 30s). |
| `5xx` | Server error. Retry once; if still failing, report body. |
