from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import time

router = APIRouter(tags=["metrics"])

requests_total = Counter(
    "mcp_bridge_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

requests_duration = Histogram(
    "mcp_bridge_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

agent_queries_total = Counter(
    "mcp_bridge_agent_queries_total",
    "Total agent queries",
    ["agent_id", "result"],
)

approval_requests_total = Counter(
    "mcp_bridge_approval_requests_total",
    "Total approval requests",
    ["status"],
)


@router.get("/api/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
