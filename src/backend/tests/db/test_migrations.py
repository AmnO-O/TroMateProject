from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.db.models import Base
from tests.db.conftest import pytestmark  # noqa: F401  (skip without TEST_DATABASE_URL)


async def test_migration_creates_every_table(engine) -> None:
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    assert set(Base.metadata.tables) | {"alembic_version"} == tables


async def test_models_and_migration_have_no_drift(engine) -> None:
    def diff(sync_conn):
        context = MigrationContext.configure(
            sync_conn, opts={"compare_type": True, "compare_server_default": True}
        )
        return compare_metadata(context, Base.metadata)

    async with engine.connect() as conn:
        assert await conn.run_sync(diff) == []


async def test_webhook_state_singleton_is_seeded(engine) -> None:
    async with engine.connect() as conn:
        rows = (await conn.execute(text("SELECT id, last_update_id FROM webhook_state"))).all()
    assert rows == [(1, 0)]
