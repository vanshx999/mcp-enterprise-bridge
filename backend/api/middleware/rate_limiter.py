from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def _rate_limit_key(request: Request) -> str:
    agent_key = request.headers.get("X-Agent-Key", "")
    if agent_key:
        prefix = agent_key[:16]
        return f"agent:{prefix}"
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
