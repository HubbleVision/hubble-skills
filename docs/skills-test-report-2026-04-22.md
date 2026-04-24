> **⚠️ 2026-04-23 更新 / 结论修正**
>
> 本报告 §2.2 把 "openclaw 缺 hubble_auth" 列为 P0 回退、§5 行动建议 #2 要求 port `cc/skills/hubble_auth` → `openclaw/skills/`。**这两项结论已被推翻，不再执行**。
>
> 正确结论：skill 用 `HUBBLE_API_KEY` (`hb_sk_...`) 做鉴权，auth / 登录流程（邮箱 OTP、钱包签名、access token）属于用户拿到 API key 之前的 onboarding，不应进入任何 skill。`cc/skills/hubble_auth/` 已于 2026-04-23 移除（tombstone 保留在原目录等待 `rm -rf`），openclaw 侧不补齐。
>
> 完整原理 + 禁止清单见 `docs/skill-design-principles.md` → 原则 1。
>
> 本报告其余结论（credits packages 回退、description 风格对齐、`hubble_agents` 未提 deploy job/versions/rollback、`amb_3` 跑 research agent 优先 hit hubble_runs）仍然有效。
>
> ---

# hubble-skills 测试报告

- 日期：2026-04-22
- 版本：README.md 声明 `v0.5.0`，OPENCLAW.md 声明 `v0.3.0`
- 测试范围：`cc/skills/` 全部 6 个 + `openclaw/skills/` 全部 5 个
- 测试项：(1) SKILL.md 静态审查；(2) description 触发 eval；(3) 端到端真实 API 调用
- 结论：cc 组整体可用、风险可控；openclaw 组存在**功能回退**和**顶层文档版本漂移**需要修

---

## 1. 被测 skill 清单

| # | 位置 | Skill | 版本 | description 首句 |
|---|---|---|---|---|
| 1 | cc/skills | hubble_auth | v0.4.0 | Use when the user asks about logging into Hubble Market, obtaining an access token... |
| 2 | cc/skills | hubble_credits | v0.4.0 | Use when the user asks about Hubble credits balance, transaction history, deposit records, recharge packages... |
| 3 | cc/skills | hubble_agents | v0.5.0 | Use when the user asks to list, view, create, update, or delete agents (PM / User Research / generic)... |
| 4 | cc/skills | hubble_pm_agent | v0.2.1 | Use when the user asks about PM-Agent status, starting/stopping scheduler, trigger, reconcile, emergency close... |
| 5 | cc/skills | hubble_runs | v0.2.1 | Use when the user asks to run an agent, check a run's status, or list recent runs... |
| 6 | cc/skills | hubble_logs | v0.2.1 | Use when the user asks about PM agent logs, research logs, orders, positions, order history, position recovery, PnL... |
| 7 | openclaw/skills | hubble_credits | v0.2.0 | Query credits balance, transactions, deposits, and create recharge orders... |
| 8 | openclaw/skills | hubble_agents | v0.5.0 | Manage agents (PM agents, User Research agents, and generic agents)... |
| 9 | openclaw/skills | hubble_pm_agent | v0.2.0 | Query and control PM-Agent status from Hubble Market Server... (read/write) |
| 10 | openclaw/skills | hubble_runs | v0.2.0 | Create and query agent runs... with x402 payment flow support |
| 11 | openclaw/skills | hubble_logs | v0.2.0 | Query agent logs, orders, positions, and PnL via /api/v1/agent-logs endpoints... |

---

## 2. 静态审查（SKILL.md 内容）

### 2.1 健康项（两组共有的优点）

- 所有 skill 都在 frontmatter 里写清楚了 `name` 和 `description`，没有格式错误。
- "Safety rules" 都明确了**不打印 `HUBBLE_API_KEY`**、**写操作需要二次确认**，这是关键的。
- 涉及 ID 参数的 skill（agents / pm_agent / runs）都给出了 UUID 正则验证规则：`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`。
- `hubble_logs` 两组都强调"设置 `page_size` 防止响应过大"，这是很好的 guardrail。
- `hubble_runs` 正确描述了 x402 两步付费流程，并明确"不自动完成付费"，安全边界合理。

### 2.2 问题清单（按严重度排序）

