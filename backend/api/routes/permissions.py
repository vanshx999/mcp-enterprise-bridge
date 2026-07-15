from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from api.middleware.auth_middleware import get_current_user, require_role

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


class PermissionCreate(BaseModel):
    agent_id: str
    tool_name: str
    resource_pattern: str = "*"
    risk_level: str = "low"
    auto_approve: bool = False


class PermissionUpdate(BaseModel):
    resource_pattern: Optional[str] = None
    risk_level: Optional[str] = None
    auto_approve: Optional[bool] = None


@router.get("")
async def list_permissions(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM user_permissions ORDER BY agent_id, tool_name"
        )
    return [dict(r) for r in rows]


@router.get("/agents")
async def list_agents(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT agent_id FROM user_permissions ORDER BY agent_id"
        )
    return [r["agent_id"] for r in rows]


@router.post("")
async def create_permission(body: PermissionCreate, current_user: dict = Depends(require_role("admin"))):
    if body.risk_level not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="risk_level must be low, medium, or high")
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """INSERT INTO user_permissions (agent_id, tool_name, resource_pattern, risk_level, auto_approve)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING *""",
                body.agent_id, body.tool_name, body.resource_pattern, body.risk_level, body.auto_approve,
            )
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="Permission already exists for this agent/tool")
            raise HTTPException(status_code=500, detail=str(e))
    return dict(row)


@router.put("/{permission_id}")
async def update_permission(permission_id: str, body: PermissionUpdate, current_user: dict = Depends(require_role("admin"))):
    updates = {}
    if body.resource_pattern is not None:
        updates["resource_pattern"] = body.resource_pattern
    if body.risk_level is not None:
        if body.risk_level not in ("low", "medium", "high"):
            raise HTTPException(status_code=400, detail="risk_level must be low, medium, or high")
        updates["risk_level"] = body.risk_level
    if body.auto_approve is not None:
        updates["auto_approve"] = body.auto_approve

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE user_permissions SET {set_clause} WHERE id = $1::uuid RETURNING *",
            permission_id, *values,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Permission not found")
    return dict(row)


@router.delete("/{permission_id}")
async def delete_permission(permission_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_permissions WHERE id = $1::uuid", permission_id
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Permission not found")
    return {"success": True}
