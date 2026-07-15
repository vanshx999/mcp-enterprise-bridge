import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
from core.database import get_pool
from api.middleware.auth_middleware import require_role

router = APIRouter(prefix="/api/query-templates", tags=["query-templates"])


class QueryTemplateCreate(BaseModel):
    name: str
    description: str = ""
    query_text: str
    parameters: list[dict[str, Any]] = []
    agent_id: Optional[str] = None


class QueryTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    query_text: Optional[str] = None
    parameters: Optional[list[dict[str, Any]]] = None
    agent_id: Optional[str] = None


@router.get("")
async def list_templates(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, query_text, parameters, agent_id, created_by, created_at, updated_at FROM query_templates ORDER BY created_at DESC"
        )
    return [dict(r) for r in rows]


@router.post("")
async def create_template(body: QueryTemplateCreate, current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO query_templates (name, description, query_text, parameters, agent_id, created_by)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6::uuid)
               RETURNING id, name, description, query_text, parameters, agent_id, created_by, created_at, updated_at""",
            body.name, body.description, body.query_text,
            json.dumps(body.parameters) if body.parameters else "[]",
            body.agent_id, current_user["id"],
        )
    return dict(row)


@router.put("/{template_id}")
async def update_template(template_id: str, body: QueryTemplateUpdate, current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    sets = []
    vals = []
    idx = 1
    if body.name is not None:
        sets.append(f"name = ${idx}"); vals.append(body.name); idx += 1
    if body.description is not None:
        sets.append(f"description = ${idx}"); vals.append(body.description); idx += 1
    if body.query_text is not None:
        sets.append(f"query_text = ${idx}"); vals.append(body.query_text); idx += 1
    if body.parameters is not None:
        sets.append(f"parameters = ${idx}::jsonb"); vals.append(json.dumps(body.parameters)); idx += 1
    if body.agent_id is not None:
        sets.append(f"agent_id = ${idx}"); vals.append(body.agent_id); idx += 1
    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")
    sets.append("updated_at = NOW()")
    vals.append(template_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE query_templates SET {', '.join(sets)} WHERE id = ${idx}::uuid RETURNING id, name, description, query_text, parameters, agent_id, created_by, created_at, updated_at",
            *vals,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    return dict(row)


@router.delete("/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("DELETE FROM query_templates WHERE id = $1::uuid RETURNING id", template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}
