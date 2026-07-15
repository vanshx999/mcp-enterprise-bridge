# MCP Enterprise Bridge — Session Prompt

## TL;DR
We're building an **MCP Enterprise Bridge MVP**: a FastAPI + LangGraph middleware that connects LLMs (via Groq) to enterprise databases with human-in-the-loop approval. It runs on `https://localhost`, is deployed via Docker Compose, and needs to be production-ready for funding.

---

## Project Structure

```
~/mcp-enterprise-bridge/
├── docker-compose.yml       # 6 services: caddy, backend, frontend, pgbouncer, postgres:16-alpine, redis:7-alpine
├── Caddyfile                # TLS via Caddy 2 (tls internal for localhost, auto-LetsEncrypt for prod)
├── secrets/
│   ├── jwt_secret.txt       # Docker secret — always read from file, never env
│   ├── groq_api_key.txt     # Docker secret — currently set
│   ├── cert.pem / key.pem   # Dev self-signed TLS certs
│   └── db_password.txt
├── backend/
│   ├── main.py              # FastAPI app, CORS, lifespan, 5 routers, WebSocket /ws/approvals
│   ├── core/
│   │   ├── config.py        # Pydantic Settings; effective_jwt_secret & effective_groq_api_key read from files
│   │   ├── database.py      # asyncpg pool, init_db/close_pool, auto-migrate tables
│   │   ├── security.py      # bcrypt hashing, JWT create/decode via python-jose
│   │   └── websocket_manager.py  # WS broadcast for real-time approval push
│   ├── api/
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py  # JWT bearer + X-Agent-Key extraction
│   │   │   └── rate_limiter.py     # slowapi rate limiting
│   │   └── routes/
│   │       ├── auth.py        # POST /api/auth/login, refresh, me; SSO/OIDC (GET /sso/login, /sso/callback, /sso/status)
│   │       ├── agent.py       # POST /api/agent/query (main entry), GET/POST/DELETE /api/agent/keys
│   │       ├── approvals.py   # GET pending, POST approve/deny, GET history (paginated with total)
│   │       ├── audit.py       # GET /api/audit/logs (paginated), GET /export/csv, /export/json
│   │       └── permissions.py # CRUD user_permissions table
│   ├── graph/
│   │   ├── state.py           # BridgeState TypedDict: RiskLevel enum, ApprovalStatus enum
│   │   ├── nodes.py           # 5 LangGraph nodes (see below)
│   │   └── workflow.py        # LangGraph StateGraph with conditional routing, MemorySaver checkpointing
│   ├── mcp_servers/
│   │   ├── sql_server.py      # execute_query (SELECT only), list_tables, describe_schema — AST-level validation via sqlparse, blocks DML/DDL
│   │   └── rest_server.py     # call_api — HTTP client with domain allowlist, SSRF protection, 100KB cap
│   ├── tests/
│   │   ├── test_sql_validation.py   # 16 tests
│   │   ├── test_fallback_intent.py  # 8 tests
│   │   └── test_rest_server.py      # 5 tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # React Router: /login, /dashboard, /approvals, /audit, /permissions
│   │   ├── pages/
│   │   │   ├── Login.tsx     # Local login + SSO button; token extraction from URL params
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Approvals.tsx # Approval request cards with approve/deny buttons
│   │   │   ├── AuditLog.tsx  # Paginated log table + timeline modal + CSV/JSON export
│   │   │   └── Permissions.tsx
│   │   ├── components/       # UI components (dark theme, TailwindCSS)
│   │   ├── api/client.ts     # Axios client with interceptors
│   │   ├── hooks/useWebSocket.ts  # Auto-detects wss:// vs ws:// from page protocol
│   │   └── store/            # Zustand auth store
│   ├── package.json, vite.config.ts, tailwind.config.js
│   └── Dockerfile
├── pgbouncer/
│   ├── pgbouncer.ini         # (unused — edoburu/pgbouncer image uses env vars)
│   └── userlist.txt
└── SESSION_PROMPT.md         # ← this file
```

