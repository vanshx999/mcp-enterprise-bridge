import pytest
from mcp_servers.sql_server import _validate_read_only, _is_read_only_statement
import sqlparse


@pytest.mark.asyncio
async def test_allow_simple_select():
    await _validate_read_only("SELECT * FROM users")
    await _validate_read_only("SELECT id, name FROM products WHERE price > 10")
    await _validate_read_only("SELECT count(*) FROM orders GROUP BY status")


@pytest.mark.asyncio
async def test_allow_cte():
    await _validate_read_only(
        "WITH active AS (SELECT * FROM users WHERE is_active = true) SELECT * FROM active"
    )


@pytest.mark.asyncio
async def test_allow_explain():
    await _validate_read_only("EXPLAIN SELECT * FROM users")


@pytest.mark.asyncio
async def test_block_insert():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("INSERT INTO users (name) VALUES ('test')")


@pytest.mark.asyncio
async def test_block_update():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("UPDATE users SET name = 'test' WHERE id = 1")


@pytest.mark.asyncio
async def test_block_delete():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("DELETE FROM users WHERE id = 1")


@pytest.mark.asyncio
async def test_block_drop():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("DROP TABLE users")


@pytest.mark.asyncio
async def test_block_alter():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("ALTER TABLE users ADD COLUMN foo TEXT")


@pytest.mark.asyncio
async def test_block_create():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("CREATE TABLE foo (id INT)")


@pytest.mark.asyncio
async def test_block_truncate():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("TRUNCATE TABLE users")


@pytest.mark.asyncio
async def test_block_multi_statement():
    with pytest.raises(ValueError, match="Only SELECT queries are permitted"):
        await _validate_read_only("SELECT * FROM users; DROP TABLE users")


def test_is_read_only_statement():
    assert _is_read_only_statement(sqlparse.parse("SELECT * FROM foo")[0])
    assert _is_read_only_statement(sqlparse.parse("WITH x AS (SELECT 1) SELECT * FROM x")[0])
    assert not _is_read_only_statement(sqlparse.parse("INSERT INTO foo VALUES (1)")[0])
    assert not _is_read_only_statement(sqlparse.parse("DELETE FROM foo")[0])
