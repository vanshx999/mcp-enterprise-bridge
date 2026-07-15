import json
import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from core.config import settings
from core.database import get_pool
from core.websocket_manager import ws_manager
from graph.state import BridgeState, RiskLevel, ApprovalStatus


async def _groq_intent_analysis(user_message: str) -> dict | None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.effective_groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an intent analyzer for an MCP bridge. Identify whether the user wants to:\n"
                            "1. Query a database (tool: execute_query, args: {query: <SELECT SQL>})\n"
                            "2. List tables (tool: list_tables, args: {schema_name: <schema>})\n"
                            "3. Describe schema (tool: describe_schema, args: {table_name: <table>, schema_name: <schema>})\n"
                            "4. Call an external REST API (tool: call_api, args: {method: <GET|POST|PUT|DELETE>, url: <url>, headers: <dict>, body: <any>})\n"
                            "5. Nothing database- or API-related (respond directly)\n\n"
                            'Respond with JSON only: {"tool_name": "...", "tool_args": {...}, "intent_summary": "...", "direct_response": null or "..."}\n'
                            "If no tool is needed, set direct_response to your answer and leave tool_name null."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 500,
                "temperature": 0.1,
            },
        )
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


def _fallback_intent_analysis(user_message: str) -> dict:
    msg = user_message.strip()
    upper = msg.upper()

    sql_select = re.search(
        r"\bSELECT\b.*\bFROM\b", upper, re.DOTALL
    )
    if sql_select:
        return {
            "tool_name": "execute_query",
            "tool_args": {"query": msg},
            "intent_summary": "Execute a SELECT query on the database",
            "direct_response": None,
        }

    if re.search(r"\blist\s+tables?\b", msg, re.IGNORECASE) or re.search(r"\bshow\s+tables?\b", msg, re.IGNORECASE):
        return {
            "tool_name": "list_tables",
            "tool_args": {"schema_name": "public"},
            "intent_summary": "List database tables",
            "direct_response": None,
        }

    schema_match = re.search(r"\bdescribe\s+schema\s+(\w+)", msg, re.IGNORECASE)
    if schema_match or re.search(r"\bschema\s+of\b", msg, re.IGNORECASE):
        table = schema_match.group(1) if schema_match else ""
        if not table:
            word_match = re.findall(r"\b(\w+)\b", msg)
            table = word_match[-1] if word_match else ""
        return {
            "tool_name": "describe_schema",
            "tool_args": {"table_name": table, "schema_name": "public"},
            "intent_summary": f"Describe schema of table '{table}'",
            "direct_response": None,
        }

    rest_match = re.search(
        r"\b(GET|POST|PUT|DELETE)\s+(https?://\S+)", msg, re.IGNORECASE
    )
    if rest_match:
        return {
            "tool_name": "call_api",
            "tool_args": {
                "method": rest_match.group(1).upper(),
                "url": rest_match.group(2),
                "headers": {},
                "body": None,
            },
            "intent_summary": f"Call {rest_match.group(1).upper()} {rest_match.group(2)}",
            "direct_response": None,
        }

    return {
        "tool_name": None,
        "tool_args": None,
        "intent_summary": "Direct response to non-tool query",
        "direct_response": (
            "I can help you query the database (SELECT), list tables, describe schemas, "
            "or call external REST APIs. Please rephrase your request."
        ),
    }


async def intent_analysis_node(state: BridgeState) -> BridgeState:
    try:
        parsed = await _groq_intent_analysis(state["user_message"])
    except Exception:
        parsed = _fallback_intent_analysis(state["user_message"])
        state["intent_summary"] = (
            f"[fallback] {parsed.get('intent_summary', '')}"
        )
        state["tool_name"] = parsed.get("tool_name")
        state["tool_args"] = parsed.get("tool_args")
        if parsed.get("direct_response"):
            state["final_response"] = parsed["direct_response"]
            state["tool_name"] = None
        return state

    state["intent_summary"] = parsed.get("intent_summary")
    state["tool_name"] = parsed.get("tool_name")
    state["tool_args"] = parsed.get("tool_args")

    if parsed.get("direct_response"):
        state["final_response"] = parsed["direct_response"]
        state["tool_name"] = None

    return state


