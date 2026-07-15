import pytest
from mcp_servers.rest_server import _validate_url


@pytest.mark.asyncio
async def test_allow_allowed_domain():
    url = await _validate_url("https://api.github.com/repos/opencode-ai/opencode")
    assert url == "https://api.github.com/repos/opencode-ai/opencode"


@pytest.mark.asyncio
async def test_allow_jsonplaceholder():
    url = await _validate_url("https://jsonplaceholder.typicode.com/posts/1")
    assert url == "https://jsonplaceholder.typicode.com/posts/1"


@pytest.mark.asyncio
async def test_allow_httpbin():
    url = await _validate_url("https://httpbin.org/get")
    assert url == "https://httpbin.org/get"


@pytest.mark.asyncio
async def test_block_unknown_domain():
    with pytest.raises(ValueError, match="not in the allowed list"):
        await _validate_url("https://example.com/api")


@pytest.mark.asyncio
async def test_block_internal_ip():
    with pytest.raises(ValueError, match="not in the allowed list"):
        await _validate_url("http://127.0.0.1:8000/secret")
