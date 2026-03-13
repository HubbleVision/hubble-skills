---
name: hubble_credits
description: Query credits balance and credit-related history from Hubble Market Server using an API key.
---

# Hubble Credits Skill

Version: v0.1.0

## When to use

Use this skill when the user asks about:

- Current credits balance
- Credits transactions history
- Deposits records

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Use `bash` tool with `curl` only.
- Use `--fail-with-body` and surface non-2xx responses to the user.

## Tools

Use the `bash` tool to call the API.

### Action: Get credits balance

Call:

- `GET /api/v1/credits/balance`

Use:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/credits/balance"`

### Action: List credits transactions

Call:

- `GET /api/v1/credits/transactions`

If the user provides a time range, pass it via query params if supported by the API; otherwise request the default list and summarize.

### Action: List deposits

Call:

- `GET /api/v1/credits/deposits`

## Curl template (copy-paste)

Always normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Then call endpoint with:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/<path>"`
