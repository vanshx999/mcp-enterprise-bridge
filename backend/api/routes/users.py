import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from core.security import hash_password
from api.middleware.auth_middleware import get_current_user, require_role

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "approver"


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_users(current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, email, role, full_name, is_active, password_change_required, created_at FROM users ORDER BY created_at DESC"
        )
    return [dict(r) for r in rows]


@router.post("")
async def create_user(body: CreateUserRequest, current_user: dict = Depends(require_role("admin"))):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if body.role not in ("admin", "approver", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be admin, approver, or viewer")

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM users WHERE email = $1", body.email)
        if existing:
            raise HTTPException(status_code=409, detail="User with this email already exists")

        row = await conn.fetchrow(
            """INSERT INTO users (id, email, hashed_password, full_name, role, password_change_required)
               VALUES ($1::uuid, $2, $3, $4, $5, true) RETURNING id, email, role, full_name, is_active, created_at""",
            str(uuid.uuid4()), body.email, hash_password(body.password), body.full_name, body.role,
        )
    return dict(row)


@router.put("/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest, current_user: dict = Depends(require_role("admin"))):
    updates = {}
    if body.full_name is not None:
        updates["full_name"] = body.full_name
    if body.role is not None:
        if body.role not in ("admin", "approver", "viewer"):
            raise HTTPException(status_code=400, detail="Role must be admin, approver, or viewer")
        updates["role"] = body.role
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE users SET {set_clause} WHERE id = $1::uuid RETURNING id, email, role, full_name, is_active, created_at",
            user_id, *values,
        )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_role("admin"))):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1::uuid", user_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}
