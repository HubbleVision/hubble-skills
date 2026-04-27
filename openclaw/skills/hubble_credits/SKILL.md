---
name: hubble_credits
description: Query Hubble credits balance, transactions, deposits; list recharge packages (optional bonus_percent for display); create a raw-credits deposit or a deposit by package slug (by-package) on Market Server using an API key.
---

# Hubble Credits Skill

Version: v0.5.2

## When to use

Use this skill when the user asks about:

- Current credits balance
- Credits transactions history
- Deposits records
- Creating a recharge (deposit) order (raw `credits` or by package)
- Listing recharge packages
- Depositing by package (`package_id` from the packages list)

## Requirements

- `HUBBLE_API_BASE_URL` (default: `https://market-v2.bedev.hubble-rpc.xyz`)
- `HUBBLE_API_KEY` (API key, must start with `hb_sk_`)

## Safety rules

- Never print `HUBBLE_API_KEY` in the output.
- Use `bash` tool with `curl` only.
- Use `--fail-with-body` and surface non-2xx responses to the user.
- For write actions (`POST`), summarize the request and wait for explicit user confirmation before calling the API.

## Package semantics (important)

- **`credits` on each package is the total amount credited** when that tier’s deposit is paid—not a pre-bonus base.
- **`bonus_percent`** (if present) is **UI/marketing only**; do not multiply `credits` by it for ordering or balance explanation.

## Tools

Use the `bash` tool to call the API.

### Action: Get credits balance

Call:

- `GET /api/v1/credits/balance`

Use:

- `curl -sS --fail-with-body -H "Authorization: Bearer $HUBBLE_API_KEY" "$BASE/api/v1/credits/balance"`

Response fields: `user_id`, `balance` (float, current credit balance).

### Action: List credits transactions

Call:

- `GET /api/v1/credits/transactions`

Query params (optional):

- `limit` (default 50, max 200)
- `offset` (default 0)

Response fields per item: `tx_id`, `user_id`, `tx_type` (e.g. `DEPOSIT`/`CONSUME`), `amount`, `balance_after`, `idempotency_key`, `source`, `created_at`.

### Action: List deposits

Call:

- `GET /api/v1/credits/deposits`

Query params (optional):

- `limit` (default 50, max 200)
- `offset` (default 0)

Response fields per item: `deposit_id`, `user_id`, `credits`, `amount_usd`, `currency`, `client_reference`, `status` (e.g. `PENDING`/`PAID`/`EXPIRED`), `infini_order_id`, `checkout_url`, `paid_at`, `created_at`.

### Action: List recharge packages

Call:

- `GET /api/v1/credits/packages`

Response fields per item: `package_id`, `credits` (total credited on paid deposit), `amount_usd`, `currency`, `label`, `is_default`, `sort_order`, `bonus_percent` (optional, display-only).

### Action: Create deposit by package

Call:

- `POST /api/v1/credits/deposits/by-package`

Request body:

```json
{"package_id": "<slug_from_packages>"}
```

Before calling: list packages, let the user pick a tier; confirm with `label`, `credits`, `amount_usd` (and optionally note `bonus_percent` is not applied again).

Response fields: same as raw deposit—`deposit_id`, `client_reference`, `credits`, `amount_usd`, `currency`, `infini_order_id`, `checkout_url`. `credits` matches the tier’s total (see Package semantics).

### Action: Create deposit (recharge) — raw credits

Call:

- `POST /api/v1/credits/deposits`

Request body:

```json
{"credits": <positive_integer>}
```

Before calling:

- Ask user for the number of credits to recharge.
- Summarize the request and wait for explicit confirmation.

Response fields: `deposit_id`, `client_reference`, `credits`, `amount_usd`, `currency`, `infini_order_id`, `checkout_url` (redirect URL to Infini checkout page).

## Curl template (copy-paste)

Always normalize base URL:

- `BASE="${HUBBLE_API_BASE_URL%/}"`

Read requests:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/<path>"`

Create deposit (raw):

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/credits/deposits" \
  -d '{"credits": <amount>}'`

Create deposit by package:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/credits/deposits/by-package" \
  -d '{"package_id": "<package_slug>"}'`

List packages:

- `curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/packages"`
