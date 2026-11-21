"""Check that DATABASE_URL is reachable and show the applied Alembic revision.

Usage (from src/backend):
    uv run python scripts/check_db.py
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.db.session import dispose_engine, get_engine


async def main() -> int:
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            version = await conn.scalar(text("SHOW server_version"))
            database = await conn.scalar(text("SELECT current_database()"))
            has_alembic = await conn.scalar(text("SELECT to_regclass('alembic_version')"))
            revision = (
                await conn.scalar(text("SELECT version_num FROM alembic_version"))
                if has_alembic
                else None
            )
    except Exception as exc:  # noqa: BLE001 - report any connection problem to the user
        print(f"Connection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()

    print(f"Connected to '{database}' (PostgreSQL {version}) at {engine.url.host}")
    print(f"Alembic revision: {revision or 'none - run: uv run alembic upgrade head'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
