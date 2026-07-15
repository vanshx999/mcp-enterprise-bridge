from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse


MAX_BODY_SIZES: dict[str, int] = {
    "/api/auth/login": 1024,
    "/api/agent/query": 65536,
    "/api/agent/keys": 1024,
    "/api/permissions": 2048,
    "/api/approvals/": 1024,
}


class InputSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method in ("POST", "PUT", "PATCH"):
            path = request.url.path
            limit = 65536
            for prefix, size in MAX_BODY_SIZES.items():
                if path.startswith(prefix):
                    limit = size
                    break

            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Max {limit} bytes for this endpoint."},
                )

            body = await request.body()
            if len(body) > limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Max {limit} bytes for this endpoint."},
                )

        return await call_next(request)
