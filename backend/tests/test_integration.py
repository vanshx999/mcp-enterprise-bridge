import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from graph.state import BridgeState
from graph.workflow import graph


@pytest.fixture
def base_state():
    return BridgeState(
        session_id="test-session-123",
        agent_id="default-agent",
        db_name=None,
        user_message="",
        tool_name=None,
        tool_args=None,
        intent_summary=None,
        has_permission=None,
        risk_level=None,
        risk_reason=None,
        auto_approve=None,
        approval_request_id=None,
        approval_status=None,
        reviewer_note=None,
        tool_result=None,
        execution_error=None,
        final_response=None,
        error_message=None,
    )


class TestDirectResponseFlow:
    @patch("graph.nodes._groq_intent_analysis")
    async def test_greeting(self, mock_groq, base_state):
        base_state["user_message"] = "hello"
        mock_groq.return_value = {
            "tool_name": None,
            "tool_args": None,
            "intent_summary": "Direct response",
            "direct_response": "Hi! How can I help you?",
        }

        result = await graph.ainvoke(base_state, {"configurable": {"thread_id": "test-dr-greeting"}})

        assert result["final_response"] == "Hi! How can I help you?"
        assert result["tool_name"] is None

    @patch("graph.nodes._groq_intent_analysis")
    @patch("graph.nodes.get_pool", new_callable=AsyncMock)
    async def test_groq_failure_fallthrough(self, mock_get_pool, mock_groq, base_state):
        mock_groq.side_effect = Exception("Groq API down")
        base_state["user_message"] = "SELECT COUNT(*) FROM orders"

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_conn.fetchval.return_value = None
        mock_conn.execute.return_value = None
        acquire_ctx = MagicMock()
        acquire_ctx.__aenter__.return_value = mock_conn
        acquire_ctx.__aexit__.return_value = None
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = acquire_ctx
        mock_get_pool.return_value = mock_pool

        result = await graph.ainvoke(base_state, {"configurable": {"thread_id": "test-dr-fallback"}})

        assert "fallback" in result.get("intent_summary", "")
        assert result["tool_name"] == "execute_query"


class TestPermissionCheck:
    @patch("graph.nodes._groq_intent_analysis")
    @patch("graph.nodes.get_pool", new_callable=AsyncMock)
    async def test_no_permission(self, mock_get_pool, mock_groq, base_state):
        mock_groq.return_value = {
            "tool_name": "execute_query",
            "tool_args": {"query": "SELECT 1"},
            "intent_summary": "SELECT query",
            "direct_response": None,
        }
        base_state["user_message"] = "SELECT 1"

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_conn.fetchval.return_value = None
        mock_conn.execute.return_value = None
        acquire_ctx = MagicMock()
        acquire_ctx.__aenter__.return_value = mock_conn
        acquire_ctx.__aexit__.return_value = None
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = acquire_ctx
        mock_get_pool.return_value = mock_pool

        result = await graph.ainvoke(base_state, {"configurable": {"thread_id": "test-tc-noperm"}})

        assert "not authorized" in (result.get("error_message") or "").lower()
        assert result.get("has_permission") is False

    @patch("graph.nodes._groq_intent_analysis")
    @patch("graph.nodes.get_pool", new_callable=AsyncMock)
    @patch("mcp_servers.sql_server.execute_query")
    async def test_select_auto_approve(self, mock_exec, mock_get_pool, mock_groq, base_state):
        mock_groq.return_value = {
            "tool_name": "execute_query",
            "tool_args": {"query": "SELECT * FROM users", "limit": 100},
            "intent_summary": "SELECT query",
            "direct_response": None,
        }
        base_state["user_message"] = "SELECT * FROM users"
        mock_exec.return_value = [{"id": 1, "name": "Alice"}]

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "agent_id": "default-agent",
            "tool_name": "execute_query",
            "risk_level": "low",
            "auto_approve": True,
        }
        mock_conn.fetchval.return_value = None
        mock_conn.execute.return_value = None
        acquire_ctx = MagicMock()
        acquire_ctx.__aenter__.return_value = mock_conn
        acquire_ctx.__aexit__.return_value = None
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = acquire_ctx
        mock_get_pool.return_value = mock_pool

        result = await graph.ainvoke(base_state, {"configurable": {"thread_id": "test-tc-select"}})

        assert result.get("final_response") is not None
        assert "Alice" in result["final_response"]


class TestFallbackParsing:
    def test_select_sql(self, base_state):
        from graph.nodes import _fallback_intent_analysis
        result = _fallback_intent_analysis("SELECT name FROM employees WHERE dept = 'eng'")
        assert result["tool_name"] == "execute_query"
        assert "employees" in result["tool_args"]["query"]

    def test_list_tables_keywords(self, base_state):
        from graph.nodes import _fallback_intent_analysis
        assert _fallback_intent_analysis("list tables")["tool_name"] == "list_tables"
        assert _fallback_intent_analysis("show tables")["tool_name"] == "list_tables"
        assert _fallback_intent_analysis("SHOW TABLES")["tool_name"] == "list_tables"

    def test_describe_schema(self, base_state):
        from graph.nodes import _fallback_intent_analysis
        result = _fallback_intent_analysis("describe schema users")
        assert result["tool_name"] == "describe_schema"
        assert result["tool_args"]["table_name"] == "users"

    def test_rest_api(self, base_state):
        from graph.nodes import _fallback_intent_analysis
        result = _fallback_intent_analysis("GET https://api.github.com/repos/user/repo")
        assert result["tool_name"] == "call_api"
        assert result["tool_args"]["method"] == "GET"

    def test_direct_response(self, base_state):
        from graph.nodes import _fallback_intent_analysis
        result = _fallback_intent_analysis("What is the capital of France?")
        assert result["tool_name"] is None
        assert result["direct_response"] is not None
