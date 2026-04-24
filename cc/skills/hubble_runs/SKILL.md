---
name: hubble_runs
description: Use when the user asks to invoke an already-existing Hubble agent via the x402 pay-per-execution flow — creating a run, polling or checking a specific run_id's status, or listing recent runs for an agent_id. NOT for creating, deploying, or managing an agent itself; "跑/部署 a new agent" goes to hubble_agents.
---

# Hubble Runs Skill

Version: v0.2.1

## When to use

Use this skill when the user asks about:

- Running an agent
- Checking run status or polling progress
- Listing recent runs

## Requirements

Read from environment:

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY` — must start with `hb_sk_`

## Safety rules

- **Never print `HUBBLE_API_KEY`**.
- Validate `agent_id` / `run_id` before use (UUID format).
- For `POST /runs`, summarize the action and wait for explicit user confirmation.

## Setup

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
[[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] && echo "Invalid agent_id" && exit 2
```

---

## Payment / x402

Paid agents use a two-step flow:

1. **First call** (no `X-PAYMENT` header) → server returns **HTTP 402** with `payment_requirements`, `agent_run_id`, `payment_id`.
2. **Second call** (with `X-PAYMENT` header) → server verifies payment, returns HTTP 202.

If the API returns 402, stop and report the payment requirements to the user. Do not automate the payment step.

---

## Run response fields

| Field | Description |
|-------|-------------|
| `status` | Execution status: `pending` / `running` / `succeeded` / `failed` |
| `task_state` | A2A state: `created` / `accepted` / `executing` / `succeeded` / `failed` |
| `payment_status` | `none` / `required` / `pending` / `confirmed` / `failed` |
| `tx_hash` / `trans_url` | Payment tx hash and block explorer URL (paid agents) |
| `external_trace_id` / `bridge_latency_ms` | External agent trace info |
| `events` | List of run events (detail response only) |

---

## Actions

### Create run — requires confirmation

Ask for required input fields, summarize, then confirm before calling:

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/$AGENT_ID/runs" \
  -d "$BODY"
```

---

### Get run (poll status)

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/$AGENT_ID/runs/$RUN_ID"
```

---

### List runs

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/$AGENT_ID/runs?limit=10&offset=0"
```

Query params: `limit` (default 10), `offset` (default 0).
