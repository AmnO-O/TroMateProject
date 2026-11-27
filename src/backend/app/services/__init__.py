"""Services: business rules, one class per use-case area (SCRUM-116, Figure 2).

Rules of the layer:
* Services hold the business logic; repositories only read and write rows.
* Services never import FastAPI or aiogram, and never touch ``AsyncSession`` directly:
  they open a ``UnitOfWork`` and commit once per use case.
* Errors are raised as ``app.services.errors`` types; routers map them to responses.
"""

from app.services.balance_service import (
    BalanceService,
    ExpenseRecord,
    MemberBalance,
    RoomBalances,
    SuggestedTransfer,
)
from app.services.debt_engine import Transfer, simplify_debts
from app.services.expense_parser import (
    ComputedSplit,
    ExpenseParser,
    MemberContext,
    ParsedExpense,
    normalize_vnd_amount,
)
from app.services.expense_service import (
    MANUAL_ONLY_CATEGORIES,
    CreatedExpense,
    CreatedSplitLine,
    ExpenseDraft,
    ExpenseService,
    resolve_auto_confirm_window,
)
from app.services.room_service import CategoryInfo, Membership, RoomService

__all__ = [
    "BalanceService",
    "CategoryInfo",
    "ComputedSplit",
    "CreatedExpense",
    "CreatedSplitLine",
    "ExpenseDraft",
    "ExpenseParser",
    "ExpenseRecord",
    "ExpenseService",
    "MANUAL_ONLY_CATEGORIES",
    "MemberBalance",
    "MemberContext",
    "Membership",
    "ParsedExpense",
    "RoomBalances",
    "RoomService",
    "SuggestedTransfer",
    "Transfer",
    "normalize_vnd_amount",
    "resolve_auto_confirm_window",
    "simplify_debts",
]
