# hubble-skills evals

自动化 eval 套件。每次改 skill 描述都可以一键回归，避免"改了描述哪边悄悄漏触发"。

## 目录结构

```
evals/
├── trigger/                        # 每个 skill 单独的 should_trigger 测试集
│   ├── hubble_credits.json         # 20 条: 10 should-trigger + 10 near-miss
│   ├── hubble_agents.json
│   ├── hubble_pm_agent.json
│   ├── hubble_runs.json
│   ├── hubble_logs.json
│   └── run_trigger_eval.py         # runner: 针对单个 skill 跑 should_trigger 评测
├── routing/                        # 跨 skill 路由 eval（给 5 个 skill，挑一个）
│   ├── routing_eval.json           # 43 条: 正例 / 歧义 / 负例（含 5 条 auth_neg guardrail）
│   └── run_routing_eval.py         # runner: 针对 cc 或 openclaw 整组跑路由评测
├── results/                        # 本地结果（.gitignore 掉）
└── run_all.sh                      # 一键入口
```

> `hubble_auth` skill 已于 2026-04-23 移除，原因见 `docs/skill-design-principles.md` → 原则 1：skill 用 API key 鉴权，不应包含任何 auth / 登录 / API key 管理类接口。routing eval 里原 `auth_pos_*` 已改成 `auth_neg_*`（expected=null），作为回归 guardrail 确保不会再有 skill 错触发在登录 query 上。

`.github/workflows/skills-eval.yml` 在每次 PR 改到 `*/skills/**/SKILL.md` 或 `evals/**` 时自动跑，并在 PR 上贴结果评论。

## 前置

runner 走 `evals/_llm.py` 做后端自适应，**两种模式任挑一种**：

1. **本地 / Pro · Max 订阅用户（推荐）**：只要先用 `claude` 登过一次（auth 存 macOS Keychain / Linux `~/.claude/.credentials.json`），`bash evals/run_all.sh` 即可开跑，**不需要 API key**。runner 会 shell 出 `claude -p`，并把 `CLAUDE_CONFIG_DIR` 临时指向一个空目录 —— 这样 `~/.claude/skills/` 里装好的 hubble_* skill 不会被加载到 eval 调用里，避免 Claude "直接执行 skill 而不是回 JSON" 这种污染。
2. **CI / 有 API key**：export `ANTHROPIC_API_KEY=sk-ant-...`，runner 会自动切到 urllib 直调 Anthropic Messages API 的路径（更快，支持 assistant-prefill 强制 JSON 输出）。GitHub Actions 里用同名 secret。

共同需要的只有 Python 3.9+。两边都是 stdlib，零 pip 依赖。

> 早期版本 runner 直接 `claude -p` 但不隔离 config dir，导致在 query 高度匹配某个本地 skill 时，Claude 会去加载并执行那个 skill 的 SKILL.md 脚本。现在用 `CLAUDE_CONFIG_DIR=$(mktemp -d)` 临时隔离后就干净了。
>
> macOS 上 Claude Code 的 auth 存在 Keychain（service `"Claude Code-credentials"`，按名字查不依赖 config dir 路径），所以换 `CLAUDE_CONFIG_DIR` 不会让你重新登录。
>
> CLI 模式下每次调用会起一个 `claude -p` 子进程，开销比 API 模式大。runner 会把 `--workers` 自动 clamp 到 4；全量跑（约 143 条）预期在 5–15 分钟，取决于网络和模型。

## 本地运行

