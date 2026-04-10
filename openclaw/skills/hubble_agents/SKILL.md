---
name: hubble_agents
description: Manage agents (PM agents and generic agents) on Hubble Market Server using an API key.
---

# Hubble Agents Skill

Version: v0.2.0

## When to use

Use this skill when the user asks about:

- Listing PM agents
- Viewing an agent's details
- Creating a PM agent
- Updating a PM agent
- Deleting an agent

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Treat `agent_id` as untrusted input. Validate it before calling the API.
- For write actions (`POST`/`PUT`/`PATCH`/`DELETE`), repeat the action summary and wait for explicit user confirmation before calling the API.
- Do not accept arbitrary JSON from the user. Ask for the minimal fields required by the endpoint.
- Validation rules:
  - `agent_id` must be UUID-like: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`

## Tools

Use the `bash` tool to call the API.

## PM Agent Routes

PM agents are trading agents managed by CF Worker. These are the primary agent type for users.

### Action: List PM agents

Call:

- `GET /api/v1/agents/pm`

Summarize key fields: `id`, `name`, `created_at`, `agent_type`, status fields if present.

Supports optional query params: `limit`, `offset`, `search`.

### Action: Create PM agent

Call:

- `POST /api/v1/agents/pm`

Before calling:

- Ask for required fields: `name`, `exchange` (e.g. `weex`/`aster`/`mock`), `exchange_auth_type` (e.g. `api_key`/`web3`), `exchange_keys` (dict with API credentials).
- Optional fields: `description`, `symbols` (list of trading symbols), `risk_limit` (0-1), `interval_ms`, `auto_start_scheduler`, `llm_provider_id`, `llm_model`, `system_prompt`, `risk_config`, `research_agent_ids`.
- Show a brief summary of the request body and ask for confirmation.

Error codes:
- `409`: Symbol conflict with an existing PM agent on the same exchange.
- `502`: CF Worker upstream error.

### Action: Update PM agent

Call:

- `PUT /api/v1/agents/pm/{agent_id}`

Before calling:

- Validate `agent_id` format.
- Note: `exchange`, `exchange_auth_type`, and `exchange_keys` are **not updatable**.
- Updatable fields: `name`, `description`, `symbols`, `risk_limit`, `interval_ms`, `system_prompt`, `risk_config`, `llm_provider_id`, `llm_model`, `research_agent_ids`.
- Summarize intended changes and ask for confirmation.

## Generic Agent Routes

### Action: Get agent

Call:

- `GET /api/v1/agents/{agent_id}`

Before calling:

- Validate `agent_id` format.

Note: Public agents do not require authentication. Unpublished agents require ownership.

### Action: Update agent (generic)

Call:

- `PUT /api/v1/agents/{agent_id}` (full update)
- `PATCH /api/v1/agents/{agent_id}` (partial update)

Before calling:

- Validate `agent_id` format.
- Summarize intended changes and ask for confirmation.

### Action: Delete agent

Call:

- `DELETE /api/v1/agents/{agent_id}`

Before calling:

- Validate `agent_id` format.
- Ask for confirmation.

## Error handling (summary)

- `401`: API key missing/invalid/expired/disabled. Ask user to rotate key.
- `403`: Authenticated but not allowed (not owner / permission). Ask user to check agent ownership.
- `404`: Agent not found. Ask user to verify `agent_id`.
- `409`: Conflict (symbol conflict for PM agents). Report the conflicting agents and symbols.
- `5xx`: Server error. Retry once with backoff; if still failing, stop and report response body.

## Curl templates (copy-paste)

Normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Validate agent_id:

- `if [[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then echo "Invalid agent_id"; exit 2; fi`

List PM agents:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents/pm"`

Get agent:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents/$AGENT_ID"`

Create PM agent:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm" \
  -d "$BODY"`

Update PM agent:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/pm/$AGENT_ID" \
  -d "$BODY"`

Update generic agent (PATCH):

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PATCH \
  "$BASE/api/v1/agents/$AGENT_ID" \
  -d "$BODY"`

Delete:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X DELETE \
  "$BASE/api/v1/agents/$AGENT_ID"`
