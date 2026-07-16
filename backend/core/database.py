import asyncio
import socket
import re
import asyncpg
from core.config import settings
from core.logging import logger

pool: asyncpg.Pool | None = None


async def _resolve_db_host(url: str) -> str:
    m = re.match(r".*@([^:/]+)", url)
    if not m:
        return url
    host = m.group(1)
    def _resolve_first(h: str) -> str | None:
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                ips = socket.getaddrinfo(h, 5432, family)
                return ips[0][4][0]
            except Exception:
                continue
        return None
    ip = await asyncio.to_thread(_resolve_first, host)
    if ip:
        logger.info(f"Resolved DB host to IP: {ip}")
        if ":" in ip:
            ip = f"[{ip}]"
        return url.replace("@" + host, "@" + ip)
    logger.warning(f"Could not resolve DB host: {host}")
    return url


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        url = settings.database_url
        ssl = None
        if settings.render or "sslmode=require" in url:
            url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            ssl = "require"
        url = await _resolve_db_host(url)
        pool = await asyncpg.create_pool(
            url, min_size=2, max_size=10, ssl=ssl
        )
    return pool


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


async def init_db():
    p = await get_pool()
    for attempt in range(5):
        try:
            async with p.acquire() as conn:
                await conn.fetchval("SELECT 1")
            break
        except Exception:
            if attempt < 4:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
    async with p.acquire() as conn:
        await conn.execute(
            """
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(50) DEFAULT 'approver',
                is_active BOOLEAN DEFAULT true,
                password_change_required BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS user_permissions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                agent_id VARCHAR(255) NOT NULL,
                tool_name VARCHAR(255) NOT NULL,
                resource_pattern TEXT DEFAULT '*',
                risk_level VARCHAR(20) DEFAULT 'low',
                auto_approve BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(agent_id, tool_name)
            );

            CREATE TABLE IF NOT EXISTS approval_requests (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_id VARCHAR(255) NOT NULL,
                agent_id VARCHAR(255) NOT NULL,
                tool_name VARCHAR(255) NOT NULL,
                tool_args JSONB NOT NULL,
                risk_level VARCHAR(20) NOT NULL,
                risk_reason TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                reviewed_by UUID REFERENCES users(id),
                reviewed_at TIMESTAMPTZ,
                reviewer_note TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '10 minutes')
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_id VARCHAR(255) NOT NULL,
                agent_id VARCHAR(255),
                event_type VARCHAR(100) NOT NULL,
                tool_name VARCHAR(255),
                tool_args JSONB,
                result_summary TEXT,
                approval_request_id UUID REFERENCES approval_requests(id),
                ip_address INET,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS session_states (
                session_id VARCHAR(255) PRIMARY KEY,
                agent_id VARCHAR(255) NOT NULL,
                graph_state JSONB NOT NULL,
                current_node VARCHAR(100),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
            CREATE INDEX IF NOT EXISTS idx_approval_requests_session ON approval_requests(session_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_session ON audit_logs(session_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);

            CREATE TABLE IF NOT EXISTS registered_databases (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(255) UNIQUE NOT NULL,
                connection_url TEXT NOT NULL,
                db_type VARCHAR(50) DEFAULT 'postgresql',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS approval_templates (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                tool_name VARCHAR(255) NOT NULL,
                resource_pattern TEXT DEFAULT '*',
                risk_level VARCHAR(20) DEFAULT 'medium',
                auto_approve BOOLEAN DEFAULT false,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS query_templates (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(255) NOT NULL,
                description TEXT DEFAULT '',
                query_text TEXT NOT NULL,
                parameters JSONB DEFAULT '[]',
                agent_id VARCHAR(255),
                created_by UUID REFERENCES users(id),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS agent_api_keys (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                agent_id VARCHAR(255) NOT NULL,
                key_hash TEXT NOT NULL,
                key_prefix VARCHAR(8) NOT NULL,
                label VARCHAR(255) DEFAULT '',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_used_at TIMESTAMPTZ
            );
            """
        )

        from core.security import hash_password

        existing_user = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE email = 'admin@mcpbridge.io'"
        )
        await conn.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS password_change_required BOOLEAN DEFAULT false
        """)

        if existing_user == 0:
            await conn.execute(
                """
                INSERT INTO users (email, hashed_password, full_name, role, password_change_required)
                VALUES ($1, $2, 'Admin', 'admin', true)
                """,
                "admin@mcpbridge.io",
                hash_password("admin123"),
            )
            await conn.execute(
                """
                INSERT INTO users (email, hashed_password, full_name, role, password_change_required)
                VALUES ($1, $2, 'Approver', 'approver', true)
                """,
                "approver@mcpbridge.io",
                hash_password("approver123"),
            )

        existing_perms = await conn.fetchval(
            "SELECT COUNT(*) FROM user_permissions WHERE agent_id = 'default-agent'"
        )
        if existing_perms == 0:
            await conn.execute(
                """
                INSERT INTO user_permissions (agent_id, tool_name, risk_level, auto_approve)
                VALUES
                    ('default-agent', 'execute_query', 'medium', false),
                    ('default-agent', 'list_tables', 'low', true),
                    ('default-agent', 'describe_schema', 'low', true),
                    ('default-agent', 'call_api', 'medium', false)
                ON CONFLICT (agent_id, tool_name) DO NOTHING
                """
            )

        existing_key_count = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_api_keys"
        )
        if existing_key_count == 0:
            import secrets
            raw_key = "mcp_sk_" + secrets.token_urlsafe(32)
            await conn.execute(
                """
                INSERT INTO agent_api_keys (agent_id, key_hash, key_prefix, label)
                VALUES ($1, $2, $3, 'default-dev-key')
                """,
                "default-agent",
                hash_password(raw_key),
                raw_key[:8],
            )
            from core.logging import logger
            logger.info(f"Default dev agent key: {raw_key}")
