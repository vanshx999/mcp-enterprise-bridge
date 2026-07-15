from graph.nodes import _fallback_intent_analysis


def test_fallback_select_query():
    result = _fallback_intent_analysis("SELECT * FROM users")
    assert result["tool_name"] == "execute_query"
    assert "SELECT * FROM users" in result["tool_args"]["query"]


def test_fallback_list_tables():
    result = _fallback_intent_analysis("list tables")
    assert result["tool_name"] == "list_tables"


def test_fallback_show_tables():
    result = _fallback_intent_analysis("show tables")
    assert result["tool_name"] == "list_tables"


def test_fallback_describe_schema():
    result = _fallback_intent_analysis("describe schema users")
    assert result["tool_name"] == "describe_schema"
    assert result["tool_args"]["table_name"] == "users"


def test_fallback_rest_api_get():
    result = _fallback_intent_analysis("GET https://api.github.com/repos/opencode-ai/opencode")
    assert result["tool_name"] == "call_api"
    assert result["tool_args"]["method"] == "GET"
    assert "api.github.com" in result["tool_args"]["url"]


def test_fallback_rest_api_post():
    result = _fallback_intent_analysis("POST https://httpbin.org/post")
    assert result["tool_name"] == "call_api"
    assert result["tool_args"]["method"] == "POST"


def test_fallback_direct_response():
    result = _fallback_intent_analysis("Hello, how are you?")
    assert result["tool_name"] is None
    assert result["direct_response"] is not None


def test_fallback_case_insensitive():
    result = _fallback_intent_analysis("SELECT NAME FROM EMPLOYEES")
    assert result["tool_name"] == "execute_query"
