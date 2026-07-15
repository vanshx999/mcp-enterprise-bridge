from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from api.middleware.auth_middleware import get_current_user, require_role

router = APIRouter(prefix="/api/approval-templates", tags=["approval-templates"])


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    tool_name: str
    resource_pattern: str = "*"
    risk_level: str = "medium"
    auto_approve: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tool_name: Optional[str] = None
    resource_pattern: Optional[str] = None
    risk_level: Optional[str] = None
    auto_approve: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_templates(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM approval_templates ORDER BY name"
        )
    return [dict(r) for r in rows]


@router.post("")
async def create_template(body: TemplateCreate, current_user: dict = Depends(require_role("admin"))):
    if body.risk_level not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="risk_level must be low, medium, or high")
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """INSERT INTO approval_templates (name, description, tool_name, resource_pattern, risk_level, auto_approve)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
                body.name, body.description, body.tool_name, body.resource_pattern, body.risk_level, body.auto_approve,
            )
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail=f"Template '{body.name}' already exists")
            raise HTTPException(status_code=500, detail=str(e))
    return dict(row)


@router.put("/{template_id}")
async def update_template(template_id: str, body: TemplateUpdate, current_user: dict = Depends(require_role("admin"))):
    updates = {}
    for field in ("name", "description", "tool_name", "resource_pattern", "risk_level", "auto_approve", "is_active"):
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "risk_level" in updates and updates["risk_level"] not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="risk_level must be low, medium, or high")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE approval_templates SET {set_clause}, updated_at = NOW() WHERE id = $1::uuid RETURNING *",
            template_id, *values,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    return dict(row)


@router.delete("/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM approval_templates WHERE id = $1::uuid", template_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}


@router.post("/{template_id}/apply")
async def apply_template(template_id: str, agent_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        template = await conn.fetchrow(
            "SELECT * FROM approval_templates WHERE id = $1::uuid AND is_active = true",
            template_id,
        )
        if not template:
            raise HTTPException(status_code=404, detail="Active template not found")

        await conn.execute(
            """INSERT INTO user_permissions (agent_id, tool_name, resource_pattern, risk_level, auto_approve)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (agent_id, tool_name) DO UPDATE SET
                   resource_pattern = EXCLUDED.resource_pattern,
                   risk_level = EXCLUDED.risk_level,
                   auto_approve = EXCLUDED.auto_approve""",
            agent_id, template["tool_name"], template["resource_pattern"],
            template["risk_level"], template["auto_approve"],
        )

    return {"success": True, "agent_id": agent_id, "template": template["name"]}
