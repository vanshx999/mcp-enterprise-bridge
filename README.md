# MCP Enterprise Bridge

A secure middleware that connects LLMs to enterprise databases and REST APIs with human-in-the-loop (HITL) approval. Built with FastAPI + LangGraph + Groq.

## Architecture

```
LLM/Agent → Agent API Key → Intent Analysis (Groq) → Permission Check → HITL Gate → MCP Execution → Audit Log
                                ↓ fallback                    ↓ no perm        ↓ timeout/deny
                            regex parser                  audit_log          audit_log
```

5 LangGraph nodes process every agent query:
1. **intent_analysis_node** — Groq (`llama-3.3-70b-versatile`) classifies intent; regex fallback
2. **permission_check_node** — Checks `user_permissions` table, computes risk level
3. **hitl_gate_node** — Auto-approves low-risk ops; creates approval request for medium/high; polls until resolved or timeout
4. **mcp_execution_node** — Executes SQL queries (SELECT-only) or REST API calls
5. **audit_log_node** — Logs everything to `audit_logs` table

## Prerequisites

- Docker & Docker Compose (with Compose V2)
- A [Groq API key](https://console.groq.com/keys)

## Quick Start

### 1. Create secrets

```bash
cd ~/mcp-enterprise-bridge
mkdir -p secrets

# Generate a strong JWT secret (min 32 chars)
openssl rand -base64 48 | tr -d '\n' > secrets/jwt_secret.txt

# Paste your Groq API key
printf '%s' 'gsk_...' > secrets/groq_api_key.txt

# Optional: custom DB password
# printf '%s' 'your-db-password' > secrets/db_password.txt
```

### 2. Start everything

```bash
docker compose up -d
```

Wait ~15s for Postgres health check + auto-migration. Check status:

```bash
docker compose ps
```

All 6 containers should show `Up`.

### 3. Access the dashboard

Open **https://localhost** in your browser.

Accept the self-signed cert warning (dev only). Login with:

| Email | Password | Role |
|-------|----------|------|
| admin@mcpbridge.io | admin123 | admin |
| approver@mcpbridge.io | approver123 | approver |

### 4. Make your first agent query

On first start, a default agent key is printed in the backend logs:

```bash
docker compose logs backend | grep "DEFAULT AGENT API KEY"
```

Or create one via the API:

```bash
# Get admin token
TOKEN=$(curl -sk -X POST https://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@mcpbridge.io","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create agent key
curl -sk -X POST https://localhost/api/agent/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"default-agent","label":"my-agent"}'
```

Then query:

```bash
curl -sk -X POST https://localhost/api/agent/query \
  -H 'Content-Type: application/json' \
  -H 'X-Agent-Key: mcp_sk_...' \
  -d '{"message":"list tables","agent_id":"default-agent"}'
```

## Configuration

### Environment Variables (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | `development` or `production` |
| `ALLOWED_ORIGINS` | `https://localhost,http://localhost:5173,http://localhost:3000` | CORS origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT lifetime |
| `APPROVAL_TIMEOUT_MINUTES` | 10 | HITL approval timeout |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model for intent analysis |
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATABASE_URL` | `postgresql://postgres:postgres@pgbouncer:6432/mcp_bridge` | DB via PgBouncer |

Never put secrets in `.env`. Use Docker secrets instead.

### SSO/OIDC (Auth0, Okta, Azure AD)

Uncomment in `backend/.env`:

```ini
SSO_ISSUER_URL=https://your-tenant.auth0.com/
SSO_CLIENT_ID=your-client-id
SSO_CLIENT_SECRET=your-client-secret
SSO_PROVIDER=auth0
SSO_SCOPE=openid email profile
FRONTEND_URL=https://localhost
```

Then restart: `docker compose up -d backend`. A **"Sign in with SSO"** button appears on the login page. Auto-provisions first-time users as `approver`.

### Caddy (TLS)

- **Dev**: `Caddyfile` uses `tls internal` — works on localhost with self-signed certs
- **Prod**: Replace domain, comment out `tls internal` — Caddy auto-provisions LetsEncrypt certs

```
example.com {
    reverse_proxy /api/* backend:8000
    reverse_proxy /ws/* backend:8000
    reverse_proxy frontend:5173
}
```

## API Reference

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/login` | — | Login with email/password (returns `password_change_required` flag) |
| POST | `/api/auth/change-password` | JWT | Change password (clears `password_change_required`) |
| POST | `/api/auth/refresh` | JWT | Refresh access token |
| GET | `/api/auth/me` | JWT | Get current user |
| GET | `/api/auth/sso/login` | — | Redirect to SSO provider |
| GET | `/api/auth/sso/callback` | — | SSO callback |
| GET | `/api/auth/sso/status` | — | Check if SSO is configured |

### Agent

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/agent/query` | Agent Key | Submit agent query |
| GET | `/api/agent/session/{id}` | JWT | Get session state |
| POST | `/api/agent/keys` | JWT (admin) | Create agent API key |
| GET | `/api/agent/keys` | JWT (admin/approver) | List agent keys |
| DELETE | `/api/agent/keys/{id}` | JWT (admin) | Revoke agent key |

### Approvals

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/approvals/pending` | JWT (admin/approver) | List pending approvals |
| POST | `/api/approvals/{id}/approve` | JWT (admin/approver) | Approve request |
| POST | `/api/approvals/{id}/deny` | JWT (admin/approver) | Deny request |
| GET | `/api/approvals/history?limit=&offset=&status=` | JWT | Approval history (paginated) |

### Permissions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/permissions` | JWT (admin/approver) | List permissions |
| GET | `/api/permissions/agents` | JWT (admin/approver) | List distinct agent IDs |
| POST | `/api/permissions` | JWT (admin) | Create permission |
| PUT | `/api/permissions/{id}` | JWT (admin) | Update permission |
| DELETE | `/api/permissions/{id}` | JWT (admin) | Delete permission |

### Audit

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/audit/logs?limit=&offset=&agent_id=&event_type=&from_date=&to_date=` | JWT | Audit logs (paginated) |
| GET | `/api/audit/logs/{session_id}` | JWT | Session audit trail |
| GET | `/api/audit/export/csv` | JWT | Export audit logs as CSV |
| GET | `/api/audit/export/json` | JWT | Export audit logs as JSON |

### WebSocket

| Endpoint | Auth | Description |
|----------|------|-------------|
| `wss://localhost/ws/approvals?token=<jwt>` | JWT (admin/approver) | Real-time approval push |

### Health & Config

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check (DB + Redis) |
| GET | `/api/config/validate` | JWT (admin) | Validate production configuration |

## Testing

```bash
# Run all tests
make test

# Or directly
docker compose exec backend python -m pytest -v

# Run a specific test file
docker compose exec backend python -m pytest tests/test_sql_validation.py -v
```

34 tests across 4 files:
- `test_sql_validation.py` — 12 tests (SELECT pass, DML/DDL block, CTE/EXPLAIN pass)
- `test_fallback_intent.py` — 8 tests (regex intent parsing)
- `test_rest_server.py` — 5 tests (domain allowlist, SSRF blocking)
- `test_integration.py` — 9 tests (E2E flows: greeting, fallthrough, permissions, SQL parsing, REST, direct)

## Development Commands

```bash
make up              # Start all services
make down            # Stop all services
make build           # Rebuild backend image
make restart         # Rebuild + restart backend
make logs            # Tail all logs
make test            # Run all backend tests
make frontend-build  # Build frontend for production
make shell-db        # Open psql shell
make ps              # Show container status
make clean           # Remove all containers, volumes, images
```

## Security

- **Secrets**: All sensitive values (JWT secret, Groq key) via Docker secrets — never in `.env`
- **SQL**: AST-level validation via sqlparse — only SELECT queries pass; INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/MERGE/CALL blocked
- **REST**: Domain allowlist only (api.github.com, jsonplaceholder.typicode.com, httpbin.org); SSRF protection (no private IPs); 100KB body cap
- **Auth**: JWT (python-jose) + bcrypt + agent API keys (`mcp_sk_*` prefix)
- **Rate limiting**: slowapi — 5/min login, 10/min agent query
- **TLS**: Caddy 2 with auto-LetsEncrypt (prod) or `tls internal` (dev)

## Project Structure

```
├── docker-compose.yml       # 6 services: caddy, backend, frontend, pgbouncer, postgres, redis
├── Caddyfile                # TLS reverse proxy
├── secrets/                 # Docker secrets (gitignored)
├── backend/
│   ├── main.py              # FastAPI app, routers, WebSocket
│   ├── core/config.py       # Pydantic Settings (reads secrets from files)
│   ├── core/database.py     # asyncpg pool + auto-migration + seed data
│   ├── core/security.py     # bcrypt, JWT
│   ├── core/websocket_manager.py
│   ├── api/routes/          # auth, agent, approvals, audit, permissions
│   ├── api/middleware/      # auth_middleware, rate_limiter
│   ├── graph/               # state.py, nodes.py, workflow.py (LangGraph)
│   ├── mcp_servers/         # sql_server.py, rest_server.py
│   └── tests/               # 25 unit tests
├── frontend/
│   ├── src/pages/           # Login, Dashboard, Approvals, AuditLog, Permissions
│   ├── src/hooks/           # useWebSocket (auto-detects wss:// vs ws://)
│   └── src/api/client.ts    # Axios client
├── pgbouncer/               # PgBouncer config (unused — edoburu image uses env vars)
└── secrets/                 # jwt_secret.txt, groq_api_key.txt, cert.pem, key.pem
```

## Infrastructure

| Service | Image | Purpose |
|---------|-------|---------|
| caddy | caddy:2-alpine | TLS termination, reverse proxy |
| backend | python:3.12-slim | FastAPI + LangGraph + Groq |
| frontend | node:20-alpine | React 18 + Vite dashboard |
| pgbouncer | edoburu/pgbouncer | Connection pooling (transaction mode, scram-sha-256) |
| postgres | postgres:16-alpine | Primary database |
| redis | redis:7-alpine | Rate limiting backing store |

## Production Deployment

### Prerequisites

- A domain name with DNS pointing to your server (e.g., `mcp-bridge.example.com`)
- Docker & Docker Compose on a Linux server (Ubuntu 22.04+ recommended)
- A [Groq API key](https://console.groq.com/keys)
- (Optional) SSO provider (Auth0, Okta, Azure AD)
- (Optional) Sentry DSN for error tracking
- (Optional) OpenTelemetry endpoint for distributed tracing
- (Optional) Slack webhook URL for approval notifications

### 1. Clone and configure

```bash
git clone https://github.com/your-org/mcp-enterprise-bridge.git
cd mcp-enterprise-bridge

# Create secrets
mkdir -p secrets
openssl rand -base64 48 | tr -d '\n' > secrets/jwt_secret.txt
printf '%s' 'gsk_your_groq_key_here' > secrets/groq_api_key.txt
```

### 2. Customize for production

Edit `Caddyfile` — replace `localhost` with your domain and remove `tls internal`:

```
mcp-bridge.example.com {
    reverse_proxy /api/* backend:8000
    reverse_proxy /ws/* backend:8000
    reverse_proxy frontend:5173
}
```

Caddy will auto-provision Let's Encrypt TLS certificates on first request.

### 3. Configure environment

Edit `backend/.env`:

```ini
ENVIRONMENT=production
ALLOWED_ORIGINS=https://mcp-bridge.example.com
DATABASE_URL=postgresql://postgres:postgres@pgbouncer:6432/mcp_bridge

# Optional observability
SENTRY_DSN=https://your-dsn@sentry.io/your-project
OTEL_ENDPOINT=http://your-otel-collector:4318/v1/traces
OTEL_SERVICE_NAME=mcp-enterprise-bridge
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
AUDIT_LOG_RETENTION_DAYS=90
```

### 4. Set up PostgreSQL (production-grade)

For production, use a managed PostgreSQL (RDS, Cloud SQL, etc.) instead of the container. Update `docker-compose.yml` to remove the `postgres` service and point `DATABASE_URL` to your managed instance.

If using the built-in Postgres container, mount a persistent volume:

```yaml
volumes:
  postgres_data:
    driver: local
```

### 5. Start services

```bash
docker compose up -d --build
```

Verify all services are healthy:

```bash
docker compose ps
curl -sk https://mcp-bridge.example.com/api/health
```

### 6. Create admin user and first agent key

```bash
# Login
TOKEN=$(curl -sk -X POST https://mcp-bridge.example.com/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@mcpbridge.io","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create agent key
curl -sk -X POST https://mcp-bridge.example.com/api/agent/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"production-agent","label":"production-v1"}'
```

### 7. Set up monitoring

- **Prometheus**: The backend exposes metrics at `https://mcp-bridge.example.com/api/metrics`. Point your Prometheus scraper there.
- **Sentry**: Enable by setting `SENTRY_DSN` in `.env`. Captures unhandled exceptions and performance traces.
- **OpenTelemetry**: Set `OTEL_ENDPOINT` to your OTLP HTTP collector. Traces are exported for FastAPI requests and LangGraph node execution.
- **Health checks**: Use `GET /api/health` for load balancer health probes. Returns DB + Redis status, version, and uptime.

### 8. Security hardening checklist

- [ ] Change default admin password immediately
- [ ] Set strong JWT secret (`openssl rand -base64 48`)
- [ ] Configure SSO and disable local login if desired
- [ ] Restrict CORS origins to your exact domain
- [ ] Enable rate limiting (login: 5/min, agent query: 10/min by default)
- [ ] Rotate agent API keys regularly via the dashboard or `POST /api/agent/keys/{id}/rotate`
- [ ] Set `APPROVAL_TIMEOUT_MINUTES` to a reasonable value (default 10)
- [ ] Configure audit log retention via `AUDIT_LOG_RETENTION_DAYS` (default 90)
- [ ] Use managed PostgreSQL with automated backups
- [ ] Enable Caddy's built-in rate limiting for brute-force protection
- [ ] Set up log aggregation (Docker logs → your observability platform)

### 9. Upgrading

```bash
git pull
docker compose up -d --build
```

Database migrations run automatically on startup. No manual migration steps needed.

## Common Commands

```bash
# Start all services
docker compose up -d

# Rebuild and restart backend after code changes
docker compose up -d --build backend

# Tail logs
docker compose logs -f backend

# Run tests
docker compose exec backend python -m pytest -v

# Access database
docker compose exec postgres psql -U postgres -d mcp_bridge

# List containers
docker compose ps
```