---

## Architecture: LangGraph Workflow (5 Nodes)

All in `backend/graph/`. Graph definition in `workflow.py`, node implementations in `nodes.py`.

```
START → intent_analysis_node → permission_check_node → hitl_gate_node → mcp_execution_node → audit_log_node → END
                                  ↓ (no permission / direct response)             ↓ (denied/timeout)
                               audit_log_node ←─────────────────────────── audit_log_node
```

### Node Details

1. **intent_analysis_node** — Calls Groq (`llama-3.3-70b-versatile` via httpx, JSON mode) to classify intent. Falls back to regex parser if Groq fails/timeout.

2. **permission_check_node** — Checks `user_permissions` table for `(agent_id, tool_name)`. Computes risk level: HIGH if write operation (INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER/CREATE) or mutating API call (POST/PUT/PATCH/DELETE). Sets auto_approve.

3. **hitl_gate_node** — If auto_approve=False, inserts into `approval_requests` table with expiry. Polls every 2s until timeout. Broadcasts via WebSocket. Returns APPROVED/DENIED/TIMEOUT.

4. **mcp_execution_node** — Routes to sql_server or rest_server based on tool_name.

5. **audit_log_node** — Inserts into `audit_logs` table with event_type, risk metadata, result. Swallows errors.

### Routing
- `route_after_intent`: direct_response → audit_log_node (skip MCP), else → permission_check_node
- `route_after_permission`: no permission/error → audit_log_node, else → hitl_gate_node
- `route_after_hitl`: approved → mcp_execution_node, else → audit_log_node

---

## What's Already Built

### Security & Auth
- JWT auth (python-jose) with bcrypt password hashing
- Agent API keys (X-Agent-Key header, `mcp_sk_*` prefix)
- Role-based access: admin, approver, agent
- CORS allowlist (localhost origins)
- Rate limiting via slowapi
- SSO/OIDC support via httpx (no authlib dependency) — works with Auth0, Okta, Azure AD
- Docker secrets for JWT secret and Groq API key (never in .env)
- TLS via Caddy 2 (`tls internal` for localhost, auto-LetsEncrypt for production domains)

### SQL MCP Server (`sql_server.py`)
- `execute_query`: SELECT-only, AST-level validation via sqlparse `stokens.DML`/`stokens.DDL`
- Blocks ALL write operations: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, CALL
- `list_tables`, `describe_schema`
- SQL injection protection via psycopg parameterization
- Respects paren depth for subqueries
- Passes CTE (WITH) and EXPLAIN

### REST MCP Server (`rest_server.py`)
- Domain allowlist: api.github.com, jsonplaceholder.typicode.com, httpbin.org
- SSRF protection (no private IPs, no localhost)
- Max 100KB response body
- GET/POST/PUT/DELETE support

### HITL Approval
- `approval_requests` table with pending/approved/denied/timeout states
- Configurable timeout via `APPROVAL_TIMEOUT_MINUTES` (default 10 min)
- Real-time WebSocket push to admin UI
- Frontend approval cards with approve/deny buttons
- Risk level badges (low/medium/high), auto-approve badges
- Denied entries shown in red in timeline modal

### Audit Log
- `audit_logs` table with event_type, tool_name, args, result
- Paginated API: `GET /api/audit/logs?limit=&offset=` returns `{total, data, limit, offset}`
- CSV export: `GET /api/audit/export/csv`
- JSON export: `GET /api/audit/export/json`
- Frontend table with search, export buttons, timeline modal

### Frontend
- React 18 + Vite + TailwindCSS, dark theme
- Zustand auth store
- Pages: Login (local + SSO), Dashboard, Approvals, Audit Log, Permissions CRUD
- WebSocket auto-detect wss:// vs ws:// from page protocol
- `VITE_API_URL` is empty (same-origin proxy via Caddy)

