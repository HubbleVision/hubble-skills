---
name: hubble_runs
description: Create and query agent runs from Hubble Market Server using an API key (free-only; no x402 automation).
---

# Hubble Runs Skill

Version: v0.1.0

## When to use

Use this skill when the user asks about:

- Running an agent
- Checking run status
- Listing recent runs

This skill is intended for free agents only.

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Treat `agent_id` and `run_id` as untrusted input. Validate them before calling the API.
- Validation rules:
  - `agent_id` must be UUID-like: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
  - `run_id` should be treated as opaque; prefer UUID-like validation if it matches that format.
- For `POST /runs`, repeat the action summary and wait for explicit user confirmation before calling the API.

## Payment / x402

- This skill does not implement any x402/payment automation.
- If the API responds with a payment challenge or indicates x402 is required, stop and tell the user that payment is not supported in this skill.

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
