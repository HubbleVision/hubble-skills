# Research Agent 模板创建支持设计文档

**日期**: 2026-04-22  
**版本**: v1.0  
**目标**: 为 `hubble_agents` skill 的 User Research Agent 创建流程增加模板支持，让用户无需手动选择 indicator，直接从预设模板快速创建。

---

## 1. 背景

当前创建 User Research Agent 时，用户必须：
1. 手动编写 `prompt`（描述分析指令）
2. 从数据源列表中逐一选择 `datasource_ids`

这两步门槛较高，尤其是选指标环节需要用户了解各 indicator 的用途。

Market Server 已提供两个相关端点：
- `GET /api/v1/config/indicator-templates` — 返回预设模板，每条已内置 `selected_indicator_ids` 和专业 `prompt`
- `GET /api/v1/research/config` — 代理 Creator 的完整 indicator 数据源列表（模板流程**不需要**调用此端点）

---

## 2. 目标

- 新增模板创建路径，用户最少只需回答 3 个问题（选模板、填名字、选 LLM）即可完成创建
- 现有手动配置流程**完全不变**
- Skills 包版本升至 `v0.5.0`，`hubble_agents` skill 内部版本升至 `v0.4.0`

---

## 3. API 端点

### 3.1 查询 Indicator 模板

```
GET /api/v1/config/indicator-templates
```

无需认证。返回模板数组，每条结构：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 模板显示名称 |
| `asset_type` | string | 资产类型（如 `"Crypto"`、`"A-shares"`、`"HK stocks"`、`"US stocks"`） |
| `analysis_type` | string | 分析类型（如 `"Technical Analysis"`、`"Fundamental Research"`） |
| `selected_indicator_ids` | string[] | 12 位 hex ID 列表，直接用作 `datasource_ids` |
| `prompt` | string | 完整分析指令，可直接使用 |

---

## 4. 流程设计

### 4.1 入口改动（自适应创建流程）

| 场景 | 行为 |
|---|---|
| 用户已提供全部必填字段 | 直接展示请求体摘要，确认后执行（不变） |
| 其他情况（部分或无字段） | **先问**：要从模板快速创建，还是手动配置所有参数？ |

### 4.2 模板路径（5 步）

**步骤 1 — 获取并展示模板列表**

调用 `GET /api/v1/config/indicator-templates`，按 `asset_type` 分组展示，每条显示序号、模板名、分析类型：

```
Crypto:
  1. High-Frequency Momentum & Scalping  [Technical Analysis]
  2. Trend Regime & Position Sizing       [Technical Analysis]

A-shares:
  3. Multi-Timeframe Trend Following      [Technical Analysis]
  4. Short-Term Mean Reversion & Momentum [Technical Analysis]
  5. Fundamental Valuation Deep Dive      [Fundamental Research]
  ...
```

**步骤 2 — 用户选模板**（输入序号）

从所选模板提取：
- `datasource_ids` ← `selected_indicator_ids`
- `prompt` ← 模板 `prompt`
- `asset_type` ← 模板 `asset_type`
- `analysis_type` ← 模板 `analysis_type`

**步骤 3 — 追问 Agent 名称**

> "这个 Agent 叫什么名字？"

**步骤 4 — 追问 LLM 选择**

> "使用哪个 LLM？`gemini_vertex`（gemini-3-flash-preview，通用）/ `minimax`（MiniMax-M2.7，中文场景）"

**步骤 5 — 可选自定义 prompt，然后确认创建**

展示模板 prompt 的前两行预览，询问：

> "模板 prompt 已内置详细的分析指令。要直接使用，还是在模板基础上补充说明？"

- 直接使用 → prompt 保持原样
- 补充说明 → 将用户输入**追加**到模板 prompt 末尾（不覆盖原始指令）

展示完整 JSON body 摘要，等用户确认后执行：

```bash
POST /api/v1/agents/user-research
```

创建成功后轮询部署状态（与现有流程相同）。

### 4.3 手动路径

现有引导模式完全不变（name → prompt → asset_type → analysis_type → datasource_ids → LLM → is_public）。

---

## 5. Skill 文档变更摘要

| 位置 | 变更内容 |
|---|---|
| 文件头部版本号 | `v0.3.1` → `v0.5.0` |
| 自适应创建流程 | 增加"先问模板或手动"入口判断 |
| 新增小节：查询 Indicator 模板 | 端点说明、字段说明 |
| 新增小节：模板创建路径 | 5 步完整流程 |

---

## 6. 版本升级

| 文件 | 变更 |
|---|---|
| `VERSION` | `v0.4.0` → `v0.5.0` |
| `CC.md` | 版本号 `v0.4.0` → `v0.5.0` |
| `README.md` | 版本号 `v0.4.0` → `v0.5.0` |
| `cc/skills/hubble_agents/SKILL.md` | 内部版本 `v0.3.1` → `v0.5.0`，新增模板功能 |

---

## 7. 不涉及的变更

- `GET /api/v1/research/config`（Creator datasource 代理）：模板流程不调用，skill 文档无需修改
- 所有其他 skill 文件（hubble_credits、hubble_runs 等）：不变
- User Research Agent 的更新、删除、版本管理流程：不变
