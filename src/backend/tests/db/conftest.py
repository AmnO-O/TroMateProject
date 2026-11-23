"""Integration-test fixtures for the PostgreSQL layer.

Set ``TEST_DATABASE_URL`` to an empty, disposable database (a local PostgreSQL or a Neon
branch). Every run DROPS AND RECREATES its ``public`` schema. Tests here are skipped when
the variable is not set, and refuse to run against the application ``DATABASE_URL``.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command
from app.core.config import get_database_settings
from app.db.models import Base
from app.db.session import build_async_url, create_session_factory
from app.db.unit_of_work import UnitOfWork

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")


def _same_database(a: str, b: str) -> bool:
    if not a or not b:
        return False
    url_a, _ = build_async_url(a)
    url_b, _ = build_async_url(b)
    return (url_a.host, url_a.port, url_a.database) == (url_b.host, url_b.port, url_b.database)


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


def make_engine() -> AsyncEngine:
    url, connect_args = build_async_url(TEST_DATABASE_URL)
    return create_async_engine(url, poolclass=pool.NullPool, connect_args=connect_args)


async def _reset_schema() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> str:
    """Recreate the schema once per session and run every Alembic migration."""

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    if _same_database(TEST_DATABASE_URL, get_database_settings().database_url):
        pytest.exit("TEST_DATABASE_URL must not point at DATABASE_URL (tests erase it)", 2)
    asyncio.run(_reset_schema())
    command.upgrade(alembic_config(TEST_DATABASE_URL), "head")
    return TEST_DATABASE_URL


@pytest.fixture
async def engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = make_engine()
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            tables = ", ".join(
                t.name for t in Base.metadata.sorted_tables if t.name != "webhook_state"
            )
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture
def uow_factory(session_factory: async_sessionmaker[AsyncSession]):
    return lambda: UnitOfWork(session_factory)
