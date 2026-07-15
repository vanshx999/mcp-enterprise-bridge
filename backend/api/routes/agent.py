import uuid
import json
import secrets
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import get_pool
from core.security import hash_password
from api.middleware.auth_middleware import get_current_user, require_role
from api.middleware.rate_limiter import limiter
from fastapi import Request
from graph.state import BridgeState, ApprovalStatus
from graph.workflow import graph

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    message: str
    agent_id: str
    session_id: Optional[str] = None
    db_name: Optional[str] = None


@router.post("/query")
@limiter.limit("10/minute")
async def agent_query(request: Request, body: AgentQueryRequest, current_user: dict = Depends(get_current_user)):
    session_id = body.session_id or str(uuid.uuid4())

    initial_state: BridgeState = {
        "session_id": session_id,
        "agent_id": body.agent_id,
        "db_name": body.db_name,
        "user_message": body.message,
        "tool_name": None,
        "tool_args": None,
        "intent_summary": None,
        "has_permission": None,
        "risk_level": None,
        "risk_reason": None,
        "auto_approve": None,
        "approval_request_id": None,
        "approval_status": None,
        "reviewer_note": None,
        "tool_result": None,
        "execution_error": None,
        "final_response": None,
        "error_message": None,
    }

    config = {"configurable": {"thread_id": session_id}}

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO session_states (session_id, agent_id, graph_state, current_node, status)
               VALUES ($1, $2, $3::jsonb, 'intent_analysis_node', 'active')
               ON CONFLICT (session_id) DO UPDATE SET graph_state = $3::jsonb, current_node = 'intent_analysis_node', updated_at = NOW()""",
            session_id, body.agent_id, json.dumps(initial_state, default=str),
        )

    try:
        result = await graph.ainvoke(initial_state, config)

        is_pending = result.get("approval_status") == "pending" if result.get("approval_status") else False

        async with pool.acquire() as conn:
            status = "pending_approval" if is_pending else "completed"
            await conn.execute(
                """UPDATE session_states SET graph_state = $1::jsonb, status = $3, updated_at = NOW()
                   WHERE session_id = $2""",
                json.dumps(result, default=str), session_id, status,
            )

        from api.routes.metrics import agent_queries_total
        result_status = "completed"
        if result.get("error_message") or result.get("execution_error"):
            result_status = "error"
        elif is_pending:
            result_status = "pending_approval"
        agent_queries_total.labels(agent_id=body.agent_id, result=result_status).inc()

        return {
            "session_id": session_id,
            "status": "pending_approval" if is_pending else "completed",
            "result": result.get("final_response") if not is_pending else None,
            "requires_approval": is_pending,
            "approval_request_id": result.get("approval_request_id"),
            "error": result.get("error_message") or result.get("execution_error"),
        }
    except Exception as e:
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE session_states SET status = 'failed', graph_state = $1::jsonb, updated_at = NOW()
                   WHERE session_id = $2""",
                json.dumps({"error": str(e)}, default=str), session_id,
            )
        from api.routes.metrics import agent_queries_total
        agent_queries_total.labels(agent_id=body.agent_id, result="error").inc()
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.post("/query/{session_id}/continue")
async def continue_query(session_id: str, current_user: dict = Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        session_row = await conn.fetchrow(
            "SELECT * FROM session_states WHERE session_id = $1", session_id
        )
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")

        if session_row["status"] != "pending_approval":
            raise HTTPException(status_code=400, detail="Session is not in pending_approval state")

        approval = await conn.fetchrow(
            "SELECT status, reviewer_note FROM approval_requests WHERE session_id = $1 ORDER BY created_at DESC LIMIT 1",
            session_id,
        )

    if not approval:
        raise HTTPException(status_code=400, detail="No approval request found for this session")

    raw_state = session_row["graph_state"]
    if isinstance(raw_state, str):
        state = json.loads(raw_state)
    else:
        state = dict(raw_state)
    approval_status = approval["status"]

    if approval_status == "denied":
        state["approval_status"] = ApprovalStatus.DENIED
        state["error_message"] = f"Request denied: {approval.get('reviewer_note') or 'No reason given'}"
        state["final_response"] = state["error_message"]
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE session_states SET graph_state = $1::jsonb, status = 'denied', updated_at = NOW() WHERE session_id = $2",
                json.dumps(state, default=str), session_id,
            )
        return {"session_id": session_id, "status": "denied", "result": None, "error": state["error_message"]}

    if approval_status == "timeout":
        state["approval_status"] = ApprovalStatus.TIMEOUT
        state["error_message"] = "Approval request timed out"
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE session_states SET graph_state = $1::jsonb, status = 'timeout', updated_at = NOW() WHERE session_id = $2",
                json.dumps(state, default=str), session_id,
            )
        return {"session_id": session_id, "status": "timeout", "result": None, "error": "Approval timed out"}

    if approval_status != "approved":
        return {"session_id": session_id, "status": "pending", "result": None, "error": None}

    state["approval_status"] = ApprovalStatus.APPROVED
    state["reviewer_note"] = approval.get("reviewer_note")

    from graph.nodes import mcp_execution_node, audit_log_node

    try:
        result = await mcp_execution_node(state)
        result = await audit_log_node(result)
    except Exception as e:
        state["execution_error"] = str(e)
        state["final_response"] = f"Execution error: {str(e)}"
        result = state

    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE session_states SET graph_state = $1::jsonb, status = 'completed', updated_at = NOW()
               WHERE session_id = $2""",
            json.dumps(result, default=str), session_id,
        )

    return {
        "session_id": session_id,
        "status": "completed",
        "result": result.get("final_response"),
        "requires_approval": False,
        "approval_request_id": None,
        "error": result.get("error_message") or result.get("execution_error"),
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM session_states WHERE session_id = $1", session_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


class CreateKeyRequest(BaseModel):
    agent_id: str
    label: str = ""


@router.post("/keys")
async def create_agent_key(body: CreateKeyRequest, current_user: dict = Depends(require_role("admin"))):
    raw_key = "mcp_sk_" + secrets.token_urlsafe(32)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO agent_api_keys (agent_id, key_hash, key_prefix, label)
               VALUES ($1, $2, $3, $4)""",
            body.agent_id,
            hash_password(raw_key),
            raw_key[:8],
            body.label,
        )
    return {"key": raw_key, "agent_id": body.agent_id, "label": body.label}


@router.get("/keys")
async def list_agent_keys(current_user: dict = Depends(require_role("admin", "approver"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, agent_id, key_prefix, label, is_active, created_at, last_used_at
               FROM agent_api_keys ORDER BY created_at DESC"""
        )
    return [dict(r) for r in rows]


@router.post("/keys/{key_id}/rotate")
async def rotate_agent_key(key_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT agent_id, label FROM agent_api_keys WHERE id = $1::uuid AND is_active = true",
            key_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Active key not found")
        await conn.execute(
            "UPDATE agent_api_keys SET is_active = false WHERE id = $1::uuid",
            key_id,
        )

    import secrets
    raw_key = "mcp_sk_" + secrets.token_urlsafe(32)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO agent_api_keys (agent_id, key_hash, key_prefix, label)
               VALUES ($1, $2, $3, $4)""",
            row["agent_id"],
            hash_password(raw_key),
            raw_key[:8],
            f"{row['label']} (rotated)",
        )
    return {"key": raw_key, "agent_id": row["agent_id"]}


@router.delete("/keys/{key_id}")
async def revoke_agent_key(key_id: str, current_user: dict = Depends(require_role("admin"))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE agent_api_keys SET is_active = false WHERE id = $1::uuid", key_id
        )
    return {"success": True}
