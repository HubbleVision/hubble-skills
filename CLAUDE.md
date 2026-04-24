# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库概述

`hubble-skills` 是一个 AI assistant skill 包，为 Claude Code（`cc/`）和 OpenClaw（`openclaw/`）提供操作 Hubble Market API 的能力。当前版本：`v0.5.1`（见 `VERSION`）。

每个 skill 对应一类业务操作，通过 `HUBBLE_API_KEY`（前缀 `hb_sk_`）鉴权，直接调 REST API。

## 目录结构

```
cc/skills/          # Claude Code skill 版本（5 个 skill）
openclaw/skills/    # OpenClaw skill 版本（内容基本相同）
evals/              # 自动化 eval 套件
  trigger/          # per-skill should_trigger 测试（每个 skill 20 条）
  routing/          # 跨 skill 路由测试（约 43 条）
  results/          # 本地结果，已 gitignore
docs/               # 设计文档和原则
data/               # 模板数据（template.json）
```

## 已有 Skills

| skill | 核心能力 |
|---|---|
| `hubble_agents` | PM agent / User Research agent CRUD、部署、版本管理 |
| `hubble_credits` | 积分余额查询、充值、流水记录 |
| `hubble_logs` | PM agent 决策日志查看 |
| `hubble_pm_agent` | PM agent 状态与调度管理 |
| `hubble_runs` | 已有 agent 的 x402 付费执行（pay-per-run） |

## 运行 Evals

```bash
# 全部（trigger + routing，cc 和 openclaw 两个变体）
bash evals/run_all.sh

# 只跑某一类
bash evals/run_all.sh trigger
bash evals/run_all.sh routing

# 只跑某个变体
bash evals/run_all.sh routing cc
bash evals/run_all.sh trigger openclaw

# Debug：每个 eval 只跑前 N 条
HUBBLE_EVAL_LIMIT=3 bash evals/run_all.sh

# 换模型
HUBBLE_EVAL_MODEL=claude-opus-4-6 bash evals/run_all.sh routing cc
```

**后端选择**（自动）：
- 未设置 `ANTHROPIC_API_KEY` → 走 `claude -p`（需先登录一次 Claude Code），eval 时临时隔离 `~/.claude/skills/` 防止 skill 污染结果
- 已设置 `ANTHROPIC_API_KEY` → 走 urllib 直调 API（更快，CI 使用此路径）

## CI

`.github/workflows/skills-eval.yml` 在以下情况自动跑 eval：
- PR 或 push 修改了 `cc/skills/**/SKILL.md`、`openclaw/skills/**/SKILL.md`、或 `evals/**`
- 需要 Actions secret：`ANTHROPIC_API_KEY`

跑完会在 PR 上贴一张命中率表格。

## 修改 Skill 的工作流

1. 编辑 `cc/skills/<skill_name>/SKILL.md` 和 `openclaw/skills/<skill_name>/SKILL.md`（两边保持同步）
2. 检查 `evals/trigger/<skill_name>.json` 是否需要补测试
3. 检查 `evals/routing/routing_eval.json` 的路由用例是否覆盖新改动
4. 本地跑 `bash evals/run_all.sh` 确认 F1 ≥ 0.85、routing pass rate 无下降

## 关键设计原则（见 `docs/skill-design-principles.md`）

**原则 1**：不要新增 auth/login 类 skill。所有 skill 以 `$HUBBLE_API_KEY` 鉴权，"如何获取 key"属于用户在 Hubble Market 网页上的 onboarding 流程，不进 skill。

**原则 2**：skill 的 `description` 必须覆盖 body 里的所有操作类型——description 是 LLM router 唯一能看到的摘要，body 里有但 description 没提的操作等于不存在。

**原则 3**：有语义重叠的 skill，两边 description 都要显式划边界。在 Hubble 业务里，"run" 专指 x402 付费执行（`hubble_runs`），"跑 research agent"是创建/部署（`hubble_agents`），必须在 description 里写清楚。

**新建 skill 检查清单**（每次都跑）：
- [ ] description 无 "login"、"sign in"、"access token"、"authenticate" 等字样
- [ ] body 每类 API 调用在 description 里有对应关键词
- [ ] 有语义重叠的 skill，description 都显式划清边界
- [ ] `evals/trigger/<new_skill>.json` 有 10 正 + 10 负共 20 条测试
- [ ] `evals/routing/routing_eval.json` 里有至少 2 条正例

## 安装 Skills（本地验证用）

```bash
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/cc/skills/hubble_credits"  ~/.claude/skills/hubble_credits
ln -sfn "$(pwd)/cc/skills/hubble_agents"   ~/.claude/skills/hubble_agents
ln -sfn "$(pwd)/cc/skills/hubble_pm_agent" ~/.claude/skills/hubble_pm_agent
ln -sfn "$(pwd)/cc/skills/hubble_runs"     ~/.claude/skills/hubble_runs
ln -sfn "$(pwd)/cc/skills/hubble_logs"     ~/.claude/skills/hubble_logs
```

安装后验证 API key 是否可用：

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/balance"
```
