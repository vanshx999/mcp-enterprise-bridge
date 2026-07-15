#!/usr/bin/env bash
# Quick-reference curl commands for MCP Enterprise Bridge
# Usage: source this file, then run any function
# BASE="${BASE:-https://localhost}"

export BASE="${BASE:-https://localhost}"

# ---- Auth ----
login() {
  TOKEN=$(curl -sk -X POST "$BASE/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@mcpbridge.io","password":"admin123"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
  echo "TOKEN=$TOKEN"
}

login_approver() {
  APPROVER_TOKEN=$(curl -sk -X POST "$BASE/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"approver@mcpbridge.io","password":"approver123"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
  echo "APPROVER_TOKEN=$APPROVER_TOKEN"
}

# ---- Agent Keys ----
create_key() {
  curl -sk -X POST "$BASE/api/agent/keys" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"agent_id":"default-agent","label":"my-agent"}'
}

list_keys() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/agent/keys"
}

rotate_key() {
  local id=$1
  curl -sk -X POST "$BASE/api/agent/keys/$id/rotate" \
    -H "Authorization: Bearer $TOKEN"
}

revoke_key() {
  local id=$1
  curl -sk -X DELETE "$BASE/api/agent/keys/$id" \
    -H "Authorization: Bearer $TOKEN"
}

# ---- Agent Queries ----
query_direct() {
  curl -sk -X POST "$BASE/api/agent/query" \
    -H "X-Agent-Key: $AGENT_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"message":"hello, what can you do?","agent_id":"default-agent"}'
}

query_sql() {
  curl -sk -X POST "$BASE/api/agent/query" \
    -H "X-Agent-Key: $AGENT_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"message":"execute_query SELECT 1 as test","agent_id":"default-agent"}'
}

query_medium() {
  curl -sk -X POST "$BASE/api/agent/query" \
    -H "X-Agent-Key: $AGENT_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"message":"execute_query SELECT * FROM information_schema.tables LIMIT 5","agent_id":"default-agent","db_name":"primary"}'
}

continue_query() {
  local session_id=$1
  curl -sk -X POST "$BASE/api/agent/query/$session_id/continue" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json'
}

get_session() {
  local session_id=$1
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/agent/session/$session_id"
}

# ---- Approvals ----
pending_approvals() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approvals/pending"
}

approve_request() {
  local id=$1
  curl -sk -X POST "$BASE/api/approvals/$id/approve" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"note":"Approved"}'
}

deny_request() {
  local id=$1
  curl -sk -X POST "$BASE/api/approvals/$id/deny" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"note":"Not authorized"}'
}

approval_history() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approvals/history?limit=10"
}

# ---- Permissions ----
list_permissions() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/permissions"
}

create_permission() {
  curl -sk -X POST "$BASE/api/permissions" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"agent_id":"default-agent","tool_name":"execute_query","resource_pattern":"*","risk_level":"low","auto_approve":true}'
}

# ---- Audit ----
audit_logs() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/audit/logs?limit=10"
}

audit_session() {
  local session_id=$1
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/audit/logs/$session_id"
}

export_csv() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/audit/export/csv"
}

export_json() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/audit/export/json"
}

# ---- Analytics ----
analytics_summary() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/analytics/summary"
}

analytics_usage() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/analytics/usage"
}

# ---- Databases ----
register_db() {
  curl -sk -X POST "$BASE/api/databases" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"name":"production","connection_url":"postgresql://user:pass@host:5432/db","db_type":"postgresql"}'
}

list_databases() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/databases"
}

test_db() {
  local id=$1
  curl -sk -X POST "$BASE/api/databases/$id/test" \
    -H "Authorization: Bearer $TOKEN"
}

delete_db() {
  local id=$1
  curl -sk -X DELETE "$BASE/api/databases/$id" \
    -H "Authorization: Bearer $TOKEN"
}

# ---- Approval Templates ----
create_template() {
  curl -sk -X POST "$BASE/api/approval-templates" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"name":"read-only-select","description":"Safe read-only queries","tool_name":"execute_query","resource_pattern":"*","risk_level":"low","auto_approve":true}'
}

list_templates() {
  curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approval-templates"
}

apply_template() {
  local template_id=$1 agent_id=$2
  curl -sk -X POST "$BASE/api/approval-templates/$template_id/apply?agent_id=$agent_id" \
    -H "Authorization: Bearer $TOKEN"
}

