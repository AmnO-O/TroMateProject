"""Async engine and session factory for PostgreSQL (Neon) via asyncpg."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseSettings, get_database_settings

ASYNC_DRIVER = "postgresql+asyncpg"

# libpq query parameters that asyncpg does not accept as connect() keywords.
_LIBPQ_ONLY_PARAMS = ("sslmode", "channel_binding")
_SSL_MODES = {"require", "verify-ca", "verify-full", "prefer", "allow"}


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when the database is used but ``DATABASE_URL`` is empty."""


def build_async_url(raw_url: str) -> tuple[URL, dict[str, Any]]:
    """Turn a Neon/libpq connection string into an asyncpg URL plus ``connect_args``.

    * ``postgresql://`` / ``postgres://`` / ``postgresql+psycopg://`` -> ``postgresql+asyncpg://``
    * ``sslmode=require`` -> ``ssl=require`` (asyncpg rejects ``sslmode``)
    * ``channel_binding`` is dropped (asyncpg negotiates SCRAM itself)
    * Neon pooled endpoints (``-pooler`` in the host) run PgBouncer in transaction mode,
      so prepared-statement caching is disabled and statement names are made unique.
    """

    if not raw_url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL is not set. Copy .env.example to .env and paste the Neon "
            "connection string."
        )

    url = make_url(raw_url)
    if url.drivername == "postgres":  # Heroku-style alias that SQLAlchemy does not register
        url = url.set(drivername="postgresql")
    if url.get_backend_name() != "postgresql":
        raise ValueError(f"Only PostgreSQL is supported, got '{url.drivername}'")

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    for param in _LIBPQ_ONLY_PARAMS:
        query.pop(param, None)
    if sslmode in _SSL_MODES and "ssl" not in query:
        query["ssl"] = sslmode

    connect_args: dict[str, Any] = {}
    if url.host and "-pooler" in url.host:
        query.setdefault("prepared_statement_cache_size", "0")
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = _unique_statement_name

    return url.set(drivername=ASYNC_DRIVER, query=query), connect_args


def _unique_statement_name() -> str:
    return f"__asyncpg_{uuid.uuid4()}__"


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    url, connect_args = build_async_url(settings.database_url)
    return create_async_engine(
        url,
        echo=settings.database_echo,
        connect_args=connect_args,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        # Neon scales to zero and closes idle connections: test before use, recycle early.
        pool_pre_ping=True,
        pool_recycle=300,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: objects stay readable after commit without implicit async IO.
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide engine, creating it on first use."""

    global _engine
    if _engine is None:
        _engine = create_engine(get_database_settings())
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""

    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


async def warmup_engine() -> None:
    """Run ``SELECT 1`` on startup to warm the Neon TCP/TLS pool before first request."""

    if not get_database_settings().database_url:
        return
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    """Close pooled connections (call on application shutdown)."""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