### Infrastructure
- Docker Compose: 6 containers all healthy
- Postgres 16 with auto-migration (tables created on startup if not exist)
- PgBouncer (transaction pool mode, scram-sha-256 for PG16)
- Caddy reverse proxy: `/api/*` and `/ws/*` → backend:8000, everything else → frontend:5173
- All secrets as Docker secrets mounted to `/run/secrets/`
- Self-signed dev cert at `secrets/cert.pem` + `secrets/key.pem`
- `backend/.env` exists for non-sensitive config only

### Tests (25 passing)
- `test_sql_validation.py` — 16 tests (SELECT pass, DML/DDL block, subquery safety, CTE pass)
- `test_fallback_intent.py` — 8 tests (SELECT patterns, list tables, describe schema, API calls)
- `test_rest_server.py` — 5 tests (allowlisted domain, SSRF block, body cap)

---

## Credentials for Local Testing

- Admin: `admin@mcpbridge.io` / `admin123`
- Approver: `approver@mcpbridge.io` / `approver123`
- Agent key: created via `POST /api/agent/keys` with admin JWT token

---

## What Needs to Be Done Next (Priority Order)

### 1. README Documentation
Document the complete setup process:
- How to create secrets (`secrets/jwt_secret.txt`, `secrets/groq_api_key.txt`, `secrets/db_password.txt`)
- Initial `docker compose up -d` + db migration (auto-migration handles it, but document)
- How to configure Caddy domain (comment/uncomment Caddyfile lines)
- SSO env vars setup (`sso_issuer_url`, `sso_client_id`, `sso_client_secret`)
- How to create initial users (the backend seeds them on startup)
- How to create agent keys via API
- How to set permissions via API or /permissions UI

### 2. CI/CD Pipeline (GitHub Actions)
Create `.github/workflows/ci.yml`:
- `lint` stage: ruff check, pyright type check
- `test` stage: run the 25 unit tests (pytest)
- `build` stage: build Docker images
- `deploy` stage: deploy to target environment

### 3. Integration Tests
- Spin up test Postgres container
- Run integration tests against real database
- Test full workflow: agent query → intent analysis → permission → HITL → execution → audit
- Test WebSocket approval flow end-to-end

### 4. Production Readiness
- Health check endpoints for each service
- Graceful shutdown handling
- Structured logging (json logs for production)
- Metrics endpoint (Prometheus)
- Rate limit tuning for production
- Security hardening:
  - CORS tighten allowed origins
  - Content Security Policy headers
  - Rate limit per-agent-key
  - Input size limits on all endpoints

### 5. Feature Completeness
- Email/Slack notification for pending approvals
- Approval templates / presets
- Usage analytics dashboard
- Multi-database support (add db selector to SQL MCP server)
- MCP server registry (dynamic addition of new MCP servers via config)
- Agent key rotation UI

### 6. Observability
- Sentry or similar error tracking
- Request tracing (OpenTelemetry)
- Database query performance monitoring
- Audit log retention policies

---

## Tech Constraints (Do NOT Change)

- **Backend**: FastAPI + LangGraph + Groq (llama-3.3-70b-versatile via httpx) — NO SQLAlchemy (raw asyncpg), NO Anthropic/OpenAI
- **Frontend**: React 18 + Vite + TailwindCSS, dark theme, Zustand
- **Infra**: Docker Compose, Caddy 2, Postgres 16, PgBouncer, Redis 7
- **Secrets**: Always via Docker secrets, never in .env files
- **SSO**: httpx directly (no authlib dependency)
- **TLS**: Caddy handles everything (auto-LetsEncrypt for prod, `tls internal` for dev)
- **DB connection**: Backend → PgBouncer (:6432) → Postgres (:5432)
- **CORS origins**: `https://localhost, http://localhost:5173, http://localhost:3000`

---

## How to Start / Restart

```bash
cd ~/mcp-enterprise-bridge
docker compose up -d                              # start all 6 services
docker compose up -d --build backend              # rebuild + restart backend after changes
docker compose logs -f backend                    # tail backend logs
docker compose exec backend python -m pytest      # run tests in container
```
