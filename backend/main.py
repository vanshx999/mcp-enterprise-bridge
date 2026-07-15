import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.config import settings
from core.database import init_db, close_pool, get_pool
from core.websocket_manager import ws_manager
from core.logging import setup_logging, logger
from core.redis_client import close_redis, check_redis_health
from core.sentry import init_sentry
from core.otel import init_otel
from core.audit_retention import cleanup_expired_audit_logs
from api.middleware.auth_middleware import get_current_user, decode_access_token
from api.middleware.rate_limiter import limiter
from api.middleware.security_headers import SecurityHeadersMiddleware
from api.middleware.input_size_limit import InputSizeLimitMiddleware
from api.middleware.metrics_middleware import MetricsMiddleware
from api.routes import auth, approvals, agent, audit, permissions, metrics, analytics, databases, approval_templates, config as config_routes, users, query_templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting MCP Enterprise Bridge", extra={"extra_fields": {"version": "0.1.0", "environment": settings.environment}})
    init_sentry()
    init_otel()
    await init_db()
    try:
        result = await cleanup_expired_audit_logs()
        if result.get("deleted_count", 0) > 0:
            logger.info(f"Startup audit cleanup: {result}")
    except Exception:
        pass
    yield
    logger.info("Shutting down...")
    await close_pool()
    await close_redis()
    ws_manager.connections.clear()


app = FastAPI(
    title="MCP Enterprise Bridge",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Agent-Key"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputSizeLimitMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(auth.router)
app.include_router(approvals.router)
app.include_router(agent.router)
app.include_router(audit.router)
app.include_router(permissions.router)
app.include_router(metrics.router)
app.include_router(analytics.router)
app.include_router(databases.router)
app.include_router(approval_templates.router)
app.include_router(config_routes.router)
app.include_router(users.router)
app.include_router(query_templates.router)


@app.get("/api/health")
async def health():
    db_ok = False
    redis_ok = False
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            db_ok = True
    except Exception:
        pass

    try:
        redis_ok = await check_redis_health()
    except Exception:
        redis_ok = False

    status = "healthy" if db_ok else "degraded"
    return {
        "status": status,
        "service": "mcp-enterprise-bridge",
        "version": "0.1.0",
        "environment": settings.environment,
        "checks": {
            "database": "ok" if db_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws/approvals")
async def approvals_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    if payload.get("role") not in ("admin", "approver"):
        await websocket.close(code=4003, reason="Insufficient permissions")
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
