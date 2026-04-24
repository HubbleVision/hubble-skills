---
name: hubble_runs
description: Use when the user asks to invoke an already-existing Hubble agent via the x402 pay-per-execution flow — creating a run, polling or checking a specific run_id's status, or listing recent runs for an agent_id. NOT for creating, deploying, or managing an agent itself; "跑/部署 a new agent" goes to hubble_agents.
---

# Hubble Runs Skill

Version: v0.2.0

## When to use

Use this skill when the user asks about:

- Running an agent
- Checking run status
- Listing recent runs

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Treat `agent_id` and `run_id` as untrusted input. Validate them before calling the API.
- Validation rules:
  - `agent_id` must be UUID-like: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
  - `run_id`: treat as opaque; prefer UUID-like validation if it matches that format.
- For `POST /runs`, repeat the action summary and wait for explicit user confirmation before calling the API.

## Payment / x402

Paid agents require a two-step flow:

1. **First call** (no `X-PAYMENT` header): server creates a run record and returns **HTTP 402** with payment requirements (`payment_requirements`, `agent_run_id`, `payment_id`).
2. **Second call** (with `X-PAYMENT` header): server verifies payment and triggers execution, returns HTTP 202.

If the user asks to run a paid agent, explain the 402 flow. This skill does not automate the payment process itself—if the API returns 402, stop and report the payment requirements to the user.

## Run response fields

A run response includes:

- `id`, `agent_id`, `requester_id`
- `status`: run execution status (e.g. `pending`, `running`, `succeeded`, `failed`)
- `task_state`: A2A task state (e.g. `created`, `accepted`, `executing`, `succeeded`, `failed`)
- `payment_status`: payment state (e.g. `none`, `required`, `pending`, `confirmed`, `failed`)
- `input_payload`, `output_payload`, `error_reason`
- `created_at`, `started_at`, `finished_at`
- `tx_hash`, `trans_url`: payment transaction hash and block explorer URL (if applicable)
- `external_trace_id`, `bridge_latency_ms`: external agent trace info (if applicable)
- `events`: list of run events (detail response only)

## Tools

Use the `bash` tool to call the API.

### Action: Create run

Call:

- `POST /api/v1/agents/{agent_id}/runs`

Before calling:

- Validate `agent_id` format.
- Ask the user for the minimal required input fields.
- Summarize request body and ask for confirmation.

### Action: Get run

Call:

- `GET /api/v1/agents/{agent_id}/runs/{run_id}`

Before calling:

- Validate `agent_id` format.

### Action: List runs

Call:

- `GET /api/v1/agents/{agent_id}/runs`

Query params (optional):

- `limit` (default 10)
- `offset` (default 0)

Before calling:

- Validate `agent_id` format.

## Curl templates (copy-paste)

Normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Validate agent_id:

- `if [[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then echo "Invalid agent_id"; exit 2; fi`

Create:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/$AGENT_ID/runs" \
  -d "$BODY"`

Get:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents/$AGENT_ID/runs/$RUN_ID"`

List:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents/$AGENT_ID/runs"`
