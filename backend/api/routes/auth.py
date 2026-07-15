import uuid
import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from core.security import verify_password, create_access_token, decode_access_token
from api.middleware.auth_middleware import get_current_user
from api.middleware.rate_limiter import limiter
from fastapi import Request
from core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _get_oidc_config():
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.sso_issuer_url.rstrip('/')}/.well-known/openid-configuration",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


@router.post("/signup")
@limiter.limit("3/minute")
async def signup(request: Request, body: SignupRequest):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM users WHERE email = $1", body.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        from core.security import hash_password
        user_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO users (id, email, hashed_password, full_name, role, is_active, password_change_required)
               VALUES ($1::uuid, $2, $3, $4, 'approver', true, false)""",
            user_id, body.email, hash_password(body.password), body.full_name,
        )

    token = create_access_token({
        "sub": user_id,
        "email": body.email,
        "role": "approver",
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": body.email,
            "role": "approver",
            "full_name": body.full_name,
            "password_change_required": False,
        },
        "password_change_required": False,
    }


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", body.email)

    if not row or not verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({
        "sub": str(row["id"]),
        "email": row["email"],
        "role": row["role"],
    })

    password_change_required = row.get("password_change_required", False)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(row["id"]),
            "email": row["email"],
            "role": row["role"],
            "full_name": row["full_name"],
            "password_change_required": password_change_required,
        },
        "password_change_required": password_change_required,
    }


@router.get("/sso/login")
async def sso_login(request: Request):
    if not settings.sso_enabled:
        raise HTTPException(status_code=400, detail="SSO is not configured")
    oidc_config = await _get_oidc_config()
    auth_url = oidc_config["authorization_endpoint"]
    redirect_uri = str(request.url_for("sso_callback"))
    params = {
        "response_type": "code",
        "client_id": settings.sso_client_id,
        "redirect_uri": redirect_uri,
        "scope": settings.sso_scope,
        "state": str(uuid.uuid4()),
    }
    import urllib.parse
    redirect_target = f"{auth_url}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=redirect_target)


@router.get("/sso/callback")
async def sso_callback(request: Request):
    if not settings.sso_enabled:
        raise HTTPException(status_code=400, detail="SSO is not configured")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    oidc_config = await _get_oidc_config()
    redirect_uri = str(request.url_for("sso_callback"))

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            oidc_config["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.sso_client_id,
                "client_secret": settings.sso_client_secret,
            },
            timeout=15,
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to exchange authorization code")
        token_data = token_resp.json()

        userinfo_resp = await client.get(
            oidc_config["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=10,
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch user info")
        userinfo = userinfo_resp.json()

    email = (userinfo.get("email") or "").lower()
    name = userinfo.get("name") or userinfo.get("nickname") or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by SSO provider")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)

        if not row:
            user_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO users (id, email, hashed_password, full_name, role, is_active)
                   VALUES ($1::uuid, $2, '', $3, 'approver', true)""",
                user_id, email, name,
            )
            user = {
                "id": user_id,
                "email": email,
                "role": "approver",
                "full_name": name,
            }
        else:
            if not row["is_active"]:
                raise HTTPException(status_code=403, detail="Account is deactivated")
            user = {
                "id": str(row["id"]),
                "email": row["email"],
                "role": row["role"],
                "full_name": row["full_name"] or name,
            }

    jwt_token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
    })

    frontend_url = settings.frontend_url.rstrip("/")
    redirect_url = f"{frontend_url}/login?token={jwt_token}&email={user['email']}&role={user['role']}&name={user['full_name']}"
    return RedirectResponse(url=redirect_url)


class RefreshResponse(BaseModel):
    access_token: str


@router.post("/refresh")
async def refresh(current_user: dict = Depends(get_current_user)):
    token = create_access_token({
        "sub": current_user["id"],
        "email": current_user.get("email", ""),
        "role": current_user.get("role", "viewer"),
    })
    return RefreshResponse(access_token=token)


@router.get("/sso/status")
async def sso_status():
    return {"sso_enabled": settings.sso_enabled, "provider": settings.sso_provider if settings.sso_enabled else None}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("is_agent"):
        raise HTTPException(status_code=400, detail="Agent keys cannot change passwords")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1::uuid", current_user["id"])
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(body.current_password, row["hashed_password"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        if len(body.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

        from core.security import hash_password
        await conn.execute(
            "UPDATE users SET hashed_password = $1, password_change_required = false WHERE id = $2::uuid",
            hash_password(body.new_password), current_user["id"],
        )

    token = create_access_token({
        "sub": str(row["id"]),
        "email": row["email"],
        "role": row["role"],
    })

    return {"success": True, "access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    if current_user.get("is_agent"):
        return current_user
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, email, role, full_name, is_active, password_change_required FROM users WHERE id = $1::uuid", current_user["id"])
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    row_dict = dict(row)
    row_dict["password_change_required"] = row_dict.get("password_change_required", False)
    return row_dict
