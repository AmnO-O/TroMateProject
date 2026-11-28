from __future__ import annotations

import inspect
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint

from app.db.enums import MAX_REVIEW_WINDOW_MINUTES, MIN_REVIEW_WINDOW_MINUTES
from app.db.models import Base, Expense, LedgerEntry, Room
from app.repositories import LedgerRepository

EXPECTED_TABLES = {
    "users",
    "bank_accounts",
    "rooms",
    "room_members",
    "categories",
    "attachments",
    "expenses",
    "expense_deliveries",
    "expense_splits",
    "expense_approvals",
    "payments",
    "ledger_entries",
    "usage_events",
    "webhook_state",
}


def test_metadata_contains_every_table_with_scrum_122_names() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_expense_has_optimistic_locking_version_column() -> None:
    column = Expense.__table__.c.version
    assert not column.nullable
    assert column.server_default is not None
    assert column.server_default.arg.text == "1"


def test_money_columns_are_bigint_vnd() -> None:
    for table, column in [
        ("expenses", "total_amount"),
        ("expense_splits", "share_amount"),
        ("payments", "amount"),
        ("ledger_entries", "amount_delta"),
    ]:
        assert Base.metadata.tables[table].c[column].type.python_type is int


def test_ledger_repository_is_append_only() -> None:
    public = {
        name
        for name, _ in inspect.getmembers(LedgerRepository, inspect.isfunction)
        if not name.startswith("_")
    }
    mutating = {n for n in public if n.startswith(("update", "delete", "remove", "set", "edit"))}

    assert mutating == set()
    assert {"append", "append_many"} <= public


def test_ledger_entry_has_effective_and_created_timestamps() -> None:
    columns = LedgerEntry.__table__.c
    assert columns.effective_at.type.timezone
    assert columns.created_at.type.timezone


def test_review_window_bounds_v3() -> None:
    assert MIN_REVIEW_WINDOW_MINUTES == 1440
    assert MAX_REVIEW_WINDOW_MINUTES == 43200


def test_room_review_timeout_column_is_nullable_with_no_default() -> None:
    column = Room.__table__.c.review_timeout_minutes
    assert column.nullable is True
    assert column.server_default is None
    assert column.default is None or column.default.arg is None
    assert Room(telegram_chat_id=1, name="P302").review_timeout_minutes is None


def test_room_review_timeout_check_constraint_allows_null_or_1_to_30_days() -> None:
    constraints = {c.name: c for c in Room.__table__.constraints if isinstance(c, CheckConstraint)}
    ck = constraints["ck_rooms_review_timeout_allowed"]
    sql = str(ck.sqltext)
    assert "IS NULL" in sql
    assert "1440" in sql
    assert "43200" in sql


def test_alembic_single_head_for_v3_room_window() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["uc05soloshare"]
    assert script.get_revision("uc05soloshare").down_revision == "uc05creatorvote"
    assert script.get_revision("uc05creatorvote").down_revision == "uc05delivery"
    assert script.get_revision("uc05delivery").down_revision == "uc01uc05merge"
    assert set(script.get_revision("uc01uc05merge").down_revision) == {"124draft", "a3c7e91f4b20"}
    rev = script.get_revision("a3c7e91f4b20")
    assert rev is not None
    assert rev.down_revision == "bd5bbd1d9957"