async def permission_check_node(state: BridgeState) -> BridgeState:
    if state.get("final_response") or not state.get("tool_name"):
        return state

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM user_permissions WHERE agent_id = $1 AND tool_name = $2",
            state["agent_id"],
            state["tool_name"],
        )

    if not row:
        state["has_permission"] = False
        state["error_message"] = f"Agent '{state['agent_id']}' is not authorized to use tool '{state['tool_name']}'"
        return state

    state["has_permission"] = True
    state["risk_level"] = row["risk_level"]
    state["auto_approve"] = row["auto_approve"]

    tool_name = (state.get("tool_name") or "").lower()
    query = ""
    if state.get("tool_args"):
        query = (state["tool_args"].get("query") or "").upper()
    api_method = ""
    if state.get("tool_args"):
        api_method = (state["tool_args"].get("method") or "").upper()

    if any(kw in tool_name for kw in ["write", "insert", "update", "delete"]):
        state["risk_level"] = RiskLevel.HIGH
        state["auto_approve"] = False
        state["risk_reason"] = f"Tool '{tool_name}' is a write operation"
    elif any(kw in query for kw in ["DROP ", "TRUNCATE ", "ALTER ", "CREATE ", "INSERT ", "UPDATE ", "DELETE "]):
        state["risk_level"] = RiskLevel.HIGH
        state["auto_approve"] = False
        state["risk_reason"] = "Query contains destructive SQL operations"
    elif tool_name == "call_api":
        if api_method in ("POST", "PUT", "PATCH", "DELETE"):
            state["risk_level"] = RiskLevel.HIGH
            state["auto_approve"] = False
            state["risk_reason"] = f"{api_method} API calls can modify external resources"
        else:
            state["risk_level"] = RiskLevel.LOW if row["risk_level"] == "low" else RiskLevel.MEDIUM
            state["risk_reason"] = "Read-only API call"
    elif tool_name == "execute_query":
        if row["risk_level"] == "low":
            state["risk_level"] = RiskLevel.LOW
        else:
            state["risk_level"] = RiskLevel.MEDIUM
        state["risk_reason"] = "SELECT query execution"
    else:
        state["risk_level"] = RiskLevel.LOW
        state["risk_reason"] = "Read-only operation"

    if state["risk_level"] == RiskLevel.HIGH:
        state["auto_approve"] = False

    return state


