import redis.asyncio as redis
from core.config import settings
from core.logging import logger

redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    global redis_client
    if redis_client is not None:
        return redis_client
    if not settings.redis_url:
        return None
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            max_connections=10,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True,
        )
        await redis_client.ping()
        return redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable (non-fatal): {e}")
        redis_client = None
        return None


async def close_redis():
    global redis_client
    if redis_client:
        try:
            await redis_client.aclose()
        except Exception:
            pass
        redis_client = None


async def check_redis_health() -> bool:
    try:
        client = await get_redis()
        if client is None:
            return False
        await client.ping()
        return True
    except Exception:
        return False
