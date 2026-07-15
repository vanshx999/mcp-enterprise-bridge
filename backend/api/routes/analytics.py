from fastapi import APIRouter, Depends
from core.database import get_pool
from api.middleware.auth_middleware import get_current_user, require_role

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()

    async with pool.acquire() as conn:
        total_queries = await conn.fetchval("SELECT COUNT(*) FROM audit_logs")
        total_approved = await conn.fetchval(
            "SELECT COUNT(*) FROM audit_logs WHERE event_type IN ('auto_approved', 'approved_and_executed')"
        )
        total_denied = await conn.fetchval(
            "SELECT COUNT(*) FROM audit_logs WHERE event_type = 'denied'"
        )
        total_approval_requests = await conn.fetchval("SELECT COUNT(*) FROM approval_requests")
        pending_approvals = await conn.fetchval(
            "SELECT COUNT(*) FROM approval_requests WHERE status = 'pending'"
        )
        active_agents = await conn.fetchval(
            "SELECT COUNT(DISTINCT agent_id) FROM audit_logs"
        )

        top_agents = await conn.fetch(
            """SELECT agent_id, COUNT(*) as query_count
               FROM audit_logs
               GROUP BY agent_id
               ORDER BY query_count DESC
               LIMIT 10"""
        )

        queries_by_day = await conn.fetch(
            """SELECT DATE(created_at) as day, COUNT(*) as count
               FROM audit_logs
               WHERE created_at > NOW() - INTERVAL '30 days'
               GROUP BY DATE(created_at)
               ORDER BY day DESC"""
        )

    return {
        "total_queries": total_queries,
        "total_approved": total_approved,
        "total_denied": total_denied,
        "total_approval_requests": total_approval_requests,
        "pending_approvals": pending_approvals,
        "active_agents": active_agents,
        "top_agents": [dict(r) for r in top_agents],
        "queries_by_day": [dict(r) for r in queries_by_day],
    }


@router.get("/usage")
async def agent_usage(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT agent_id, tool_name, COUNT(*) as count,
                      MIN(created_at) as first_used, MAX(created_at) as last_used
               FROM audit_logs
               GROUP BY agent_id, tool_name
               ORDER BY count DESC"""
        )

    return {"usage": [dict(r) for r in rows]}
