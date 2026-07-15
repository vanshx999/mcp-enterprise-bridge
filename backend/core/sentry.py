import sentry_sdk
from core.config import settings
from core.logging import logger


def init_sentry() -> None:
    if not settings.sentry_enabled:
        logger.info("Sentry disabled — no DSN configured")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )
    logger.info("Sentry initialized")
