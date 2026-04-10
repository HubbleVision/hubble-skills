# Claude Code 使用说明（hubble-skills）

本仓库提供一组可直接被 Claude Code 加载的 skills，目录位于：

- `cc/skills/`

当前版本：`v0.2.1`

## 前置条件

- 已安装 Claude Code CLI（`claude` 命令可用）
- 你有可用的 Hubble Market Server API Key（前缀为 `hb_sk_`）

## 必需环境变量（必须配置）

- `HUBBLE_API_BASE_URL`
  - 默认：`https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY`
  - 你的 API key，必须以 `hb_sk_` 开头

示例：

```bash
export HUBBLE_API_BASE_URL="https://market-v2.bedev.hubble-rpc.xyz"
export HUBBLE_API_KEY="hb_sk_xxxxxxxxxxxxxxxxx"
```

安全建议：

- 不要把 `HUBBLE_API_KEY` 提交到 Git
- 不要把 `HUBBLE_API_KEY` 打印到日志/截图/聊天记录

## 安装 skills

Claude Code 的个人 skill 默认加载路径为：

- `~/.claude/skills/`

如果目录不存在，先创建：

```bash
mkdir -p ~/.claude/skills
```

### 方案 A：symlink（推荐，方便升级）

```bash
ln -sfn "$(pwd)/cc/skills/hubble_credits"  ~/.claude/skills/hubble_credits
ln -sfn "$(pwd)/cc/skills/hubble_agents"   ~/.claude/skills/hubble_agents
ln -sfn "$(pwd)/cc/skills/hubble_pm_agent" ~/.claude/skills/hubble_pm_agent
ln -sfn "$(pwd)/cc/skills/hubble_runs"     ~/.claude/skills/hubble_runs
ln -sfn "$(pwd)/cc/skills/hubble_logs"     ~/.claude/skills/hubble_logs
```

### 方案 B：copy（适合离线/服务器场景）

```bash
cp -R cc/skills/* ~/.claude/skills/
```

## 使用方式

在 Claude Code 会话中，直接描述任务即可触发对应 skill，例如：

- "查一下我的 Hubble credits 余额"
- "列出我的 PM Agent"
- "查看 PM Agent `<agent_id>` 的状态"
- "看看最近的 PM 决策日志"

Claude Code 会自动识别并加载对应 skill 来处理请求。

## 验证（最小自检）

安装后可用 `curl` 直接验证环境变量和 API Key 是否正确（不依赖 Claude Code）：

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/balance"
```

## 常见问题排查

- `401 Unauthorized`：`HUBBLE_API_KEY` 缺失/无效/过期/被禁用
- `403 Forbidden`：API key 对应的用户没有权限（如非 owner）
- `404 Not Found`：URL 路径或 `agent_id` 参数不正确
- Skills 不生效：确认 `~/.claude/skills/` 目录下已有对应 skill 文件夹，Claude Code 无需重启即可加载新 skill