#### 🔴 严重：openclaw/hubble_credits 功能回退

cc 版本（v0.4.0）已包含的 `GET /api/v1/credits/packages` 与 `POST /api/v1/credits/deposits/by-package` **在 openclaw 版本（v0.2.0）里完全缺失**。
- 影响：用户在 OpenClaw 下说"列出充值套餐"/"按套餐充值"时，skill 根本不会发起对应的 API 调用。
- 建议：把 cc/skills/hubble_credits 的"List recharge packages" 和 "Create deposit by package" 两节合并到 openclaw 版本，统一升到 v0.4.0。

#### 🔴 严重：openclaw 缺失 `hubble_auth`

cc 有完整的 `hubble_auth`（邮箱验证码登录、钱包签名登录、`/auth/me`）。openclaw 完全没有这个 skill。
- 影响：OpenClaw 用户无法用自然语言触发登录流程；必须预先手动拿到 JWT/API key 才能用其它 skill。
- 建议：要么把 `cc/skills/hubble_auth/` 同步复制到 `openclaw/skills/`，要么在 OPENCLAW.md 里说明"登录流程不通过 skill"并提供替代指引。

#### 🟡 中等：顶层文档版本不一致

- `README.md` 写 `v0.5.0`
- `OPENCLAW.md` 写 `v0.3.0`
- `CC.md` 写 `v0.5.0`
- 各 skill 个体版本散落在 v0.2.0 ~ v0.5.0 之间

建议：统一采用"仓库版本"+"每个 skill 独立 semver"的双层方案，在 README 或 CHANGELOG 里列明每个 skill 的当前版本，避免 README 和 SKILL.md 版本不一致。

#### 🟡 中等：cc 和 openclaw description 风格不一致会影响触发

- cc 用"Use when the user asks about X / Y / Z"模板（命令式）—— 符合 Anthropic skill 推荐写法，对 Claude Code 路由友好。
- openclaw 用"Query X, Y, Z via Z endpoints"模板（声明式）—— 更像功能说明文档，LLM 在多个 skill 同时存在时路由精度会略低。

建议：统一改成 cc 的"Use when the user asks about..."模式。即便是 OpenClaw，这种 description 也更利于意图路由。

#### 🟡 中等：`hubble_agents` description 没提 "deploy job / versions / rollback"

两组的 description 都只提到 "list, view, create, update, or delete"，但 skill body 里实际还支持：
- 查询部署 job 状态（`GET /agents/user-research/jobs/{job_id}`）
- 版本历史 / 详情 / 回滚
- 数据源 / indicator 模板列表

当用户说"查 research agent 的 job 状态"或"回滚到 v2"时，光看 description 可能匹配不到。

建议：在 description 里显式加上 "deploy job status, versions, rollback, data sources, indicator templates"。

#### 🟢 低：`hubble_pm_agent` 和 `hubble_agents` 在"list PM agents vs. PM status"上会轻度竞争

- 当用户说"看看我的 PM agent"时，hubble_agents 会理解为 list；hubble_pm_agent 会理解为 status。
- 实际两个 skill 都合理，最差情况是先走错再切换，代价不高。

建议（可选）：在 hubble_pm_agent description 加一句 "for a specific PM agent by id"，暗示它是 per-agent 操作。

#### 🟢 低：`hubble_logs` description 里未提 "PM positions / position logs / PM position symbols"

body 里有这些细分接口，但 description 只说 "positions"。绝大多数情况下足够，不是阻塞。

#### 🟢 低：openclaw 版本多处出现 "Use the bash tool to call the API." 重复说明；cc 版本已精简掉

纯风格问题，不影响功能。建议统一精简。

### 2.3 cc vs openclaw 对齐矩阵

| 能力 | cc | openclaw | 备注 |
|---|---|---|---|
| Auth (email / wallet) | ✅ v0.4.0 | ❌ 缺失 | 严重回退 |
| Credits: balance / tx / deposits | ✅ | ✅ | OK |
| Credits: packages / deposit-by-package | ✅ | ❌ | 严重回退 |
| Agents: PM CRUD | ✅ | ✅ | OK |
| Agents: User Research CRUD + jobs + versions | ✅ | ✅ | 都有，但 description 未提 |
| PM-Agent: status / scheduler / trigger / reconcile / emergency-close | ✅ | ✅ | OK |
| Runs: create / get / list + x402 | ✅ | ✅ | OK |
| Logs: pm / research / orders / positions / pnl / recovery | ✅ | ✅ | OK |

