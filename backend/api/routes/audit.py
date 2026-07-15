import csv
import io
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from core.database import get_pool
from api.middleware.auth_middleware import get_current_user, require_role
from core.audit_retention import cleanup_expired_audit_logs

router = APIRouter(prefix="/api/audit", tags=["audit"])


async def _build_audit_query(filters: dict):
    conditions = []
    params = []
    idx = 1

    if filters.get("agent_id"):
        conditions.append(f"agent_id = ${idx}")
        params.append(filters["agent_id"])
        idx += 1
    if filters.get("event_type"):
        conditions.append(f"event_type = ${idx}")
        params.append(filters["event_type"])
        idx += 1
    if filters.get("from_date"):
        conditions.append(f"created_at >= ${idx}")
        params.append(filters["from_date"])
        idx += 1
    if filters.get("to_date"):
        conditions.append(f"created_at <= ${idx}")
        params.append(filters["to_date"])
        idx += 1

    where = ""
    if conditions:
        where = " WHERE " + " AND ".join(conditions)
    return where, params


@router.get("/logs")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    filters = {
        "agent_id": agent_id,
        "event_type": event_type,
        "from_date": from_date,
        "to_date": to_date,
    }
    where, params = await _build_audit_query(filters)

    count_query = f"SELECT COUNT(*) FROM audit_logs{where}"
    data_query = f"SELECT * FROM audit_logs{where} ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params)
        rows = await conn.fetch(data_query, *params + [limit, offset])

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [dict(row) for row in rows],
    }


@router.get("/logs/{session_id}")
async def get_session_logs(session_id: str, current_user: dict = Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM audit_logs WHERE session_id = $1 ORDER BY created_at ASC",
            session_id,
        )
    return [dict(row) for row in rows]


@router.get("/export/csv")
async def export_audit_csv(
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    filters = {
        "agent_id": agent_id,
        "event_type": event_type,
        "from_date": from_date,
        "to_date": to_date,
    }
    where, params = await _build_audit_query(filters)
    query = f"SELECT * FROM audit_logs{where} ORDER BY created_at DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(row.values())

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/export/json")
async def export_audit_json(
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    filters = {
        "agent_id": agent_id,
        "event_type": event_type,
        "from_date": from_date,
        "to_date": to_date,
    }
    where, params = await _build_audit_query(filters)
    query = f"SELECT * FROM audit_logs{where} ORDER BY created_at DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    data = json.dumps([dict(r) for r in rows], default=str, indent=2)
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
    )


@router.post("/cleanup")
async def cleanup_audit_logs(
    dry_run: bool = Query(False, description="If true, only count without deleting"),
    current_user: dict = Depends(require_role("admin")),
):
    result = await cleanup_expired_audit_logs(dry_run=dry_run)
    return result
