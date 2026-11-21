from __future__ import annotations

import pytest

from app.db.session import DatabaseNotConfiguredError, build_async_url


def test_neon_libpq_url_is_converted_to_asyncpg() -> None:
    url, connect_args = build_async_url(
        "postgresql://alex:secret@ep-cool-darkness-123456.ap-southeast-1.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )

    assert url.drivername == "postgresql+asyncpg"
    assert url.username == "alex"
    assert url.password == "secret"
    assert url.database == "neondb"
    assert dict(url.query) == {"ssl": "require"}
    assert connect_args == {}


def test_pooled_neon_endpoint_disables_prepared_statement_cache() -> None:
    url, connect_args = build_async_url(
        "postgresql://u:p@ep-cool-darkness-123456-pooler.ap-southeast-1.aws.neon.tech/neondb"
        "?sslmode=require"
    )

    assert url.query["prepared_statement_cache_size"] == "0"
    assert connect_args["statement_cache_size"] == 0
    name_func = connect_args["prepared_statement_name_func"]
    assert name_func() != name_func()


@pytest.mark.parametrize(
    "raw",
    [
        "postgres://u:p@localhost/db",
        "postgresql+psycopg://u:p@localhost/db",
        "postgresql+asyncpg://u:p@localhost/db",
    ],
)
def test_postgres_driver_variants_use_asyncpg(raw: str) -> None:
    url, _ = build_async_url(raw)
    assert url.drivername == "postgresql+asyncpg"


def test_explicit_ssl_parameter_is_kept() -> None:
    url, _ = build_async_url("postgresql+asyncpg://u:p@host/db?ssl=verify-full&sslmode=require")
    assert dict(url.query) == {"ssl": "verify-full"}


def test_sslmode_disable_does_not_force_ssl() -> None:
    url, _ = build_async_url("postgresql://u:p@localhost/db?sslmode=disable")
    assert "ssl" not in url.query


def test_missing_database_url_raises_clear_error() -> None:
    with pytest.raises(DatabaseNotConfiguredError, match="DATABASE_URL"):
        build_async_url("")


def test_non_postgres_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        build_async_url("sqlite+aiosqlite:///tromate.db")
