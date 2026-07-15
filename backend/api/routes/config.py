from fastapi import APIRouter, Depends
from core.config import settings
from api.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/validate")
async def validate_config(current_user: dict = Depends(get_current_user)):
    checks = []

    jwt_ok = len(settings.effective_jwt_secret) >= 32
    checks.append({
        "check": "jwt_secret_length",
        "status": "pass" if jwt_ok else "fail",
        "message": "JWT secret must be at least 32 characters",
    })

    groq_key_ok = settings.effective_groq_api_key.startswith("gsk_") if settings.effective_groq_api_key else False
    checks.append({
        "check": "groq_api_key",
        "status": "pass" if groq_key_ok else "warn",
        "message": "GROQ_API_KEY missing or invalid format (should start with gsk_)",
    })

    db_url_ok = settings.database_url.startswith("postgresql://")
    checks.append({
        "check": "database_url",
        "status": "pass" if db_url_ok else "fail",
        "message": "DATABASE_URL must be a valid PostgreSQL connection string",
    })

    redis_url_ok = settings.redis_url.startswith("redis://")
    checks.append({
        "check": "redis_url",
        "status": "pass" if redis_url_ok else "fail",
        "message": "REDIS_URL must be a valid Redis connection string",
    })

    origins = settings.origins_list
    origins_ok = all(o.startswith("https://") or o.startswith("http://") for o in origins)
    checks.append({
        "check": "allowed_origins",
        "status": "pass" if origins_ok else "fail",
        "message": f"ALLOWED_ORIGINS must contain valid URLs: {settings.allowed_origins}",
    })

    env_ok = settings.environment in ("development", "production")
    checks.append({
        "check": "environment",
        "status": "pass" if env_ok else "fail",
        "message": f"ENVIRONMENT must be 'development' or 'production', got '{settings.environment}'",
    })

    if settings.sentry_dsn:
        checks.append({
            "check": "sentry_dsn",
            "status": "pass" if settings.sentry_dsn.startswith("https://") else "warn",
            "message": "SENTRY_DSN should start with https://",
        })

    if settings.slack_webhook_url:
        checks.append({
            "check": "slack_webhook_url",
            "status": "pass" if settings.slack_webhook_url.startswith("https://hooks.slack.com") else "warn",
            "message": "SLACK_WEBHOOK_URL should be a valid Slack webhook URL",
        })

    if settings.sso_enabled:
        checks.append({
            "check": "sso_issuer_url",
            "status": "pass" if settings.sso_issuer_url else "fail",
            "message": "SSO_ISSUER_URL is required when SSO is enabled",
        })
        checks.append({
            "check": "sso_client_id",
            "status": "pass" if settings.sso_client_id else "fail",
            "message": "SSO_CLIENT_ID is required when SSO is enabled",
        })
        checks.append({
            "check": "sso_client_secret",
            "status": "pass" if settings.sso_client_secret else "fail",
            "message": "SSO_CLIENT_SECRET is required when SSO is enabled",
        })

    failures = [c for c in checks if c["status"] == "fail"]
    warnings = [c for c in checks if c["status"] == "warn"]

    return {
        "status": "ok" if not failures else "error",
        "summary": {
            "total": len(checks),
            "passed": len([c for c in checks if c["status"] == "pass"]),
            "warnings": len(warnings),
            "failures": len(failures),
        },
        "checks": checks,
    }
