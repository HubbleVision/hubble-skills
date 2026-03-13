# OpenClaw 使用说明（hubble-skills）

本仓库提供一组可直接被 OpenClaw 加载的 skills，目录位于：

- `openclaw/skills/`

当前版本：`v0.1.0`

## 前置条件

- 已安装并运行 OpenClaw（本机或服务器均可）
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

## 安装 skills（copy 或 symlink）

OpenClaw 通常会从你的 OpenClaw workspace 下加载 skills：

- `~/.openclaw/workspace/skills/`

如果目录不存在，先创建：

```bash
mkdir -p ~/.openclaw/workspace/skills
```

### 方案 A：symlink（推荐，方便升级）

```bash
ln -sfn "$(pwd)/openclaw/skills/hubble_credits"  ~/.openclaw/workspace/skills/hubble_credits
ln -sfn "$(pwd)/openclaw/skills/hubble_agents"   ~/.openclaw/workspace/skills/hubble_agents
ln -sfn "$(pwd)/openclaw/skills/hubble_pm_agent" ~/.openclaw/workspace/skills/hubble_pm_agent
ln -sfn "$(pwd)/openclaw/skills/hubble_runs"     ~/.openclaw/workspace/skills/hubble_runs
ln -sfn "$(pwd)/openclaw/skills/hubble_logs"     ~/.openclaw/workspace/skills/hubble_logs
```

### 方案 B：copy（适合“拷贝到服务器后离线使用”）

```bash
cp -R openclaw/skills/* ~/.openclaw/workspace/skills/
```

## 运行用户提示（很重要）

skills 和环境变量必须配置在“运行 OpenClaw 的那个用户”下：

- 如果 OpenClaw 以 `root` 运行，那么路径就是：`/root/.openclaw/workspace/skills/`
- 如果以普通用户运行，就是：`/home/<user>/.openclaw/workspace/skills/`

如果你不确定 OpenClaw 以谁运行：

```bash
ps -ef | grep -i openclaw | grep -v grep
```

## 验证（最小自检）

只要环境变量已生效、skills 已被加载，你可以让 OpenClaw 使用 skill 访问接口。

也可以直接用 `curl` 验证 API Key / Base URL 是否正确（不依赖 OpenClaw）：

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/balance"
```

## 常见问题排查

- `401 Unauthorized`：通常是 `HUBBLE_API_KEY` 缺失/无效/过期/被禁用
- `403 Forbidden`：API key 对应的用户没有权限操作该资源（例如非 owner）
- `404 Not Found`：URL 路径或 `agent_id` 等参数不正确
- skills 不生效：优先确认“运行用户”是否一致（root vs 普通用户），以及 OpenClaw 进程是否需要重启才会重新加载 skills
