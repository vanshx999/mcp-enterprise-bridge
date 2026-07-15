from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from core.security import decode_access_token
from core.database import get_pool

bearer_scheme = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = None
    if credentials:
        token = credentials.credentials
    else:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    agent_key = request.headers.get("X-Agent-Key")

    if not token and not agent_key:
        raise HTTPException(status_code=401, detail="Authentication required")

    if agent_key:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT agent_id, key_hash FROM agent_api_keys WHERE is_active = true"
            )
        for row in rows:
            if pwd_context.verify(agent_key, row["key_hash"]):
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE agent_api_keys SET last_used_at = NOW() WHERE agent_id = $1",
                        row["agent_id"],
                    )
                return {
                    "id": row["agent_id"],
                    "agent_id": row["agent_id"],
                    "role": "agent",
                    "is_agent": True,
                }
        raise HTTPException(status_code=401, detail="Invalid agent key")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role", "viewer"),
        "is_agent": False,
    }


def require_role(*roles: str):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("is_agent"):
            return current_user
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
