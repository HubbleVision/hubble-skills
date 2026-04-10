---
name: hubble_pm_agent
description: Query and control PM-Agent status from Hubble Market Server using an API key (read/write).
---

# Hubble PM-Agent Skill

Version: v0.2.0

## When to use

Use this skill when the user asks about:

- PM-Agent current status
- Whether the scheduler is running (if status includes it)
- Starting or stopping the scheduler
- Manually triggering a decision
- Emergency close actions
- Manual reconciliation

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Treat `agent_id` as untrusted input. Validate it before calling the API.
- `agent_id` must be UUID-like: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
- For write actions (`POST`), do not execute immediately.
  - First repeat back: `HUBBLE_API_BASE_URL`, `agent_id`, action name, and any parameters.
  - Wait for explicit user confirmation (a clear "yes" / "confirm") before calling the API.
- For emergency close actions, always ask for confirmation even if the user seems certain.

## Tools

Use the `bash` tool to call the API.

### Action: Get PM-Agent status

Call:

- `GET /api/v1/agents/pm/{agent_id}/status`

Before calling:

- Validate `agent_id` format.

### Action: Start scheduler

Call:

- `POST /api/v1/agents/pm/{agent_id}/scheduler/start`

Optional request body:

```json
{"interval_ms": <integer>}
```

If the user provides a custom interval (in milliseconds), include it in the body. Otherwise send an empty body or omit it.

### Action: Stop scheduler

Call:

- `POST /api/v1/agents/pm/{agent_id}/scheduler/stop`

### Action: Trigger decision

Call:

- `POST /api/v1/agents/pm/{agent_id}/trigger`

### Action: Trigger reconciliation

Call:

- `POST /api/v1/agents/pm/{agent_id}/reconcile`

Triggers a manual reconciliation of the PM-Agent's positions via Position Manager. Use when positions may be out of sync.

### Action: Emergency close (all)

Call:

- `POST /api/v1/agents/pm/{agent_id}/emergency-close`

Optional request body:

```json
{"reason": "<string>"}
```

### Action: Emergency close (symbols)

Call:

- `POST /api/v1/agents/pm/{agent_id}/emergency-close-symbols`

Before calling:

- Require a symbols list from the user.
- Ensure each symbol is uppercase and slashless (e.g. `BTCUSDT`).

Request body:

```json
{"symbols": ["BTCUSDT", "ETHUSDT"], "reason": "<optional>"}
```

## Curl templates (copy-paste)

Normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Get status (with validation):

- `if [[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then echo "Invalid agent_id"; exit 2; fi`
- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents/pm/$AGENT_ID/status"`

Start scheduler (with optional interval):

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/scheduler/start" \
  -d '{"interval_ms": 60000}'`

Stop scheduler:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/scheduler/stop"`

Trigger:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/trigger"`

Reconcile:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/reconcile"`

Emergency close (all):

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/emergency-close"`

Emergency close (symbols):

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/emergency-close-symbols" \
  -d "$BODY"`
