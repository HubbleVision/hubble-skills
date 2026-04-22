---
name: hubble_auth
description: Use when the user asks about logging into Hubble Market, obtaining an access token, sending an email verification code, verifying email code login, or checking their own user profile via the Hubble Market API.
---

# Hubble Auth Skill

Version: v0.4.0

## When to use

Use this skill when the user asks about:

- Logging in via wallet signature (challenge/login flow)
- Logging in via email verification code
- Sending an email verification code
- Viewing current user profile (`/auth/me`)

## Requirements

Read from environment:

- `HUBBLE_API_BASE_URL` — default: `https://market-v2.bedev.hubble-rpc.xyz`

Auth endpoints do **not** require `HUBBLE_API_KEY`. They return an `access_token` (JWT) on success, which can then be used as a Bearer token for other API calls.

## Safety rules

- **Never print tokens or keys** in any response or tool output.
- For all write actions (`POST`), summarize the request and wait for explicit user confirmation before calling the API.

## Setup

```bash
BASE="${HUBBLE_API_BASE_URL%/}"
```

---

## Email Code Login (新)

两步流程：先发送验证码，再验证登录。

### Step 1 — 发送邮箱验证码

```bash
curl -sS --fail-with-body \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/auth/email-code/send" \
  -d '{"email": "<user_email>"}'
```

响应字段：`expires_in`（验证码有效期，秒）、`cooldown_seconds`（再次发送的冷却时间，秒）。

> 注意：新用户首次通过邮箱注册需要邀请码（`invite_code`），在 Step 2 中传入。

---

### Step 2 — 验证邮箱验证码并登录

```bash
curl -sS --fail-with-body \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/auth/email-code/verify" \
  -d '{"email": "<user_email>", "code": "<6_digit_code>", "invite_code": "<invite_code_or_null>"}'
```

- `invite_code`：仅首次注册时必填，已有账号可省略（传 `null` 或不传）。
- 成功响应与钱包登录相同，见下方 `AuthLoginResponse`。

错误响应格式（非 2xx）：

```json
{ "code": "<error_code>", "message": "<human_readable>" }
```

常见 `code` 值：`invalid_code`、`code_expired`、`too_many_attempts`、`rate_limited`、`invite_code_required`、`invite_code_invalid`。

---

## Wallet Login

### Step 1 — 获取签名挑战

```bash
curl -sS --fail-with-body \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/auth/challenge" \
  -d '{"wallet_address": "<0x_address>", "chain_id": <chain_id>}'
```

响应字段：`nonce`、`expires_in`（秒）、`message`（待签名内容）。

支持的 `chain_id`：`1`（Ethereum）、`8453`（Base）、`137`（Polygon）、`56`（BSC）。

---

### Step 2 — 提交签名登录

```bash
curl -sS --fail-with-body \
  -H "Content-Type: application/json" \
  -X POST \
  "$BASE/api/v1/auth/login" \
  -d '{"wallet_address": "<0x_address>", "chain_id": <chain_id>, "signature": "<hex_sig>", "nonce": "<nonce>"}'
```

---

## AuthLoginResponse（两种登录方式共用）

| 字段 | 说明 |
|---|---|
| `access_token` | JWT access token，用于后续 API 调用的 Bearer token |
| `token_type` | 固定为 `"bearer"` |
| `expires_in` | Token 有效期（秒） |
| `user_id` | 用户 UUID |
| `avatar_url` | 用户头像 URL（可为 null） |

---

## 查看当前用户信息

需要有效 JWT 或 API Key：

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE/api/v1/auth/me"
```

响应字段：`id`、`wallet_address`、`chain_id`、`display_name`、`email`、`avatar_url`、`created_at`。
