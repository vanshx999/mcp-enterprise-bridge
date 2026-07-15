import os
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/mcp_bridge"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    jwt_secret_key: str = "your-super-secret-key-min-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    backend_port: int = 8000
    allowed_origins: str = "https://localhost,http://localhost:5173,http://localhost:3000"
    environment: str = "development"
    redis_url: str = "redis://localhost:6379"
    approval_timeout_minutes: int = 10
    jwt_secret_key_file: Optional[str] = None
    groq_api_key_file: Optional[str] = None

    sso_issuer_url: Optional[str] = None
    sso_client_id: Optional[str] = None
    sso_client_secret: Optional[str] = None
    sso_provider: str = "auth0"
    sso_scope: str = "openid email profile"
    frontend_url: str = "http://localhost:5173"
    render: bool = False

    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1
    otel_service_name: str = "mcp-enterprise-bridge"
    otel_endpoint: Optional[str] = None
    audit_log_retention_days: int = 90
    slack_webhook_url: Optional[str] = None

    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "noreply@mcpbridge.io"
    notification_email_to: Optional[str] = None

    smtp_password_file: Optional[str] = None

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.sentry_dsn)

    @property
    def otel_enabled(self) -> bool:
        return bool(self.otel_endpoint)

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def sso_enabled(self) -> bool:
        return bool(self.sso_issuer_url and self.sso_client_id and self.sso_client_secret)

    @property
    def effective_jwt_secret(self) -> str:
        if self.jwt_secret_key_file:
            path = self.jwt_secret_key_file
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().strip()
        return self.jwt_secret_key

    @property
    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.notification_email_to)

    @property
    def effective_smtp_password(self) -> str:
        if self.smtp_password_file:
            return self._read_secret(self.smtp_password_file)
        return self.smtp_password or ""

    @property
    def effective_groq_api_key(self) -> str:
        if self.groq_api_key_file:
            path = self.groq_api_key_file
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().strip()
        return self.groq_api_key

    @staticmethod
    def _read_secret(path: str) -> str:
        try:
            with open(path) as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError):
            return ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