---

## 3. Description 触发 eval

eval 数据集见 `docs/eval_prompts.json`（42 条：30 正例 + 4 歧义 + 6 负例 + 2 跨 skill 组合）。

### 3.1 评测方式

把每条 prompt 与 6 个 skill 的 description 做相关性判断：
- ✅ = 预计会正确触发预期 skill；
- ⚠️ = 预计能触发但可能先去到其它 skill，需要一次切换；
- ❌ = 预计无法正确触发。

注：严格意义上最终还是要在真实 Claude Code / OpenClaw 里 eval。下面是"按当前 description 文本"给出的预估，可作为优化依据。

### 3.2 cc 组结果（按类别汇总）

| 类别 | 总数 | ✅ | ⚠️ | ❌ | 命中率（含 ⚠️） |
|---|---|---|---|---|---|
| 正例 | 30 | 27 | 2 | 1 | 96.7% |
| 歧义 | 4 | 2 | 2 | 0 | 100% |
| 负例 | 6 | 6 | 0 | 0 | 100%（不误触发） |

关键失败/边界用例（cc 组）：

- ❌ `agents_pos_6` "查看 research agent 的部署 job 状态" → cc hubble_agents description 未提 "deploy job status"。即使 body 里支持，路由层可能不命中。
- ⚠️ `agents_pos_8` "把这个 research agent 回滚到 v2" → 同上，description 没提 "rollback / versions"。
- ⚠️ `amb_3` "我想在 hubble 上跑个新的 research agent" → 字面"跑" 容易优先匹配 hubble_runs，但用户意图是 create。需要 agent 做二次确认。
- ⚠️ `amb_4` "我的账户里还有多少钱" → "多少钱" 比"credits 余额"模糊，描述文本未收录"账户/余额/钱"之类的中文词。

### 3.3 openclaw 组结果

| 类别 | 总数 | ✅ | ⚠️ | ❌ | 命中率 |
|---|---|---|---|---|---|
| 正例（不含 auth 类） | 24 | 19 | 2 | 3 | 87.5% |
| auth 类正例 | 6 | 0 | 0 | 6 | 0% — 无 skill |
| 歧义 | 4 | 1 | 2 | 1 | 75% |
| 负例 | 6 | 6 | 0 | 0 | 100% |

关键失败用例（openclaw 组）：

- ❌ 所有 `auth_pos_*` 6 条 → 无 `hubble_auth` skill，完全无法触发。
- ❌ `credits_pos_4` "列出所有充值套餐" → openclaw/hubble_credits description 未提 packages。
- ❌ `credits_pos_6` "按套餐下一个充值订单" → 同上。
- ⚠️ `amb_4` "我的账户里还有多少钱" → openclaw description 风格声明式，"钱"语义匹配更弱。

### 3.4 Description 优化建议（可直接改 SKILL.md）

```diff
- description: Query credits balance, transactions, deposits, and create recharge orders from Hubble Market Server using an API key.
+ description: Use when the user asks about Hubble credits balance, account balance ("还有多少钱"), transaction history, deposits, recharge packages, or wants to recharge via a package or a specific amount.

- description: Manage agents (PM agents, User Research agents, and generic agents) on Hubble Market Server using an API key.
+ description: Use when the user asks to list, view, create, update, delete, or manage agents — including PM agents, User Research agents (data sources, indicator templates, deploy job status, version history, rollback), or generic agents.

- description: Query and control PM-Agent status from Hubble Market Server using an API key (read/write).
+ description: Use when the user asks about a specific PM-Agent's status, scheduler start/stop, decision trigger, position reconciliation, or emergency close — typically given an agent_id.

- description: Create and query agent runs from Hubble Market Server using an API key, with x402 payment flow support.
+ description: Use when the user asks to run (execute) an agent, check a specific run's status, or list recent runs; note: "run" here means invoking an existing agent, not creating one.

- description: Query agent logs, orders, positions, and PnL via /api/v1/agent-logs endpoints using an API key, with safe defaults to limit response size.
+ description: Use when the user asks about decision logs, research logs, orders (list/single/history), positions, PM positions, position recovery, or PnL summary/orders data.
```

