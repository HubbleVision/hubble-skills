---
name: hubble_logs
description: Use when the user asks about PM agent logs, research logs, orders, positions, order history, position recovery, or PnL data from the Hubble Market API.
---

# Hubble Logs Skill

Version: v0.2.1

## When to use

Use this skill when the user asks about:

- PM logs (decision logs)
- Research logs
- Orders (list, single, history)
- Positions / PM positions
- Position recovery logs
- PnL summary and PnL order details

## Requirements

Read from environment:

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY` — must start with `hb_sk_`

## Safety rules

- **Never print `HUBBLE_API_KEY`**.
- Always set `page_size` explicitly (default 100, max 200 unless user insists).
- Prefer narrow time windows — ask user for `start`/`end` if not provided.

## Setup

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
AUTH=(-H "Authorization: Bearer $HUBBLE_API_KEY" -H "Content-Type: application/json")
```

---

## Common query params

Most endpoints support: `start`, `end` (RFC3339 or unix ms), `pm_id`, `round_id`, `token`, `page`, `page_size`.

---

## Actions

### PM logs

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pm/logs?page=1&page_size=100"
```

Extra params: `level` (`info` / `warn` / `error`).

---

### Research logs

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/research/logs?page=1&page_size=100"
```

Extra params: `level` (`info` / `warn` / `error`).

---

### Orders (list)

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/orders?page=1&page_size=100"
```

Extra params: `status`, `event_type`.

---

### Order (single)

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/orders/$ORDER_ID"
```

---

### Order history

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/order/history?page=1&page_size=100"
```

Extra params: `order_id`, `position_id`, `symbol`, `status`, `action_type`.

---

### Positions

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/positions?page=1&page_size=100"
```

Extra params: `status`, `event_type`.

---

### PM positions

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pm/$PM_ID/positions?page=1&page_size=100"
```

Extra params: `status`, `event_type`.

---

### PM position symbols

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pm/$PM_ID/positions/symbols?page=1&page_size=100"
```

Extra params: `status` (e.g. `open` / `closed`).

---

### Position logs

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/position/logs?pm_id=$PM_ID&position_id=$POSITION_ID&page=1&page_size=100"
```

Both `pm_id` and `position_id` are required.

---

### Position recovery

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/position/recovery?page=1&page_size=100"
```

Extra params: `pm_id`, `round_id`, `token`.

---

### PnL summary

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pnl/summary?page=1&page_size=100&bucket=day"
```

Extra params: `symbol`, `position_id`, `action_types` (comma-separated, default `close,decrease`), `bucket` (`hour` / `day`).

---

### PnL orders

```bash
curl -sS --fail-with-body "${AUTH[@]}" \
  "$BASE/api/v1/agent-logs/pnl/orders?page=1&page_size=100"
```

Extra params: `symbol`, `position_id`, `action_types`.