async def hitl_gate_node(state: BridgeState) -> BridgeState:
    if state.get("final_response") or state.get("error_message"):
        return state

    if state.get("auto_approve", False):
        state["approval_status"] = ApprovalStatus.APPROVED
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_logs (session_id, agent_id, event_type, tool_name, tool_args, result_summary)
                   VALUES ($1, $2, 'auto_approved', $3, $4::jsonb, 'Auto-approved based on permission rules')""",
                state["session_id"], state["agent_id"], state["tool_name"],
                json.dumps(state["tool_args"] or {}),
            )
        return state

    timeout_minutes = settings.approval_timeout_minutes
    pool = await get_pool()
    async with pool.acquire() as conn:
        request_id = await conn.fetchval(
            """INSERT INTO approval_requests (session_id, agent_id, tool_name, tool_args, risk_level, risk_reason, status, expires_at)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6, 'pending', NOW() + ($7 || ' minutes')::INTERVAL)
               RETURNING id""",
            state["session_id"], state["agent_id"], state["tool_name"],
            json.dumps(state["tool_args"] or {}),
            state["risk_level"].value if hasattr(state["risk_level"], 'value') else state["risk_level"],
            state.get("risk_reason", ""),
            str(timeout_minutes),
        )
        request_id_str = str(request_id)

    state["approval_request_id"] = request_id_str
    state["approval_status"] = ApprovalStatus.PENDING

    await ws_manager.broadcast({
        "type": "new_approval",
        "data": {
            "id": request_id_str,
            "session_id": state["session_id"],
            "agent_id": state["agent_id"],
            "tool_name": state["tool_name"],
            "tool_args": state["tool_args"],
            "risk_level": state["risk_level"].value if hasattr(state["risk_level"], 'value') else state["risk_level"],
            "risk_reason": state.get("risk_reason", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    })

    from core.notifications import notify_pending_approval
    asyncio.ensure_future(notify_pending_approval(
        request_id=request_id_str,
        agent_id=state["agent_id"],
        tool_name=state["tool_name"],
        tool_args=state["tool_args"] or {},
        risk_level=state["risk_level"].value if hasattr(state["risk_level"], 'value') else str(state["risk_level"]),
        risk_reason=state.get("risk_reason"),
    ))

    return state


async def mcp_execution_node(state: BridgeState) -> BridgeState:
    if state["approval_status"] != ApprovalStatus.APPROVED:
        return state

    from mcp_servers.sql_server import execute_query, list_tables, describe_schema
    from mcp_servers.rest_server import call_api

    tool_name = state["tool_name"]
    args = state["tool_args"] or {}

    try:
        db_name = state.get("db_name")
        if tool_name == "execute_query":
            result = await execute_query(args.get("query", ""), args.get("limit", 100), db_name=db_name)
        elif tool_name == "list_tables":
            result = await list_tables(args.get("schema_name", "public"), db_name=db_name)
        elif tool_name == "describe_schema":
            result = await describe_schema(args.get("table_name", ""), args.get("schema_name", "public"), db_name=db_name)
        elif tool_name == "call_api":
            result = await call_api(
                method=args.get("method", "GET"),
                url=args.get("url", ""),
                headers=args.get("headers") or {},
                body=args.get("body"),
            )
        else:
            state["execution_error"] = f"Unknown tool: {tool_name}"
            state["final_response"] = f"Error: Unknown tool '{tool_name}'"
            return state

        state["tool_result"] = result
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."
        state["final_response"] = f"Results from {tool_name}:\n{result_str}"
    except Exception as e:
        state["execution_error"] = str(e)
        state["final_response"] = f"Execution error: {str(e)}"

    return state


async def audit_log_node(state: BridgeState) -> BridgeState:
    try:
        pool = await get_pool()
        has_error = bool(state.get("error_message") or state.get("execution_error"))

        if state.get("final_response") and not state.get("tool_name"):
            event_type = "direct_response"
        elif not state.get("has_permission") and state.get("error_message"):
            event_type = "permission_denied"
        elif state.get("approval_status") == ApprovalStatus.APPROVED and not state.get("auto_approve"):
            event_type = "approved_and_executed"
        elif state.get("auto_approve") and state.get("approval_status") == ApprovalStatus.APPROVED:
            event_type = "auto_approved"
        elif state.get("approval_status") == ApprovalStatus.DENIED:
            event_type = "denied"
        elif state.get("approval_status") == ApprovalStatus.TIMEOUT:
            event_type = "timeout"
        elif has_error:
            event_type = "error"
        elif state.get("approval_status") == ApprovalStatus.PENDING:
            event_type = "approval_requested"
        else:
            event_type = "completed"

        result_summary = state.get("final_response") or state.get("error_message") or ""
        if len(result_summary) > 1000:
            result_summary = result_summary[:1000]

        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_logs (session_id, agent_id, event_type, tool_name, tool_args, result_summary, approval_request_id, metadata)
                   VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8::jsonb)""",
                state["session_id"],
                state["agent_id"],
                event_type,
                state.get("tool_name"),
                json.dumps(state.get("tool_args") or {}),
                result_summary,
                state.get("approval_request_id"),
                json.dumps({
                    "risk_level": state.get("risk_level"),
                    "auto_approve": state.get("auto_approve"),
                    "has_permission": state.get("has_permission"),
                }),
            )
    except Exception:
        pass

    return state
