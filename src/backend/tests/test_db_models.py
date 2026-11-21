from __future__ import annotations

import inspect

from app.db.models import Base, Expense, LedgerEntry
from app.repositories import LedgerRepository

EXPECTED_TABLES = {
    "users",
    "bank_accounts",
    "rooms",
    "room_members",
    "categories",
    "attachments",
    "expenses",
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