---

## 4. 端到端真实 API 调用（阻塞）

本次 session 的 bash sandbox 不可用，无法直接发起 curl 请求验证 API。已准备了一份离线自检脚本，放在：

- `docs/skills-selfcheck.sh` （见附件；只调用只读接口，绝不触发付费/写操作）

在你本地运行：

```bash
export HUBBLE_API_BASE_URL="https://market-v2.bedev.hubble-rpc.xyz"
export HUBBLE_API_KEY="hb_sk_...你的 key..."
bash docs/skills-selfcheck.sh
```

脚本覆盖：credits balance / transactions / deposits / packages、agents pm list、research data-sources、indicator-templates、PnL summary（page_size=5 安全默认）。

---

## 5. 行动建议（按优先级）

1. **P0**：把 openclaw 的 `hubble_credits` 升到 v0.4.0，补齐 `packages` 和 `deposits/by-package` 两个 action（参照 cc 版本直接拷贝相应章节）。
2. **P0**：决定 openclaw 是否支持 `hubble_auth`。如要支持，直接 port `cc/skills/hubble_auth` → `openclaw/skills/hubble_auth`。
3. **P1**：统一 description 模式到 "Use when the user asks..."，并在 description 里补齐 deploy job / versions / rollback / packages 等关键词。
4. **P1**：修好 README.md / OPENCLAW.md / CC.md 顶层版本标注。建议加 `CHANGELOG.md` 统一管理每个 skill 的版本。
5. **P2**：每个 skill 的 SKILL.md 建议新增 "Examples" 一节（2-3 个 "用户自然语言 → 最终 curl"），作为 eval 的 ground truth 来源。
6. **P2**：把本文件的 eval prompt 集固化进仓库 `evals/`，接上 skill-creator 的 benchmark 流程，每次改 description 后自动回归。

---

## 附录 A：eval prompt 集摘要

| ID | prompt | 预期 skill | 命中（cc / openclaw） |
|---|---|---|---|
| auth_pos_1 | 帮我登录 Hubble Market | hubble_auth | ✅ / ❌ |
| auth_pos_2 | 给我的邮箱发一个验证码 | hubble_auth | ✅ / ❌ |
| auth_pos_5 | get me an access token from Hubble Market | hubble_auth | ✅ / ❌ |
| credits_pos_1 | 查一下我的 Hubble credits 余额 | hubble_credits | ✅ / ✅ |
| credits_pos_4 | 列出所有充值套餐 | hubble_credits | ✅ / ❌ |
| credits_pos_6 | 按套餐下一个充值订单 | hubble_credits | ✅ / ❌ |
| agents_pos_1 | 列出我的 PM agents | hubble_agents | ✅ / ✅ |
| agents_pos_6 | 查看 research agent 的部署 job 状态 | hubble_agents | ❌ / ⚠️ |
| agents_pos_8 | 把这个 research agent 回滚到 v2 | hubble_agents | ⚠️ / ⚠️ |
| pm_pos_1 | 看看 PM-Agent 现在的状态 | hubble_pm_agent | ✅ / ✅ |
| pm_pos_4 | 紧急平仓 | hubble_pm_agent | ✅ / ✅ |
| runs_pos_1 | 跑一下这个 agent | hubble_runs | ✅ / ✅ |
| logs_pos_1 | 看看最近的 PM 决策日志 | hubble_logs | ✅ / ✅ |
| logs_pos_2 | 拉 BTCUSDT 最近一天的 PnL summary | hubble_logs | ✅ / ✅ |
| amb_3 | 我想在 hubble 上跑个新的 research agent | hubble_agents | ⚠️ / ⚠️ |
| amb_4 | 我的账户里还有多少钱 | hubble_credits | ⚠️ / ❌ |
| neg_1 | 给我写一首关于 BTC 的诗 | none | ✅ / ✅ |
| neg_4 | 用 Python 写一个快排 | none | ✅ / ✅ |

完整 42 条在 `docs/eval_prompts.json`。
