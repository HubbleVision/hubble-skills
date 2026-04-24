# Research Agent Template Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `hubble_agents` skill 的 User Research Agent 创建流程增加模板支持，让用户可以直接从预设模板快速创建 Agent，无需手动选择指标或编写 prompt。

**Architecture:** 纯 Markdown 文件修改，无代码变更。两个 skill 文件（`cc/` 和 `openclaw/`）同步更新，同时更新包版本号相关文件。

**Tech Stack:** Markdown, bash (grep 验证)

---

## 文件改动一览

| 文件 | 操作 | 说明 |
|---|---|---|
| `cc/skills/hubble_agents/SKILL.md` | 修改 | 主体改动：版本号、新端点、创建流程 |
| `openclaw/skills/hubble_agents/SKILL.md` | 修改 | 同步相同功能改动，保持 openclaw 格式 |
| `VERSION` | 修改 | `v0.4.0` → `v0.5.0` |
| `CC.md` | 修改 | `v0.4.0` → `v0.5.0` |
| `README.md` | 修改 | `v0.3.0` → `v0.5.0` |

---

## Task 1: 更新 cc/skills/hubble_agents/SKILL.md

**Files:**
- Modify: `cc/skills/hubble_agents/SKILL.md`

- [ ] **Step 1: 确认当前文件内容**

```bash
grep -n "Version:\|自适应创建流程\|查询可用数据源\|indicator" \
  cc/skills/hubble_agents/SKILL.md
```

预期输出包含：`Version: v0.3.1`、`自适应创建流程`、`查询可用数据源`，且不含 `indicator-templates`。

- [ ] **Step 2: 更新版本号**

将文件第 8 行：
```
Version: v0.3.1
```
改为：
```
Version: v0.5.0
```

- [ ] **Step 3: 更新"自适应创建流程"——替换入口判断逻辑**

将以下内容：
```
#### 自适应创建流程

根据用户提供的信息量决定行为：

- **用户已提供全部必填字段** → 直接展示请求体摘要，确认后执行。
- **用户提供了部分字段** → 只追问缺失的必填项，不询问模式。
- **用户未提供任何字段** → 询问用户偏好：
  > "要我一步步引导你填写参数，还是你直接告诉我所有内容？"

**引导模式提问顺序（每次只问一个）**：
```
替换为：
```
#### 自适应创建流程

根据用户提供的信息量决定行为：

- **用户已提供全部必填字段** → 直接展示请求体摘要，确认后执行。
- **其他情况** → 先问：
  > "要从模板快速创建，还是手动配置所有参数？"
  - **模板** → 进入模板创建路径（见下方）
  - **手动** → 进入引导模式（每次只问一个）

**引导模式提问顺序（每次只问一个）**：
```

- [ ] **Step 4: 在"引导模式提问顺序"末尾后追加"模板创建路径"小节**

找到以下内容（引导模式最后一行）：
```
7. 是否公开到市场？（可选，默认 `false`，直接回车跳过）

收集完毕后，展示完整 JSON body，等用户确认后再执行。
```
在其后追加：
```

**模板创建路径（5 步）**：

1. 调用 `GET /api/v1/config/indicator-templates`，按 `asset_type` 分组展示模板列表（序号、名称、分析类型），等用户输入序号选择。
2. 询问：这个 Agent 叫什么名字？
3. 询问：使用哪个 LLM？`gemini_vertex`（gemini-3-flash-preview，通用）/ `minimax`（MiniMax-M2.7，中文场景）
4. 展示模板 prompt 前两行预览，询问："要直接使用模板指令，还是在模板基础上补充说明？"
   - 直接使用 → prompt 不变
   - 补充说明 → 将用户输入追加到模板 prompt 末尾（不覆盖原始指令）
5. 展示完整 JSON body，等用户确认后执行创建请求。

从模板提取的字段：`datasource_ids` ← `selected_indicator_ids`，`prompt`、`asset_type`、`analysis_type` 直接使用。
```

- [ ] **Step 5: 在"查询可用数据源"一节之后新增"查询 Indicator 模板"一节**

找到以下内容：
```
每条记录包含 `id`（填入请求体）、`name`（展示名）和 `params`（配置参数）。

---

### 列出 User Research Agents
```
在 `---` 与 `### 列出 User Research Agents` 之间插入：
```

### 查询 Indicator 模板

获取预设分析模板，每条模板已内置 `datasource_ids` 和专业 `prompt`，可直接用于创建 User Research Agent。

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
```

- [ ] **Step 6: 验证改动**

```bash
grep -n "Version:\|模板创建路径\|indicator-templates\|其他情况" \
  cc/skills/hubble_agents/SKILL.md
```

预期：
- 含 `Version: v0.5.0`
- 含 `模板创建路径`
- 含 `/api/v1/config/indicator-templates`
- 含 `其他情况`（新入口判断）
- 不含 `v0.3.1`

- [ ] **Step 7: Commit**

```bash
git add cc/skills/hubble_agents/SKILL.md
git commit -m "feat(cc): hubble_agents v0.5.0 — 新增 User Research Agent 模板创建路径"
```

---

## Task 2: 更新 openclaw/skills/hubble_agents/SKILL.md

**Files:**
- Modify: `openclaw/skills/hubble_agents/SKILL.md`

openclaw 版本结构与 cc 版本基本相同，但动作节使用 `### Action:` 前缀，自适应逻辑略有差异。

