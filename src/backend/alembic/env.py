"""Alembic environment for TroMate (async SQLAlchemy + asyncpg).

The database URL comes from, in order:
1. ``config.attributes["database_url"]`` (set programmatically, e.g. by tests),
2. ``-x database_url=...`` on the command line,
3. ``DATABASE_URL`` from the environment or ``src/backend/.env``.

Neon URLs (``postgresql://...?sslmode=require``) are converted by ``build_async_url``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_database_settings
from app.db.models import Base
from app.db.session import build_async_url

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return (
        config.attributes.get("database_url")
        or context.get_x_argument(as_dictionary=True).get("database_url")
        or get_database_settings().database_url
    )


def _configure(**kwargs: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout (``alembic upgrade head --sql``) without connecting."""

    url, _ = build_async_url(_database_url())
    _configure(
        url=url.render_as_string(hide_password=False),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url, connect_args = build_async_url(_database_url())
    engine = create_async_engine(url, poolclass=pool.NullPool, connect_args=connect_args)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
