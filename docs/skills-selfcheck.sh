#!/usr/bin/env bash
# hubble-skills 端到端自检脚本（只调用只读接口，绝不触发付费/写操作）
#
# 用法：
#   export HUBBLE_API_BASE_URL="https://market-v2.bedev.hubble-rpc.xyz"
#   export HUBBLE_API_KEY="hb_sk_...你的 key..."
#   bash docs/skills-selfcheck.sh
#
# 输出：每个接口一行 HTTP 状态 + 简短响应片段。完整响应存到 /tmp/hubble-selfcheck/*.json。

set -u

: "${HUBBLE_API_BASE_URL:?HUBBLE_API_BASE_URL is required}"
: "${HUBBLE_API_KEY:?HUBBLE_API_KEY is required}"

case "$HUBBLE_API_KEY" in
  hb_sk_*) ;;
  *) echo "HUBBLE_API_KEY must start with hb_sk_"; exit 2 ;;
esac

BASE="${HUBBLE_API_BASE_URL%/}"
OUT="/tmp/hubble-selfcheck"
mkdir -p "$OUT"

pass=0
fail=0

check() {
  local name="$1"; shift
  local url="$1"; shift
  local out_file="$OUT/$(echo "$name" | tr ' /' '__').json"
  local http
  http=$(curl -sS -o "$out_file" -w "%{http_code}" \
    -H "Authorization: Bearer $HUBBLE_API_KEY" \
    -H "Content-Type: application/json" \
    "$url" 2>/dev/null || echo "000")
  if [[ "$http" =~ ^2 ]]; then
    pass=$((pass+1))
    printf "  \033[32m✓\033[0m %-40s HTTP %s  (bytes: %s)\n" \
      "$name" "$http" "$(wc -c < "$out_file")"
  else
    fail=$((fail+1))
    printf "  \033[31m✗\033[0m %-40s HTTP %s  body: %s\n" \
      "$name" "$http" "$(head -c 200 "$out_file" | tr -d '\n')"
  fi
}

echo
echo "== hubble_credits =="
check "credits: balance"       "$BASE/api/v1/credits/balance"
check "credits: transactions"  "$BASE/api/v1/credits/transactions?limit=5&offset=0"
check "credits: deposits"      "$BASE/api/v1/credits/deposits?limit=5&offset=0"
check "credits: packages"      "$BASE/api/v1/credits/packages"

echo
echo "== hubble_agents =="
check "agents: list PM"        "$BASE/api/v1/agents/pm?limit=5&offset=0"
check "agents: list UR"        "$BASE/api/v1/agents/user-research?page=1&page_size=5"
check "agents: data-sources"   "$BASE/api/v1/agents/user-research/data-sources"
check "config: indicator-tpls" "$BASE/api/v1/config/indicator-templates"

echo
echo "== hubble_logs =="
check "logs: pm logs"          "$BASE/api/v1/agent-logs/pm/logs?page=1&page_size=5"
check "logs: research logs"    "$BASE/api/v1/agent-logs/research/logs?page=1&page_size=5"
check "logs: orders"           "$BASE/api/v1/agent-logs/orders?page=1&page_size=5"
check "logs: positions"        "$BASE/api/v1/agent-logs/positions?page=1&page_size=5"
check "logs: order history"    "$BASE/api/v1/agent-logs/order/history?page=1&page_size=5"
check "logs: pnl summary"      "$BASE/api/v1/agent-logs/pnl/summary?page=1&page_size=5&bucket=day"

echo
echo "== summary =="
echo "  pass: $pass"
echo "  fail: $fail"
echo "  raw:  $OUT"
echo

if [[ $fail -gt 0 ]]; then
  exit 1
fi
