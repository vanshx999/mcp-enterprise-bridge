from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from api.middleware.auth_middleware import get_current_user, require_role
from mcp_servers.sql_server import close_all_db_pools

router = APIRouter(prefix="/api/databases", tags=["databases"])


class DatabaseCreate(BaseModel):
    name: str
    connection_url: str
    db_type: str = "postgresql"


class DatabaseUpdate(BaseModel):
    connection_url: Optional[str] = None
    db_type: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_databases(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, db_type, is_active, created_at, updated_at FROM registered_databases ORDER BY name"
        )
    return [dict(r) for r in rows]


@router.post("")
async def register_database(body: DatabaseCreate, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """INSERT INTO registered_databases (name, connection_url, db_type)
                   VALUES ($1, $2, $3) RETURNING id, name, db_type, is_active, created_at""",
                body.name, body.connection_url, body.db_type,
            )
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail=f"Database '{body.name}' already registered")
            raise HTTPException(status_code=500, detail=str(e))
    return dict(row)


@router.put("/{db_id}")
async def update_database(db_id: str, body: DatabaseUpdate, current_user: dict = Depends(require_role("admin"))):
    updates = {}
    if body.connection_url is not None:
        updates["connection_url"] = body.connection_url
    if body.db_type is not None:
        updates["db_type"] = body.db_type
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE registered_databases SET {set_clause}, updated_at = NOW() WHERE id = $1::uuid RETURNING id, name, db_type, is_active, updated_at",
            db_id, *values,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Database not found")

    await close_all_db_pools()
    return dict(row)


@router.delete("/{db_id}")
async def unregister_database(db_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM registered_databases WHERE id = $1::uuid", db_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Database not found")

    await close_all_db_pools()
    return {"success": True}


@router.post("/{db_id}/test")
async def test_database_connection(db_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT name, connection_url FROM registered_databases WHERE id = $1::uuid AND is_active = true",
            db_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Active database not found")

    import asyncpg
    try:
        test_pool = await asyncpg.create_pool(row["connection_url"], min_size=1, max_size=1)
        async with test_pool.acquire() as test_conn:
            await test_conn.fetchval("SELECT 1")
        await test_pool.close()
        return {"success": True, "name": row["name"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
