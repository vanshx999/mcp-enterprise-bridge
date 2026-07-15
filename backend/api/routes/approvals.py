from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from api.middleware.auth_middleware import get_current_user, require_role
from core.websocket_manager import ws_manager
from core.email_notifier import notify_approval_resolved_email
import json

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    note: Optional[str] = None


class DenyRequest(BaseModel):
    note: str


class BulkActionRequest(BaseModel):
    request_ids: list[str]
    action: str  # "approve" or "deny"
    note: str = ""


@router.post("/bulk")
async def bulk_action(body: BulkActionRequest, current_user: dict = Depends(require_role("admin", "approver"))):
    if body.action not in ("approve", "deny"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'deny'")
    if not body.request_ids:
        raise HTTPException(status_code=400, detail="No request IDs provided")
    if body.action == "deny" and not body.note.strip():
        raise HTTPException(status_code=400, detail="Note is required when denying")

    pool = await get_pool()
    results = []
    for rid in body.request_ids:
        async with pool.acquire() as conn:
            if body.action == "approve":
                row = await conn.fetchrow(
                    """UPDATE approval_requests SET status = 'approved', reviewed_by = $1::uuid, reviewed_at = NOW(), reviewer_note = $2
                       WHERE id = $3::uuid AND status = 'pending' RETURNING id, agent_id, tool_name""",
                    current_user["id"], body.note, rid,
                )
            else:
                row = await conn.fetchrow(
                    """UPDATE approval_requests SET status = 'denied', reviewed_by = $1::uuid, reviewed_at = NOW(), reviewer_note = $2
                       WHERE id = $3::uuid AND status = 'pending' RETURNING id, agent_id, tool_name""",
                    current_user["id"], body.note, rid,
                )
        if row:
            results.append(rid)
            await ws_manager.broadcast({
                "type": "approval_resolved",
                "data": {"request_id": rid, "status": body.action},
            })
            await notify_approval_resolved_email(rid, row["agent_id"], row["tool_name"], body.action, body.note)

    from api.routes.metrics import approval_requests_total
    for _ in results:
        approval_requests_total.labels(status=body.action).inc()

    return {"success": True, "action": body.action, "processed": len(results), "request_ids": results}


@router.get("/pending")
async def get_pending(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, session_id, agent_id, tool_name, tool_args, risk_level, risk_reason, created_at, expires_at
               FROM approval_requests
               WHERE status = 'pending'
               ORDER BY created_at DESC"""
        )
    return [dict(row) for row in rows]


@router.post("/{request_id}/approve")
async def approve_request(
    request_id: str,
    body: ApproveRequest,
    current_user: dict = Depends(require_role("admin", "approver")),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE approval_requests
               SET status = 'approved', reviewed_by = $1::uuid, reviewed_at = NOW(), reviewer_note = $2
               WHERE id = $3::uuid AND status = 'pending'
               RETURNING id, agent_id, tool_name""",
            current_user["id"], body.note or "", request_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")

    await ws_manager.broadcast({
        "type": "approval_resolved",
        "data": {"request_id": request_id, "status": "approved"},
    })

    from api.routes.metrics import approval_requests_total
    approval_requests_total.labels(status="approved").inc()

    await notify_approval_resolved_email(request_id, row["agent_id"], row["tool_name"], "approved", body.note)

    return {"success": True, "request_id": request_id}


@router.post("/{request_id}/deny")
async def deny_request(
    request_id: str,
    body: DenyRequest,
    current_user: dict = Depends(require_role("admin", "approver")),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE approval_requests
               SET status = 'denied', reviewed_by = $1::uuid, reviewed_at = NOW(), reviewer_note = $2
               WHERE id = $3::uuid AND status = 'pending'
               RETURNING id, agent_id, tool_name""",
            current_user["id"], body.note, request_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")

    await ws_manager.broadcast({
        "type": "approval_resolved",
        "data": {"request_id": request_id, "status": "denied"},
    })

    from api.routes.metrics import approval_requests_total
    approval_requests_total.labels(status="denied").inc()

    await notify_approval_resolved_email(request_id, row["agent_id"], row["tool_name"], "denied", body.note)

    return {"success": True, "request_id": request_id}


@router.get("/history")
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    base_query = """FROM approval_requests a
                    LEFT JOIN users u ON a.reviewed_by = u.id"""
    params = []
    if status:
        base_query += " WHERE a.status = $" + str(len(params) + 1)
        params.append(status)

    count_query = "SELECT COUNT(*) " + base_query
    data_query = "SELECT a.*, u.full_name as reviewer_name " + base_query
    data_query += " ORDER BY a.created_at DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params)
        rows = await conn.fetch(data_query, *params + [limit, offset])

    return {"total": total, "limit": limit, "offset": offset, "data": [dict(row) for row in rows]}
