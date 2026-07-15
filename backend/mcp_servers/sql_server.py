import asyncpg
import sqlparse
from sqlparse import tokens as stokens
from core.database import get_pool


_DML_DDL = {stokens.DML, stokens.DDL}

_db_connection_cache: dict[str, asyncpg.Pool] = {}


async def _get_pool_for_db(db_name: str | None = None) -> asyncpg.Pool:
    if not db_name:
        return await get_pool()

    if db_name in _db_connection_cache:
        return _db_connection_cache[db_name]

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT connection_url FROM registered_databases WHERE name = $1 AND is_active = true",
            db_name,
        )
    if not row:
        raise ValueError(f"Unknown or inactive database: '{db_name}'")

    db_pool = await asyncpg.create_pool(
        row["connection_url"],
        min_size=1,
        max_size=5,
    )
    _db_connection_cache[db_name] = db_pool
    return db_pool


async def close_all_db_pools():
    for name, pool in _db_connection_cache.items():
        await pool.close()
    _db_connection_cache.clear()


def _check_read_only(tokens, depth=0) -> bool:
    for token in tokens:
        if token.is_whitespace:
            continue
        if token.ttype in (stokens.Comment.Single, stokens.Comment.Multi):
            continue

        if token.ttype is stokens.Punctuation:
            if token.value == "(":
                inner = _check_read_only(token.tokens if hasattr(token, "tokens") else [], depth + 1)
                if not inner:
                    return False
                continue
            elif token.value == ")":
                continue

        if (
            token.ttype in _DML_DDL
            and depth == 0
            and token.value.upper() not in ("SELECT", "VALUES", "TABLE", "EXPLAIN")
        ):
            return False

        if hasattr(token, "tokens"):
            inner = _check_read_only(token.tokens, depth)
            if not inner:
                return False

    return True


def _is_read_only_statement(stmt: sqlparse.sql.Statement) -> bool:
    non_ws = [
        t for t in stmt.tokens
        if not t.is_whitespace and t.ttype not in (stokens.Comment.Single, stokens.Comment.Multi)
    ]
    if not non_ws:
        return True

    first_val = non_ws[0].value.upper().lstrip("(")
    if first_val not in ("SELECT", "VALUES", "TABLE", "EXPLAIN", "WITH"):
        return False

    return _check_read_only(stmt.tokens)


async def _validate_read_only(query: str):
    parsed = sqlparse.parse(query)
    if not parsed:
        raise ValueError("Empty or unparseable SQL query")

    for statement in parsed:
        if not _is_read_only_statement(statement):
            raise ValueError(
                "Only SELECT queries are permitted. Write operations (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, CALL) are blocked."
            )


async def execute_query(query: str, limit: int = 100, db_name: str | None = None) -> list[dict]:
    await _validate_read_only(query)
    limit = min(limit, 1000)
    pool = await _get_pool_for_db(db_name)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query + f" LIMIT {limit}")
        if rows:
            columns = [k for k in rows[0].keys()]
            return [dict(zip(columns, row)) for row in rows]
        return []


async def list_tables(schema_name: str = "public", db_name: str | None = None) -> list[dict]:
    pool = await _get_pool_for_db(db_name)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                table_name,
                (SELECT reltuples::bigint AS row_count
                 FROM pg_class
                 WHERE oid = (quote_ident($1) || '.' || quote_ident(table_name))::regclass
                ) AS row_count
            FROM information_schema.tables
            WHERE table_schema = $1 AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            schema_name,
        )
        return [dict(row) for row in rows]


async def describe_schema(table_name: str, schema_name: str = "public", db_name: str | None = None) -> list[dict]:
    pool = await _get_pool_for_db(db_name)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = $1 AND table_schema = $2
            ORDER BY ordinal_position
            """,
            table_name,
            schema_name,
        )
        return [dict(row) for row in rows]
