"""Cross-cutting integration tests combining UC01 v3 DB window, BR01 payer, and draft flow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

pytest.importorskip("aiogram")

from aiogram.types import CallbackQuery, Message, Update  # noqa: E402

from app.adapters.ai_extraction import AIExtractionAdapter  # noqa: E402
from app.bots.aiogram_bot import AiogramEngine  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.enums import (  # noqa: E402
    DEFAULT_CATEGORIES,
    MAX_REVIEW_WINDOW_MINUTES,
    MIN_REVIEW_WINDOW_MINUTES,
)
from app.db.models import Room, RoomMember, User  # noqa: E402
from app.services.expense_service import ExpenseService  # noqa: E402
from tests.test_uc01_new_command import (  # noqa: E402
    _build_fake_service,
    _callback_update,
    _FakeExpenseRepo,
    _FakeRoomRepo,
    _FakeRoomService,
    _FakeUnitOfWork,
    _group_command_update,
    _reply_update,
)


def _build_orm_room_service() -> tuple[ExpenseService, _FakeExpenseRepo, Room, uuid.UUID]:
    room = Room(id=uuid.uuid4(), telegram_chat_id=-100123456, name="P302", members=[])
    u1 = User(
        id=uuid.uuid4(), telegram_user_id=9001, display_name="Trần Minh", username="tranminh"
    )
    u2 = User(
        id=uuid.uuid4(), telegram_user_id=9002, display_name="Nguyễn Văn Nam", username="nam"
    )
    m1 = RoomMember(id=uuid.uuid4(), room_id=room.id, user_id=u1.id, user=u1)
    m2 = RoomMember(id=uuid.uuid4(), room_id=room.id, user_id=u2.id, user=u2)
    members = [m1, m2]
    room.members = members
    categories = {
        name.lower(): SimpleNamespace(id=uuid.uuid4(), name=name, is_archived=False)
        for name in DEFAULT_CATEGORIES
    }
    room_repo = _FakeRoomRepo(room=room, members=members, categories=categories)
    expense_repo = _FakeExpenseRepo()
    service = ExpenseService(
        extractor=AIExtractionAdapter(api_key=""),
        room_service=_FakeRoomService(sender_member=members[0]),
        uow_factory=lambda: _FakeUnitOfWork(room_repo, expense_repo),  # type: ignore[arg-type]
    )
    return service, expense_repo, room, m1.id


@pytest.mark.parametrize(
    "command_text",
    [
        "/new Lan paid 200k for dinner",
        "/new Nam trả 150k đi chợ",
    ],
)
async def test_e2e_new_command_rejects_other_payer_uc03b_af06(
    settings: Settings, command_text: str
) -> None:
    service, expense_repo, _ = _build_fake_service(review_timeout_minutes=MIN_REVIEW_WINDOW_MINUTES)
    engine = AiogramEngine(settings, expense_service=service)
    captured: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        captured.append(text)

    with patch.object(Message, "answer", fake_answer):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_group_command_update(command_text), context={"bot": engine.bot}),
        )
    await engine.bot.session.close()

    assert len(engine._drafts) == 0
    assert len(expense_repo.saved) == 0
    assert len(captured) == 1
    assert "BR01" in captured[0]


async def test_e2e_new_command_accepts_self_named_payer_and_shares(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(review_timeout_minutes=MIN_REVIEW_WINDOW_MINUTES)
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"
    edited: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        return None

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append(text)

    async def fake_cb_answer(self: CallbackQuery, *args: Any, **kwargs: Any) -> None:
        return None

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Trần Minh trả 150k đi chợ"),
                context={"bot": engine.bot},
            ),
        )
        draft_id = next(iter(engine._drafts))
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _callback_update(f"draft:share:{draft_id}"),
                context={"bot": engine.bot},
            ),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    saved = expense_repo.saved[0]
    assert saved.payer_member_id == saved.created_by_member_id
    assert saved.total_amount == 150_000
    assert len(edited) == 1
    assert "Chờ xác nhận" in edited[0]


async def test_real_room_orm_default_and_window_latching_across_updates() -> None:
    service, expense_repo, room, creator_member_id = _build_orm_room_service()
    assert room.review_timeout_minutes is None

    # 1. Real ORM default (None) -> AF06 manual approval, no deadline
    draft_none = await service.prepare_expense_draft(
        telegram_chat_id=room.telegram_chat_id,
        chat_title=room.name,
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Đi chợ 100k",
    )
    assert draft_none is not None
    assert draft_none.manual_reason == "NO_ROOM_WINDOW"
    assert draft_none.auto_confirm_enabled is False
    created_none = await service.share_expense_draft(draft_none)
    assert created_none.review_window_minutes is None
    assert created_none.review_deadline is None

    # 2. Room adopts 1-day minimum window -> deadline == shared_at + 24h
    room.review_timeout_minutes = MIN_REVIEW_WINDOW_MINUTES
    t1 = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
    draft_1d = await service.prepare_expense_draft(
        telegram_chat_id=room.telegram_chat_id,
        chat_title=room.name,
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Ăn tối 200k",
    )
    assert draft_1d is not None
    assert draft_1d.auto_confirm_enabled is True
    created_1d = await service.share_expense_draft(draft_1d, now=t1)
    assert created_1d.review_window_minutes == 1440
    assert created_1d.review_deadline == t1 + timedelta(hours=24)

    # 3. Room adopts 30-day maximum window -> earlier expense keeps 1-day deadline, new gets 30d
    room.review_timeout_minutes = MAX_REVIEW_WINDOW_MINUTES
    t2 = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
    draft_30d = await service.prepare_expense_draft(
        telegram_chat_id=room.telegram_chat_id,
        chat_title=room.name,
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Mua nước uống 60k",
    )
    assert draft_30d is not None
    created_30d = await service.share_expense_draft(draft_30d, now=t2)
    assert created_30d.review_window_minutes == 43_200
    assert created_30d.review_deadline == t2 + timedelta(days=30)

    exp_none, exp_1d, exp_30d = expense_repo.saved
    assert exp_none.review_window_minutes is None
    assert exp_1d.review_window_minutes == 1440
    assert exp_1d.review_deadline == t1 + timedelta(hours=24)
    assert exp_30d.review_window_minutes == 43_200
    assert all(e.payer_member_id == creator_member_id for e in expense_repo.saved)


async def test_e2e_draft_edit_rejects_other_payer_and_preserves_original_draft(
    settings: Settings,
) -> None:
    service, expense_repo, _ = _build_fake_service(review_timeout_minutes=MIN_REVIEW_WINDOW_MINUTES)
    engine = AiogramEngine(settings, expense_service=service)
    answers: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answers.append(text)

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        answers.append(text)

    async def fake_cb_answer(self: CallbackQuery, *args: Any, **kwargs: Any) -> None:
        return None

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Ăn trưa 120k chia tao với Nam"),
                context={"bot": engine.bot},
            ),
        )
        draft_id = next(iter(engine._drafts))

        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _callback_update(f"draft:edit:{draft_id}"),
                context={"bot": engine.bot},
            ),
        )
        prompt_text = answers[-1]
        assert prompt_text.startswith(f"UC01 {draft_id}")

        # Attempt to edit into another member's payment -> rejected by BR01, draft stays intact
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _reply_update("Nam trả 200k ăn tối", reply_to_text=prompt_text),
                context={"bot": engine.bot},
            ),
        )
        assert "BR01" in answers[-1]
        assert draft_id in engine._drafts

        # Share original draft -> still works with original 120k
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _callback_update(f"draft:share:{draft_id}"),
                context={"bot": engine.bot},
            ),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    assert expense_repo.saved[0].total_amount == 120_000
