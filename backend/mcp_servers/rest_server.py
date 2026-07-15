import httpx
from typing import Any


ALLOWED_DOMAINS = {"api.github.com", "jsonplaceholder.typicode.com", "httpbin.org"}
MAX_RESPONSE_BYTES = 100_000


async def _validate_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_DOMAINS:
        allowed = ", ".join(sorted(ALLOWED_DOMAINS))
        raise ValueError(
            f"Domain '{parsed.hostname}' is not in the allowed list ({allowed})"
        )
    return url


async def call_api(method: str, url: str, headers: dict = None, body: Any = None) -> dict:
    validated_url = await _validate_url(url)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method=method.upper(),
            url=validated_url,
            headers=headers or {},
            json=body if body and method.upper() in ("POST", "PUT", "PATCH") else None,
        )
        content = response.text
        if len(content) > MAX_RESPONSE_BYTES:
            content = content[:MAX_RESPONSE_BYTES] + f"\n... (truncated, full response was {len(content)} bytes)"
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": content,
        }
