import pytest

from app.services.errors import ConflictError, PermissionDeniedError
from app.services.expense_service import ExpenseService
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import CHAT_ID, make_expense, make_room


async def test_review_revision_and_ledger(uow_factory):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)

    async def review(user, action, version, **kwargs):
        return await service.review(
            telegram_chat_id=CHAT_ID,
            telegram_user_id=user,
            expense_id=expense.id,
            action=action,
            version=version,
            **kwargs,
        )

    with pytest.raises(PermissionDeniedError):
        await review(4, "agree", 1)
    assert (await review(3, "agree", 1)).agreed_count == 1
    disputed = await review(2, "reject", 1)
    assert disputed.status == "DISPUTED"
    revised = await review(1, "edit", disputed.version, description="Updated groceries")
    assert revised.description == "Updated groceries"
    assert revised.agreed_count == 1
    with pytest.raises(ConflictError):
        await review(3, "agree", 1)
    assert (await review(2, "agree", revised.version)).status == "PENDING"
    assert (await review(3, "agree", revised.version)).status == "CONFIRMED"
    with pytest.raises(ConflictError):
        await review(3, "agree", revised.version)
    async with uow_factory() as uow:
        assert await uow.ledger.net_balances(room.room_id) == {
            room.rep.member_id: 200_000,
            room.lan.member_id: -100_000,
            room.minh.member_id: -100_000,
        }