```bash
# 模式 1：Pro / Max 订阅（已 `claude` 登录），不用 API key
bash evals/run_all.sh

# 模式 2：有 API key（CI 同路径）
export ANTHROPIC_API_KEY=sk-ant-...

# 全部：两组 skill × trigger + routing
bash evals/run_all.sh

# 只跑某一类
bash evals/run_all.sh trigger        # 只跑 per-skill trigger eval
bash evals/run_all.sh routing        # 只跑跨 skill routing eval

# 只跑某个变体
bash evals/run_all.sh routing cc     # 只跑 cc 变体的 routing eval
bash evals/run_all.sh trigger openclaw

# debug 用，每个 eval 只跑前 N 条
HUBBLE_EVAL_LIMIT=3 bash evals/run_all.sh

# 换模型跑对比（默认 claude-sonnet-4-6）
HUBBLE_EVAL_MODEL=claude-opus-4-6 bash evals/run_all.sh routing cc
HUBBLE_EVAL_MODEL=claude-haiku-4-5-20251001 bash evals/run_all.sh routing cc

# 调并发
HUBBLE_EVAL_WORKERS=10 bash evals/run_all.sh
```

结果写到 `evals/results/`：
- `trigger-<variant>-<skill>.json` — 每个 skill 的 accuracy / precision / recall / F1
- `routing-<variant>.json` / `.md` — 跨 skill 路由命中率，附失败样例

跑完会在终端打印一张合并 summary 表格。

## 两种 eval 的区别

**trigger eval**（per-skill）：给 Claude 一个 skill 的 description + 一条用户 prompt，问"这个 skill 应不应该触发？"。测的是**单个 description 的语义清晰度** —— description 太宽会在负例上误触发（false positive），太窄会在正例上漏触发（false negative）。

**routing eval**（cross-skill）：给 Claude 一组 6 个 skill 的 description + 一条用户 prompt，问"挑哪个？"。测的是**多个 skill 共存时的路由精度** —— description 是否独特到能被正确挑中，不会被别的 skill 抢走。

两种都重要：trigger 帮你发现描述本身的问题，routing 帮你发现描述之间的冲突。

## 如何扩展 eval 集

**加一条 trigger 测试**：编辑 `evals/trigger/<skill_name>.json`，追加 `{"query": "...", "should_trigger": true|false}`。

**加一条 routing 测试**：编辑 `evals/routing/routing_eval.json` 的 `cases`，追加一条 `{"id": "...", "prompt": "...", "expected": "<skill_name_or_null>", "category": "..."}`。

**新 skill**：
1. 在 `evals/trigger/` 下加 `<new_skill>.json`，参考其它文件格式写 10 正 + 10 负共 20 条。
2. 路由 eval 里加几条针对这个新 skill 的正例。
3. runner 会自动识别，不需要改代码。

eval 集写好之后**先过 code review**，因为"对的答案"直接决定了回归的方向。坏的 ground truth 会让后续所有优化走偏。

## 如何读结果

- trigger eval 看 **F1**：低于 0.85 通常意味着 description 需要重写。
  - Precision 低 → description 太宽，要加"不触发"条件。
  - Recall 低 → description 不够具体，补充用户常用的说法、关键词。
- routing eval 看 **pass_rate** 和 **failures 表**：失败样例会直接告诉你"本来该走 X，却被判到 Y"。
  - 相同 description 在两组下都失败 → 描述本身有问题。
  - 只在一组下失败 → 可能是那一组有特定的描述干扰。

## 和 Anthropic skill-creator 的关系

这套 runner **等价于** `skill-creator/scripts/run_eval.py` 的简化版，专门为这个仓库定制：

- 后端自适应（见上）：本地走 `claude -p` + `CLAUDE_CONFIG_DIR` 隔离，有 key 时走 urllib 直调 API，都是 stdlib 零 pip 依赖。
- 额外提供了**跨 skill routing eval**，这在 skill-creator 里没有现成工具。
- 如果后面想用 `skill-creator/scripts/run_loop.py` 自动优化某个 description，直接把我们的 `evals/trigger/<skill>.json` 喂给它就行，格式完全兼容。

## CI 工作流

`.github/workflows/skills-eval.yml`：

- 在 PR 改到 SKILL.md 或 evals/ 时自动触发
- 产出 artifact: `evals/results/`
- 在 PR 上贴一张命中率表格评论

CI 里需要 secrets:
- `ANTHROPIC_API_KEY` — CI 走 API 路径（Ubuntu runner 没法用订阅 auth）

手动触发：Actions → skills-eval → Run workflow（可以选 mode：all / trigger / routing）。