- [ ] **Step 1: 确认当前内容**

```bash
grep -n "Version:\|自适应收集参数\|查询可用数据源\|indicator" \
  openclaw/skills/hubble_agents/SKILL.md
```

预期：含 `Version: v0.3.1`、`自适应收集参数`；不含 `indicator-templates`。

- [ ] **Step 2: 更新版本号**

将：
```
Version: v0.3.1
```
改为：
```
Version: v0.5.0
```

- [ ] **Step 3: 更新"自适应收集参数"入口判断**

将：
```
- 用户已提供全部必填字段 → 直接展示请求体摘要，确认后执行。
- 用户提供了部分字段 → 只追问缺失的必填项。
- 用户未提供任何字段 → 先询问：
  > "要我一步步引导你填写，还是你直接告诉我所有参数？"
```
替换为：
```
- 用户已提供全部必填字段 → 直接展示请求体摘要，确认后执行。
- 其他情况 → 先问：
  > "要从模板快速创建，还是手动配置所有参数？"
  - **模板** → 进入模板创建路径（见下方）
  - **手动** → 进入引导模式（每次只问一个）
```

- [ ] **Step 4: 在引导模式末尾后追加模板创建路径**

找到以下内容（openclaw 版本引导模式末尾）：
```
7. 是否公开到市场？（可选，默认 `false`，可跳过）

全部收集完毕后，展示完整 JSON body，等用户确认后再执行。
```
在其后追加：
```

**模板创建路径（5 步）**：

1. 调用 `GET /api/v1/config/indicator-templates`，按 `asset_type` 分组展示模板列表（序号、名称、分析类型），等用户输入序号选择。
2. 询问：这个 Agent 叫什么名字？
3. 询问：使用哪个 LLM？`gemini_vertex`（gemini-3-flash-preview，通用）/ `minimax`（MiniMax-M2.7，中文场景）
4. 展示模板 prompt 前两行预览，询问："要直接使用模板指令，还是在模板基础上补充说明？"
   - 直接使用 → prompt 不变
   - 补充说明 → 将用户输入追加到模板 prompt 末尾（不覆盖原始指令）
5. 展示完整 JSON body，等用户确认后执行创建请求。

从模板提取的字段：`datasource_ids` ← `selected_indicator_ids`，`prompt`、`asset_type`、`analysis_type` 直接使用。
```

- [ ] **Step 5: 在"查询可用数据源"节之后新增"查询 Indicator 模板"节**

找到 openclaw 版本中"查询可用数据源"节末尾（`---` 之前）：
```bash
grep -n "查询可用数据源\|列出 User Research" openclaw/skills/hubble_agents/SKILL.md
```

在对应位置的 `---` 与下一个 `### Action:` 之间插入：
```

### Action: 查询 Indicator 模板

Call:

- `GET /api/v1/config/indicator-templates`

获取预设分析模板，每条模板已内置 `datasource_ids` 和专业 `prompt`，可直接用于创建 User Research Agent。无需认证。

每条模板字段：

| 字段 | 说明 |
|---|---|
| `name` | 模板显示名称 |
| `asset_type` | 资产类型（如 `"Crypto"`、`"A-shares"`、`"HK stocks"`、`"US stocks"`） |
| `analysis_type` | 分析类型（如 `"Technical Analysis"`、`"Fundamental Research"`） |
| `selected_indicator_ids` | 12 位 hex ID 列表，直接用作 `datasource_ids` |
| `prompt` | 完整分析指令，可直接使用 |

---
```

- [ ] **Step 6: 验证改动**

```bash
grep -n "Version:\|模板创建路径\|indicator-templates\|其他情况" \
  openclaw/skills/hubble_agents/SKILL.md
```

预期：含 `Version: v0.5.0`、`模板创建路径`、`indicator-templates`、`其他情况`；不含 `v0.3.1`。

- [ ] **Step 7: Commit**

```bash
git add openclaw/skills/hubble_agents/SKILL.md
git commit -m "feat(openclaw): hubble_agents v0.5.0 — 同步新增 User Research Agent 模板创建路径"
```

---

## Task 3: 更新包版本号文件

**Files:**
- Modify: `VERSION`
- Modify: `CC.md`
- Modify: `README.md`

- [ ] **Step 1: 确认当前版本号**

```bash
cat VERSION
grep "版本\|Version" CC.md README.md
```

预期：`VERSION` 为 `v0.4.0`，`CC.md` 含 `v0.4.0`，`README.md` 含 `v0.3.0`。

- [ ] **Step 2: 更新 VERSION 文件**

将文件内容从：
```
v0.4.0
```
改为：
```
v0.5.0
```

- [ ] **Step 3: 更新 CC.md**

将：
```
当前版本：`v0.4.0`
```
改为：
```
当前版本：`v0.5.0`
```

- [ ] **Step 4: 更新 README.md**

将：
```
Version: v0.3.0
```
改为：
```
Version: v0.5.0
```

- [ ] **Step 5: 验证**

```bash
cat VERSION && grep "版本\|Version" CC.md README.md
```

预期：三个文件均显示 `v0.5.0`。

- [ ] **Step 6: Commit**

```bash
git add VERSION CC.md README.md
git commit -m "chore: 升级 Skills 至 v0.5.0，hubble_agents 新增模板创建支持"
```
