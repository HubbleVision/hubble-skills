---
name: hubble_credits
description: Use when the user asks about Hubble credits balance, transaction history, deposit records, recharge packages, or wants to create a recharge order via the Hubble Market API.
---

# Hubble Credits Skill

Version: v0.4.0

## When to use

Use this skill when the user asks about:

- Current credits balance
- Credits transactions history
- Deposits records
- Creating a recharge (deposit) order
- Listing available recharge packages
- Creating a deposit by selecting a package

## Requirements

Read from environment (never ask user to paste keys):

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`
- `HUBBLE_API_KEY` — must start with `hb_sk_`

## Safety rules

- **Never print `HUBBLE_API_KEY`** in any response or tool output.
- Use the Bash tool with `curl` only.
- Always pass `--fail-with-body`; surface non-2xx bodies to the user verbatim.
- For write actions (`POST`), summarize the request and wait for explicit user confirmation before calling the API.

## Setup (one-liner for Bash tool)

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
```

## Actions

### Get credits balance

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/balance"
```

Response fields: `user_id`, `balance` (float).

---

### List credits transactions

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/transactions?limit=50&offset=0"
```

Query params: `limit` (default 50, max 200), `offset` (default 0).

Response fields per item: `tx_id`, `user_id`, `tx_type` (e.g. `DEPOSIT`/`CONSUME`), `amount`, `balance_after`, `idempotency_key`, `source`, `created_at`.

---

### List deposits

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/deposits?limit=50&offset=0"
```

Query params: `limit` (default 50, max 200), `offset` (default 0).

Response fields per item: `deposit_id`, `user_id`, `credits`, `amount_usd`, `currency`, `client_reference`, `status` (e.g. `PENDING`/`PAID`/`EXPIRED`), `infini_order_id`, `checkout_url`, `paid_at`, `created_at`.

---

### Create deposit (recharge) — requires confirmation

Ask user for the number of credits to recharge, then confirm before calling:

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/credits/deposits" \
  -d '{"credits": <positive_integer>}'
```

Response fields: `deposit_id`, `client_reference`, `credits`, `amount_usd`, `currency`, `infini_order_id`, `checkout_url` (redirect to Infini checkout page).

---

### List recharge packages

列出平台提供的充值套餐，供用户选择后按套餐充值。

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE/api/v1/credits/packages"
```

Response fields per item: `package_id`（套餐 slug，传给按套餐充值接口）、`credits`、`amount_usd`、`currency`、`label`（展示名，如 `"Starter"`）、`is_default`（是否默认推荐套餐）、`sort_order`（展示排序，越小越靠前）。

---

### Create deposit by package — requires confirmation

先调 `GET /credits/packages` 列出可用套餐，让用户选择后再执行。确认时展示：套餐名（`label`）、`credits`、`amount_usd`。

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $HUBBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/credits/deposits/by-package" \
  -d '{"package_id": "<package_slug>"}'
```

Response fields 与 `POST /deposits` 相同：`deposit_id`, `client_reference`, `credits`, `amount_usd`, `currency`, `infini_order_id`, `checkout_url`。
