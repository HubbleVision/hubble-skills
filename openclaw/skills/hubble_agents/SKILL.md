---
name: hubble_agents
description: Read agent list and agent details from Hubble Market Server using an API key.
---

# Hubble Agents Skill

Version: v0.1.0

## When to use

Use this skill when the user asks about:

- Listing agents
- Viewing an agent's details
- Creating an agent
- Updating an agent
- Deleting an agent

Milestone 2+ scope: read-write (`list` / `get` / `create` / `update` / `delete`).

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

### Action: List agents

Call:

- `GET /api/v1/agents`

Default behavior:

- Request the list and summarize key fields (`id`, `name`, `created_at`, `owner`, status fields if present).

### Action: Get agent

Call:

- `GET /api/v1/agents/{agent_id}`

Before calling:

- Validate `agent_id` format.

### Action: Create agent

Call:

- `POST /api/v1/agents`

Before calling:

- Ask the user for the minimal required fields.
- Show a brief summary of the request body and ask for confirmation.

### Action: Update agent

Call:

- `PUT /api/v1/agents/{agent_id}`
- `PATCH /api/v1/agents/{agent_id}`

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
- `409`: Conflict (if applicable). Ask user to re-fetch state and retry.
- `5xx`: Server error. Retry once with backoff; if still failing, stop and report response body.

## Curl templates (copy-paste)

Normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

List:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents"`

Get (with validation):

- `if [[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then echo "Invalid agent_id"; exit 2; fi`
- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/agents/$AGENT_ID"`

Create:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents" \
  -d "$BODY"`

Update (PUT/PATCH):

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/$AGENT_ID" \
  -d "$BODY"`
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