delete_template() {
  local id=$1
  curl -sk -X DELETE "$BASE/api/approval-templates/$id" \
    -H "Authorization: Bearer $TOKEN"
}

# ---- System ----
health() {
  curl -sk "$BASE/api/health"
}

metrics() {
  curl -sk "$BASE/api/metrics"
}

audit_cleanup() {
  curl -sk -X POST "$BASE/api/audit/cleanup?dry_run=true" \
    -H "Authorization: Bearer $TOKEN"
}

# ---- Full E2E Flow ----
e2e() {
  echo "=== Full E2E Test ==="
  login
  echo ""

  echo "--- Health ---"
  health
  echo ""

  echo "--- Create agent key ---"
  local kr; kr=$(create_key)
  echo "$kr" | python3 -m json.tool
  local ak; ak=$(echo "$kr" | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])")
  echo ""

  echo "--- Direct query ---"
  curl -sk -X POST "$BASE/api/agent/query" \
    -H "X-Agent-Key: $ak" \
    -H 'Content-Type: application/json' \
    -d '{"message":"hello","agent_id":"default-agent"}' | python3 -m json.tool
  echo ""

  echo "--- Create low-risk auto-approve permission ---"
  create_permission
  echo ""

  echo "--- Auto-approved query ---"
  curl -sk -X POST "$BASE/api/agent/query" \
    -H "X-Agent-Key: $ak" \
    -H 'Content-Type: application/json' \
    -d '{"message":"execute_query SELECT 1 as test","agent_id":"default-agent"}' | python3 -m json.tool
  echo ""

  echo "--- Medium-risk (pending approval) query ---"
  # Override with medium risk, no auto-approve
  curl -sk -X POST "$BASE/api/permissions" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"agent_id":"default-agent","tool_name":"execute_query","resource_pattern":"*","risk_level":"medium","auto_approve":false}' > /dev/null 2>&1
  local qr; qr=$(curl -sk -X POST "$BASE/api/agent/query" \
    -H "X-Agent-Key: $ak" \
    -H 'Content-Type: application/json' \
    -d '{"message":"execute_query SELECT current_database()","agent_id":"default-agent"}')
  echo "$qr" | python3 -m json.tool
  local sid; sid=$(echo "$qr" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
  echo ""

  echo "--- Approve & continue ---"
  local pid; pid=$(curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/approvals/pending" | python3 -c "
import sys,json
data=json.load(sys.stdin)
print(data[0]['id'] if data else '')")
  if [ -n "$pid" ]; then
    curl -sk -X POST "$BASE/api/approvals/$pid/approve" \
      -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"note":"ok"}' > /dev/null 2>&1
    curl -sk -X POST "$BASE/api/agent/query/$sid/continue" \
      -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
  fi
  echo ""

  echo "--- Analytics ---"
  analytics_summary | python3 -m json.tool
  echo ""

  echo "=== E2E Complete ==="
}

# Print usage
if [ $# -eq 0 ]; then
  echo "MCP Bridge Curl Commands"
  echo "========================"
  echo "Usage: source $0, then run any function"
  echo ""
  echo "  login              - Get admin JWT token"
  echo "  login_approver     - Get approver JWT token"
  echo "  health             - Health check"
  echo "  metrics            - Prometheus metrics"
  echo "  create_key         - Create agent API key"
  echo "  list_keys          - List agent keys"
  echo "  rotate_key <id>    - Rotate agent key"
  echo "  revoke_key <id>    - Revoke agent key"
  echo "  query_direct       - Direct response query"
  echo "  query_sql          - Auto-approved SQL query"
  echo "  query_medium       - Medium-risk SQL (requires approval)"
  echo "  continue_query <session> - Resume after approval"
  echo "  get_session <id>   - Get session state"
  echo "  pending_approvals  - List pending approvals"
  echo "  approve_request <id>"
  echo "  deny_request <id>"
  echo "  list_permissions   - List permissions"
  echo "  create_permission  - Create low-risk auto-approve"
  echo "  audit_logs         - View audit log"
  echo "  analytics_summary  - View analytics"
  echo "  register_db        - Register a database"
  echo "  list_databases     - List databases"
  echo "  test_db <id>       - Test database connection"
  echo "  create_template    - Create approval template"
  echo "  list_templates     - List templates"
  echo "  apply_template <tid> <agent_id>"
  echo "  e2e                - Run full end-to-end test"
fi
