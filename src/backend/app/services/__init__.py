"""Services: business rules, one class per use-case area (SCRUM-116, Figure 2).

Rules of the layer:
* Services hold the business logic; repositories only read and write rows.
* Services never import FastAPI or aiogram, and never touch ``AsyncSession`` directly:
  they open a ``UnitOfWork`` and commit once per use case.
* Errors are raised as ``app.services.errors`` types; routers map them to responses.
"""

from app.services.expense_parser import (
    ComputedSplit,
    ExpenseParser,
    MemberContext,
    ParsedExpense,
    normalize_vnd_amount,
)
from app.services.expense_service import CreatedExpense, CreatedSplitLine, ExpenseService
from app.services.room_service import CategoryInfo, Membership, RoomService

__all__ = [
    "CategoryInfo",
    "ComputedSplit",
    "CreatedExpense",
    "CreatedSplitLine",
    "ExpenseParser",
    "ExpenseService",
    "MemberContext",
    "Membership",
    "ParsedExpense",
    "RoomService",
    "normalize_vnd_amount",
]
