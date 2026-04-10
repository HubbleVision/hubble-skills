---
name: hubble_agents
description: Use when the user asks to list, view, create, update, or delete agents (PM agents or generic agents) on the Hubble Market API.
---

# Hubble Agents Skill

Version: v0.2.1

## When to use

Use this skill when the user asks about:

- Listing PM agents
- Viewing an agent's details
- Creating a PM agent
- Updating a PM agent
- Deleting an agent

## Requirements

Read from environment:

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY` — must start with `hb_sk_`

## Safety rules

- **Never print `HUBBLE_API_KEY`**.
- Validate `agent_id` format before use: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
- For all write actions (`POST`/`PUT`/`PATCH`/`DELETE`), summarize the action and wait for explicit user confirmation.

## Setup

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
# Validate agent_id
[[ ! "$AGENT_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] && echo "Invalid agent_id" && exit 2
```

---

## PM Agent Routes

PM agents are trading agents managed by Cloudflare Worker. Primary agent type for users.

### List PM agents

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/pm"
```

Optional query params: `limit`, `offset`, `search`.

Summarize: `id`, `name`, `created_at`, `agent_type`, status fields if present.

---

### Create PM agent — requires confirmation

Required fields: `name`, `exchange` (e.g. `weex`/`aster`/`mock`), `exchange_auth_type` (e.g. `api_key`/`web3`), `exchange_keys` (dict).

Optional: `description`, `symbols`, `risk_limit` (0-1), `interval_ms`, `auto_start_scheduler`, `llm_provider_id`, `llm_model`, `system_prompt`, `risk_config`, `research_agent_ids`.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/agents/pm" \
  -d "$BODY"
```

Errors: `409` = symbol conflict on same exchange (report conflicting agents); `502` = CF Worker upstream error.

---

### Update PM agent — requires confirmation

Not updatable: `exchange`, `exchange_auth_type`, `exchange_keys`.

Updatable: `name`, `description`, `symbols`, `risk_limit`, `interval_ms`, `system_prompt`, `risk_config`, `llm_provider_id`, `llm_model`, `research_agent_ids`.

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/pm/$AGENT_ID" \
  -d "$BODY"
```

---

## Generic Agent Routes

### Get agent

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  "$BASE/api/v1/agents/$AGENT_ID"
```

Note: public agents do not require authentication; unpublished agents require ownership.

---

### Update agent (generic) — requires confirmation

```bash
# Full update
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PUT \
  "$BASE/api/v1/agents/$AGENT_ID" \
  -d "$BODY"

# Partial update
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X PATCH \
  "$BASE/api/v1/agents/$AGENT_ID" \
  -d "$BODY"
```

---

### Delete agent — requires confirmation

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -X DELETE \
  "$BASE/api/v1/agents/$AGENT_ID"
```

---

## Error reference

| Code | Meaning |
|------|---------|
| `401` | API key missing/invalid/expired. Ask user to rotate key. |
| `403` | Not owner or no permission. |
| `404` | Agent not found. Verify `agent_id`. |
| `409` | Symbol conflict for PM agents. Report conflicting agents/symbols. |
| `5xx` | Server error. Retry once; if still failing, report body. |
