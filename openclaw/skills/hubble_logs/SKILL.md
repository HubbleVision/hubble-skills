---
name: hubble_logs
description: Query agent logs and PnL via /api/v1/agent-logs endpoints using an API key, with safe defaults to limit response size.
---

# Hubble Logs Skill

Version: v0.1.0

## When to use

Use this skill when the user asks about:

- PM logs (decision logs)
- Research logs
- Orders / positions events
- PnL summary and PnL order details

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Treat `pm_id` and `round_id` as untrusted input.
  - `pm_id` is expected to be a UUID.
- Avoid large responses:
  - Always set `page_size` explicitly (default 100; keep <= 200 unless user insists).
  - Prefer narrow time windows (ask user for `start`/`end` if not provided).

## Tools

Use the `bash` tool to call the API.

## Common query params

Most endpoints support:

- `start`, `end` (RFC3339 or unix seconds/milliseconds)
- `pm_id`, `round_id`
- `token`
- `page`, `page_size`

PnL endpoints additionally support:

- `symbol` (e.g. `BTCUSDT`)
- `position_id`
- `action_types` (comma-separated, default `close,decrease`)

## Actions

### Action: PM logs

- `GET /api/v1/agent-logs/pm/logs`

### Action: Research logs

- `GET /api/v1/agent-logs/research/logs`

### Action: Orders

- `GET /api/v1/agent-logs/orders`

### Action: Positions

- `GET /api/v1/agent-logs/positions`

### Action: PM positions

- `GET /api/v1/agent-logs/pm/{pm_id}/positions`

### Action: PM position symbols

- `GET /api/v1/agent-logs/pm/{pm_id}/positions/symbols`

### Action: Position logs

- `GET /api/v1/agent-logs/position/logs` (requires `pm_id` and `position_id` as query params)

### Action: PnL summary

- `GET /api/v1/agent-logs/pnl/summary`

### Action: PnL orders

- `GET /api/v1/agent-logs/pnl/orders`

## Curl templates (copy-paste)

Normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Helper:

- `AUTH=(-H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json")`

Example (PM logs, safe default):

- `curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pm/logs?page=1&page_size=100"`

Example (PnL summary, safe default):

- `curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pnl/summary?page=1&page_size=100&bucket=day"`

Example (PnL orders for a symbol):

- `curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pnl/orders?page=1&page_size=100&symbol=$SYMBOL"`
