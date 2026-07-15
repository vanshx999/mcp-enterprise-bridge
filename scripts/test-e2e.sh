#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-https://localhost}"
TOKEN=""
AGENT_KEY=""

# -- Helper --
json() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

echo "=== 1. Health Check ==="
curl -sk "$BASE/api/health" | python3 -m json.tool

echo ""
echo "=== 2. Login as admin ==="
TOKEN=$(curl -sk -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@mcpbridge.io","password":"admin123"}' | json "['access_token']")
echo "TOKEN=${TOKEN:0:32}..."

echo ""
echo "=== 3. Login as approver ==="
APPROVER_TOKEN=$(curl -sk -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"approver@mcpbridge.io","password":"approver123"}' | json "['access_token']")
echo "APPROVER_TOKEN=${APPROVER_TOKEN:0:32}..."

echo ""
echo "=== 4. Create Agent Key ==="
KEY_RESP=$(curl -sk -X POST "$BASE/api/agent/keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"test-agent","label":"e2e-test"}')
AGENT_KEY=$(echo "$KEY_RESP" | json "['key']")
echo "AGENT_KEY=${AGENT_KEY:0:20}..."

echo ""
echo "=== 5. List Agent Keys ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/agent/keys" | python3 -m json.tool

echo ""
echo "=== 6. List Permissions ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/permissions" | python3 -m json.tool

echo ""
echo "=== 7. Agent Query — Direct (greeting) ==="
curl -sk -X POST "$BASE/api/agent/query" \
  -H "X-Agent-Key: $AGENT_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello, who are you?","agent_id":"test-agent"}' | python3 -m json.tool

echo ""
echo "=== 8. Agent Query — Auto-approved (SELECT) ==="
# First create a low-risk auto-approve permission
curl -sk -X POST "$BASE/api/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"test-agent","tool_name":"execute_query","resource_pattern":"*","risk_level":"low","auto_approve":true}'

echo ""
curl -sk -X POST "$BASE/api/agent/query" \
  -H "X-Agent-Key: $AGENT_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"message":"execute_query SELECT 1 as test","agent_id":"test-agent"}' | python3 -m json.tool

echo ""
echo "=== 9. Agent Query — Medium risk (requires approval) ==="
# Create medium-risk permission without auto-approve
curl -sk -X POST "$BASE/api/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"test-agent","tool_name":"execute_query","resource_pattern":"*","risk_level":"medium","auto_approve":false}'

echo ""
QUERY_RESP=$(curl -sk -X POST "$BASE/api/agent/query" \
  -H "X-Agent-Key: $AGENT_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"message":"execute_query SELECT * FROM information_schema.tables LIMIT 5","agent_id":"test-agent"}')
echo "$QUERY_RESP" | python3 -m json.tool
SESSION_ID=$(echo "$QUERY_RESP" | json "['session_id']")
echo "SESSION_ID=$SESSION_ID"

echo ""
echo "=== 10. List Pending Approvals ==="
PENDING=$(curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approvals/pending")
echo "$PENDING" | python3 -m json.tool
APPROVAL_ID=$(echo "$PENDING" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")
echo "APPROVAL_ID=$APPROVAL_ID"

echo ""
echo "=== 11. Approve the Request ==="
curl -sk -X POST "$BASE/api/approvals/$APPROVAL_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"note":"Looks good, approved"}'

echo ""
echo "=== 12. Continue the Query Session ==="
curl -sk -X POST "$BASE/api/agent/query/$SESSION_ID/continue" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' | python3 -m json.tool

echo ""
echo "=== 13. Get Session State ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/agent/session/$SESSION_ID" | python3 -m json.tool

echo ""
echo "=== 14. Test Deny Flow ==="
# Create another medium-risk query
Q2=$(curl -sk -X POST "$BASE/api/agent/query" \
  -H "X-Agent-Key: $AGENT_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"message":"execute_query SELECT current_database()","agent_id":"test-agent"}')
SID2=$(echo "$Q2" | json "['session_id']")
AID2=$(curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approvals/pending" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")
echo "Denying approval $AID2..."
curl -sk -X POST "$BASE/api/approvals/$AID2/deny" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"note":"Not authorized for this operation"}'
curl -sk -X POST "$BASE/api/agent/query/$SID2/continue" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 15. Audit Log ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/audit/logs?limit=5" | python3 -m json.tool

echo ""
echo "=== 16. Analytics Summary ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/analytics/summary" | python3 -m json.tool

echo ""
echo "=== 17. Prometheus Metrics ==="
curl -sk "$BASE/api/metrics" | head -20

echo ""
echo "=== 18. Approvals History ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approvals/history?limit=5" | python3 -m json.tool

echo ""
echo "=== 19. Register a Database ==="
curl -sk -X POST "$BASE/api/databases" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"test-db","connection_url":"postgresql://postgres:postgres@localhost:5432/mcp_bridge","db_type":"postgresql"}' | python3 -m json.tool

echo ""
echo "=== 20. List Databases ==="
curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/databases" | python3 -m json.tool

echo ""
echo "=== 21. Approval Templates ==="
curl -sk -X POST "$BASE/api/approval-templates" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"read-only","description":"Read-only SELECT access","tool_name":"execute_query","resource_pattern":"*","risk_level":"low","auto_approve":true}' | python3 -m json.tool

curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approval-templates" | python3 -m json.tool

echo ""
echo "=== 22. Key Rotation ==="
# Get first key ID
KEY_ID=$(curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/agent/keys" | python3 -c "
import sys,json
keys=json.load(sys.stdin)
active=[k for k in keys if k.get('is_active')]
print(active[0]['id'] if active else '')
")
if [ -n "$KEY_ID" ]; then
  echo "Rotating key $KEY_ID..."
  curl -sk -X POST "$BASE/api/agent/keys/$KEY_ID/rotate" \
    -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
fi

echo ""
echo "=== DONE ==="
