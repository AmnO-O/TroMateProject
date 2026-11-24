"""Services: business rules, one class per use-case area (SCRUM-116, Figure 2).

Rules of the layer:
* Services hold the business logic; repositories only read and write rows.
* Services never import FastAPI or aiogram, and never touch ``AsyncSession`` directly:
  they open a ``UnitOfWork`` and commit once per use case.
* Errors are raised as ``app.services.errors`` types; routers map them to responses.

Planned services: ``ExpenseParser`` (SCRUM-123), ``ExpenseService`` (SCRUM-124),
``DebtEngine`` (SCRUM-125).
"""

from app.services.expense_parser import (
    ComputedSplit,
    ExpenseParser,
    ExtractionPayload,
    MemberContext,
    ParsedExpense,
    normalize_vnd_amount,
)
from app.services.room_service import CategoryInfo, Membership, RoomService

__all__ = [
    "CategoryInfo",
    "ComputedSplit",
    "ExpenseParser",
    "ExtractionPayload",
    "MemberContext",
    "Membership",
    "ParsedExpense",
    "RoomService",
    "normalize_vnd_amount",
]
