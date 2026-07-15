from datetime import datetime, timezone, timedelta
from core.database import get_pool
from core.config import settings
from core.logging import logger


async def cleanup_expired_audit_logs(dry_run: bool = False) -> dict:
    pool = await get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)

    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM audit_logs WHERE created_at < $1",
            cutoff,
        )

        if dry_run:
            return {"dry_run": True, "deletable_count": count, "cutoff_date": cutoff.isoformat()}

        if count > 0:
            await conn.execute(
                "DELETE FROM audit_logs WHERE created_at < $1",
                cutoff,
            )
            logger.info(f"Cleaned up {count} audit log entries older than {cutoff.date()}")

    return {"deleted_count": count, "cutoff_date": cutoff.isoformat()}
