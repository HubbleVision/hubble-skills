---
name: hubble_pm_agent
description: Use when the user asks about PM-Agent status, starting or stopping the scheduler, triggering a decision, reconciling positions, or performing emergency close actions via the Hubble Market API.
---

# Hubble PM-Agent Skill

Version: v0.2.1

## When to use

Use this skill when the user asks about:

- PM-Agent current status
- Starting or stopping the scheduler
- Manually triggering a decision round
- Manual reconciliation of positions
- Emergency close (all positions or specific symbols)

## Requirements

Read from environment:

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY` — must start with `hb_sk_`

## Safety rules

- **Never print `HUBBLE_API_KEY`**.
- Validate `agent_id` format before use: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
- For **all write actions** (`POST`), repeat back: `HUBBLE_API_BASE_URL`, `agent_id`, action name, and any parameters — then wait for explicit "yes" / "confirm" before calling.
- For emergency close actions, always ask for confirmation even if the user seems certain.

## Setup

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
[[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] && echo "Invalid agent_id" && exit 2
```

---

## Actions

### Get PM-Agent status

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/pm/$AGENT_ID/status"
```

---

### Start scheduler — requires confirmation

Optional body: `{"interval_ms": <integer>}` — include if user specifies a custom interval in milliseconds.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/scheduler/start" \
  -d '{"interval_ms": 60000}'
```

---

### Stop scheduler — requires confirmation

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/scheduler/stop"
```

---

### Trigger decision — requires confirmation

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/trigger"
```

---

### Trigger reconciliation — requires confirmation

Use when positions may be out of sync. Proxies to Position Manager.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/reconcile"
```

---

### Emergency close (all positions) — requires confirmation

Optional body: `{"reason": "<string>"}`.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/emergency-close" \
  -d '{"reason": "manual close"}'
```

---

### Emergency close (specific symbols) — requires confirmation

Symbols must be uppercase and slashless (e.g. `BTCUSDT`).

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm/$AGENT_ID/emergency-close-symbols" \
  -d '{"symbols": ["BTCUSDT", "ETHUSDT"], "reason": "manual close"}'
```
