"""End-to-end tests and latency benchmark for UC01 `/new` command in AiogramEngine."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytest.importorskip("aiogram")

from aiogram.types import (  # noqa: E402
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    CallbackQuery,
    ForceReply,
    Message,
    Update,
)

from app.adapters.ai_extraction import AIExtractionAdapter  # noqa: E402
from app.bots.aiogram_bot import AiogramEngine  # noqa: E402
from app.bots.expense_card import (  # noqa: E402
    format_review_window,
    render_confirmation_card_html,
)
from app.bots.interface import ConfirmationCardDTO, SplitLineDTO  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.enums import (  # noqa: E402
    DEFAULT_CATEGORIES,
    ApprovalDecision,
    ExpenseStatus,
    SourceType,
)
from app.services.errors import ConflictError, PermissionDeniedError  # noqa: E402
from app.services.expense_service import ExpenseService  # noqa: E402
from app.services.room_service import RoomService  # noqa: E402


@dataclass
class _FakeRoomRepo:
    room: Any
    members: list[Any]
    categories: dict[str, Any]

    async def get_room_by_chat_id(self, telegram_chat_id: int) -> Any:
        return self.room if self.room.telegram_chat_id == telegram_chat_id else None

    async def get_room(self, room_id: uuid.UUID) -> Any:
        return self.room if self.room.id == room_id else None

    async def get_category(self, category_id):
        return next(c for c in self.categories.values() if c.id == category_id)

    async def list_categories(self, room_id):
        return list(self.categories.values())

    async def list_members(self, room_id: uuid.UUID) -> list[Any]:
        return self.members if self.room.id == room_id else []

    async def get_category_by_name(self, room_id: uuid.UUID, name: str) -> Any:
        return self.categories.get(name.strip().lower())


@dataclass
class _FakeExpenseRepo:
    jobs: list[Any] = field(default_factory=list)

    def enqueue(self, expense):
        self.jobs.append(
            SimpleNamespace(
                id=uuid.uuid4(),
                kind="card",
                expense_id=expense.id,
                attempts=0,
                available_at=datetime.now(UTC),
            )
        )

    async def get(self, expense_id, *, for_update=False):
        return next(exp for exp in self.saved if exp.id == expense_id)

    async def next_delivery(self, now):
        return next((job for job in self.jobs if job.available_at <= now), None)

    async def finish_delivery(self, job):
        self.jobs.remove(job)

    saved: list[Any] = field(default_factory=list)

    async def add(self, expense: Any) -> Any:
        if expense.id is None:
            expense.id = uuid.uuid4()
        if expense.version is None:
            expense.version = 1
        expense.content_revision = expense.card_revision = 1
        self.saved.append(expense)
        return expense


class _FakeUnitOfWork:
    def __init__(self, rooms: _FakeRoomRepo, expenses: _FakeExpenseRepo) -> None:
        self.rooms = rooms
        self.expenses = expenses
        self.committed = False

    async def __aenter__(self) -> _FakeUnitOfWork:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    async def flush(self):
        pass

    async def commit(self) -> None:
        self.committed = True


async def _deliver_shared_cards(engine, edit_message):
    with patch.object(engine.bot, "edit_message_text", new_callable=AsyncMock) as edit:
        while await engine.expense_service.deliver_next(engine._deliver):
            pass
    for call in edit.await_args_list:
        await edit_message(None, *call.args, **call.kwargs)


class _FakeRoomService(RoomService):
    def __init__(self, sender_member: Any) -> None:
        self._sender_member = sender_member

    async def ensure_room_and_member_in_uow(
        self,
        uow: Any,
        *,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        display_name: str,
        username: str | None = None,
    ) -> tuple[Any, Any, bool, bool]:
        room = await uow.rooms.get_room_by_chat_id(telegram_chat_id)
        return room, self._sender_member, False, False


def _build_fake_service(
    *,
    api_key: str = "",
    review_timeout_minutes: int | None = None,
) -> tuple[ExpenseService, _FakeExpenseRepo, Any]:
    room_id = uuid.uuid4()
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    m1, m2, m3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    members = [
        SimpleNamespace(
            id=m1,
            user=SimpleNamespace(
                id=u1, telegram_user_id=9001, display_name="Trần Minh", username="tranminh"
            ),
        ),
        SimpleNamespace(
            id=m2,
            user=SimpleNamespace(
                id=u2, telegram_user_id=9002, display_name="Nguyễn Văn Nam", username="nam"
            ),
        ),
        SimpleNamespace(
            id=m3,
            user=SimpleNamespace(
                id=u3, telegram_user_id=9003, display_name="Trần Bình An", username="an"
            ),
        ),
    ]
    room = SimpleNamespace(
        id=room_id,
        telegram_chat_id=-100123456,
        review_timeout_minutes=review_timeout_minutes,
        members=members,
    )
    categories = {
        name.lower(): SimpleNamespace(id=uuid.uuid4(), name=name, is_archived=False)
        for name in DEFAULT_CATEGORIES
    }

    room_repo = _FakeRoomRepo(room=room, members=members, categories=categories)
    expense_repo = _FakeExpenseRepo()
    room_service = _FakeRoomService(sender_member=members[0])

    service = ExpenseService(
        extractor=AIExtractionAdapter(api_key=api_key, timeout_s=15.0),
        room_service=room_service,
        uow_factory=lambda: _FakeUnitOfWork(room_repo, expense_repo),  # type: ignore[arg-type]
    )
    return service, expense_repo, room


def _group_command_update(text: str, *, chat_type: str = "supergroup") -> dict[str, Any]:
    cmd_len = len(text.split()[0])
    return {
        "update_id": 101,
        "message": {
            "message_id": 55,
            "date": 1700000000,
            "chat": {"id": -100123456, "type": chat_type, "title": "Phòng 302"},
            "from": {
                "id": 9001,
                "is_bot": False,
                "first_name": "Trần",
                "last_name": "Minh",
                "username": "tranminh",
            },
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": cmd_len}],
        },
    }


def _callback_update(
    data: str,
    *,
    user_id: int = 9001,
    first_name: str = "Trần",
    last_name: str = "Minh",
    username: str = "tranminh",
    update_id: int = 102,
    message_id: int = 56,
) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb-{update_id}",
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
            },
            "chat_instance": "chat-inst-1",
            "data": data,
            "message": {
                "message_id": message_id,
                "date": 1700000001,
                "chat": {"id": -100123456, "type": "supergroup", "title": "Phòng 302"},
                "from": {"id": 123456, "is_bot": True, "first_name": "TroMate"},
                "text": "summary",
            },
        },
    }


def _reply_update(
    text: str,
    *,
    reply_to_text: str,
    user_id: int = 9001,
    reply_to_bot_id: int = 123456,
    update_id: int = 103,
) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 58,
            "date": 1700000002,
            "chat": {"id": -100123456, "type": "supergroup", "title": "Phòng 302"},
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Trần",
                "last_name": "Minh",
                "username": "tranminh",
            },
            "text": text,
            "reply_to_message": {
                "message_id": 57,
                "date": 1700000001,
                "chat": {"id": -100123456, "type": "supergroup", "title": "Phòng 302"},
                "from": {"id": reply_to_bot_id, "is_bot": True, "first_name": "TroMate"},
                "text": reply_to_text,
            },
        },
    }


def _load_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


async def test_new_command_creates_pending_expense_and_inline_card(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"

    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[tuple[str, dict[str, Any]]] = []
    cb_answers: list[tuple[str | None, dict[str, Any]]] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append((text, kwargs))

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        cb_answers.append((text, kwargs))

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Đi chợ mua thịt cá hết 150k chia tao với Nam"),
                context={"bot": engine.bot},
            ),
        )
        assert len(expense_repo.saved) == 0
        assert len(answered) == 1
        summary_html, summary_kwargs = answered[0]
        assert "Đi chợ mua thịt cá" in summary_html
        assert "150,000đ" in summary_html
        assert "Bật" in summary_html
        assert "1 ngày" in summary_html

        summary_rows = summary_kwargs["reply_markup"].inline_keyboard
        assert [btn.text for btn in summary_rows[0]] == ["✓ Chia sẻ", "✎ Chỉnh sửa", "✕ Hủy"]
        assert [btn.text for btn in summary_rows[1]] == ["🔕 Tắt tự động xác nhận"]
        share_cb = summary_rows[0][0].callback_data
        assert share_cb is not None and share_cb.startswith("draft:share:")

        before_share = datetime.now(UTC)
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
        )
        after_share = datetime.now(UTC)
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    saved = expense_repo.saved[0]
    assert saved.status == ExpenseStatus.PENDING
    assert saved.total_amount == 150_000
    assert [s.share_amount for s in saved.splits] == [75_000, 75_000]
    assert saved.review_window_minutes == 1440
    assert saved.review_deadline is not None
    assert (
        before_share + timedelta(minutes=1440)
        <= saved.review_deadline
        <= after_share + timedelta(minutes=1440)
    )
    assert len(saved.approvals) == 1
    assert saved.approvals[0].member_id == saved.created_by_member_id
    assert saved.approvals[0].decision == ApprovalDecision.AGREE
    assert saved.approvals[0].expense_version == 1

    await _deliver_shared_cards(engine, fake_edit_text)
    assert len(edited) == 1
    html_text, kwargs = edited[0]
    assert "Đi chợ mua thịt cá" in html_text
    assert "150,000đ" in html_text
    assert "Đồng ý: 1/2" in html_text
    keyboard = kwargs["reply_markup"].inline_keyboard[0]
    assert len(keyboard) == 1
    assert keyboard[0].url.endswith(f"_{saved.version}_review")
    assert keyboard[0].callback_data is None
    assert cb_answers[-1] == ("Đã chia sẻ khoản chi.", {})


async def test_new_command_br02_manual_approval_for_utilities_and_rent(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"
    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append(text)

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        return None

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        for cmd in (
            "/new Tiền điện tháng 10 hết 650k chia đều cả phòng",
            "/new Tiền trọ tháng 10 hết 3tr",
        ):
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(_group_command_update(cmd), context={"bot": engine.bot}),
            )
            summary_html, summary_kwargs = answered[-1]
            assert "Duyệt thủ công (BR02)" in summary_html
            assert len(summary_kwargs["reply_markup"].inline_keyboard) == 1
            share_cb = summary_kwargs["reply_markup"].inline_keyboard[0][0].callback_data
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
            )
    await engine.bot.session.close()

    await _deliver_shared_cards(engine, fake_edit_text)
    assert len(expense_repo.saved) == 2
    utilities_exp, rent_exp = expense_repo.saved
    assert utilities_exp.review_deadline is None
    assert utilities_exp.review_window_minutes is None
    assert rent_exp.review_deadline is None
    assert rent_exp.review_window_minutes is None
    assert "Chờ xác nhận (Duyệt thủ công — BR02)" in edited[0]
    assert "Không tự động xác nhận" in edited[0]


async def test_new_command_category_inference_and_br02_vs_br03(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"
    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append(text)

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        return None

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        for cmd in (
            "/new Tiền phòng tháng 12 3tr",
            "/new Tiền điện căn hộ 650k",
            "/new Mua nước uống 45k",
        ):
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(_group_command_update(cmd), context={"bot": engine.bot}),
            )
            share_cb = answered[-1][1]["reply_markup"].inline_keyboard[0][0].callback_data
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
            )
    await engine.bot.session.close()

    await _deliver_shared_cards(engine, fake_edit_text)
    assert len(expense_repo.saved) == 3
    rent_exp, utilities_exp, drink_exp = expense_repo.saved
    assert rent_exp.review_deadline is None
    assert utilities_exp.review_deadline is None
    assert drink_exp.review_deadline is not None
    assert drink_exp.review_window_minutes == 1440

    assert "Danh mục: Rent" in edited[0]
    assert "Danh mục: Utilities" in edited[1]
    assert "Danh mục: Food &amp; Drinks" in edited[2]


async def test_new_command_escapes_html_in_validation_error(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    captured: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        captured.append(text)

    with patch.object(Message, "answer", fake_answer):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Ăn trưa 100k chia Nam, <b>"),
                context={"bot": engine.bot},
            ),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 0
    assert len(captured) == 1
    assert "&lt;b&gt;" in captured[0]
    assert "<b>" not in captured[0]
    assert "Không tìm thấy thành viên" in captured[0]
    assert "cần nhắn /start hoặc /new trong nhóm trước" in captured[0]


async def test_ensure_room_and_member_initializes_relationships_for_async_session() -> None:
    from sqlalchemy import inspect as sa_inspect

    class _ColdRoomRepo:
        def __init__(self) -> None:
            self.created_room: Any = None
            self.created_member: Any = None

        async def get_room_by_chat_id(self, telegram_chat_id: int) -> Any:
            return None

        async def get_user_by_telegram_id(self, telegram_user_id: int) -> Any:
            return None

        async def add_user(self, user: Any) -> Any:
            user.id = uuid.uuid4()
            return user

        async def add_room(self, room: Any) -> Any:
            room.id = uuid.uuid4()
            self.created_room = room
            return room

        async def add_categories(self, categories: Any) -> list[Any]:
            return list(categories)

        async def get_member_by_user(self, room_id: uuid.UUID, user_id: uuid.UUID) -> Any:
            return None

        async def add_member(self, member: Any) -> Any:
            member.id = uuid.uuid4()
            self.created_member = member
            return member

    cold_repo = _ColdRoomRepo()
    uow = SimpleNamespace(rooms=cold_repo)
    room, member, room_created, member_created = await RoomService().ensure_room_and_member_in_uow(
        uow,  # type: ignore[arg-type]
        telegram_chat_id=-777111222,
        chat_title="New Room",
        telegram_user_id=777111222,
        display_name="First User",
        username="firstuser",
    )

    assert room_created is True
    assert member_created is True
    assert "members" not in sa_inspect(cold_repo.created_room).unloaded
    assert "user" not in sa_inspect(cold_repo.created_member).unloaded
    assert room.members == [member]
    assert member.user.display_name == "First User"


async def test_new_command_guards_empty_args_and_private_chat(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="")
    engine = AiogramEngine(settings, expense_service=service)
    captured: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        captured.append(text)

    with patch.object(Message, "answer", fake_answer):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_group_command_update("/new"), context={"bot": engine.bot}),
        )
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Ăn trưa 50k", chat_type="private"),
                context={"bot": engine.bot},
            ),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 0
    assert len(captured) == 2
    assert "Vui lòng nhập nội dung" in captured[0]
    assert "chỉ dùng trong nhóm" in captured[1]


def test_confirmation_card_displays_vietnamese_vote_labels() -> None:
    card = ConfirmationCardDTO(
        expense_id=uuid.uuid4(),
        version=2,
        description="Bữa trưa",
        total_amount=100_000,
        payer_name="Hao",
        category_name="Other",
        status="DISPUTED",
        payer_decision="AGREE",
        voter_count=3,
        agreed_count=1,
        splits=(SplitLineDTO("Lan", 50_000, "REJECT"), SplitLineDTO("Minh", 50_000, "PENDING")),
    )
    html = render_confirmation_card_html(card)
    assert "Người trả: Hao · ✓ Đồng ý" in html
    assert html.count("Hao") == 1
    assert "Lan: 50,000đ · ✕ Từ chối" in html
    assert "Minh: 50,000đ · ⏳ Chờ duyệt" in html


def test_confirmation_card_formats_deadline_in_gmt_plus_7() -> None:
    card = ConfirmationCardDTO(
        expense_id=uuid.uuid4(),
        version=1,
        description="Ăn tối",
        total_amount=100_000,
        payer_name="Trần Minh",
        category_name="Food & Drinks",
        status="PENDING",
        splits=(SplitLineDTO(display_name="Trần Minh", share_amount=100_000),),
        review_deadline=datetime(2026, 11, 25, 10, 30, tzinfo=UTC),
    )
    html = render_confirmation_card_html(card)
    assert "⏳ Hạn xác nhận: 17:30 25/11 (GMT+7)" in html


async def test_aiogram_engine_uses_gemini_model_shared_client_and_command_scopes() -> None:
    custom_settings = Settings(
        app_env="test",
        public_base_url="http://testserver",
        auto_set_webhook=False,
        bot_library="aiogram",
        telegram_bot_token="123456:TEST_TOKEN",
        telegram_webhook_secret="test-secret-0123456789abcdef",
        gemini_model="gemini-2.5-flash",
    )
    engine = AiogramEngine(custom_settings)
    extractor = engine._expense_service._extractor
    assert isinstance(extractor, AIExtractionAdapter)
    assert extractor.model == "gemini-2.5-flash"
    assert extractor._client is engine._http_client
    assert engine._http_client.is_closed is False

    set_commands_mock = AsyncMock()
    with (
        patch.object(
            engine.bot,
            "get_me",
            new=AsyncMock(return_value=SimpleNamespace(username="tromate_bot")),
        ),
        patch.object(engine.bot, "set_my_commands", new=set_commands_mock),
        patch.object(engine.bot, "set_chat_menu_button", new=AsyncMock()),
    ):
        await engine.startup()

    assert set_commands_mock.await_count == 2
    private_call, group_call = set_commands_mock.await_args_list
    assert isinstance(private_call.kwargs["scope"], BotCommandScopeAllPrivateChats)
    assert [cmd.command for cmd in private_call.args[0]] == ["start", "help", "app"]
    assert isinstance(group_call.kwargs["scope"], BotCommandScopeAllGroupChats)
    assert [cmd.command for cmd in group_call.args[0]] == [
        "start",
        "help",
        "app",
        "balance",
        "new",
    ]

    await engine.shutdown()
    assert engine._http_client.is_closed is True


async def test_new_command_e2e_latency_fallback_vs_gemini(settings: Settings) -> None:
    sample_cmd = "/new Trà sữa 120k tao trả, Minh 70k, An 50k"

    async def _run_once(api_key: str) -> tuple[float, int]:
        service, repo, _ = _build_fake_service(api_key=api_key, review_timeout_minutes=1440)
        engine = AiogramEngine(settings, expense_service=service)
        engine.username = "tromate_bot"
        update = Update.model_validate(
            _group_command_update(sample_cmd),
            context={"bot": engine.bot},
        )
        draft_markups: list[Any] = []

        async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
            draft_markups.append(kwargs.get("reply_markup"))

        async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
            return None

        async def fake_cb_answer(
            self: CallbackQuery, text: str | None = None, **kwargs: Any
        ) -> None:
            return None

        t0 = time.perf_counter()
        with (
            patch.object(Message, "answer", fake_answer),
            patch.object(Message, "edit_text", fake_edit_text),
            patch.object(CallbackQuery, "answer", fake_cb_answer),
        ):
            await engine.dp.feed_update(engine.bot, update)
            share_cb = draft_markups[0].inline_keyboard[0][0].callback_data
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        await engine.bot.session.close()
        return elapsed_ms, len(repo.saved)

    fb_ms, fb_saved = await _run_once("")
    assert fb_saved == 1

    gemini_key = _load_gemini_key() if os.environ.get("RUN_LIVE_GEMINI") == "1" else ""
    if not gemini_key:
        print(f"\n[UC01 /new E2E Timing] Fallback={fb_ms:.3f} ms (Gemini skipped)")
        return

    gm_ms, gm_saved = await _run_once(gemini_key)
    assert gm_saved == 1
    print(
        f"\n[UC01 /new E2E Timing] Fallback={fb_ms:.3f} ms vs Gemini={gm_ms:.2f} ms "
        f"(Fallback is {gm_ms / max(fb_ms, 1e-6):,.1f}x faster)"
    )


@pytest.mark.parametrize("scenario", ["agree", "share", "stale", "forbidden", "malformed"])
async def test_on_review_callback(scenario):
    expense_id = uuid.uuid4()
    review = SimpleNamespace(expense_id=expense_id, version=2)
    engine = Mock(spec=AiogramEngine)
    engine._expense_url.return_value = "https://t.me/test?startapp=expense_test"
    engine._expense_service = AsyncMock()
    service_review = engine._expense_service.review
    service_review.return_value = review
    message = Mock(spec=Message)
    message.answer = AsyncMock()
    message.chat = SimpleNamespace(id=-100)
    message.message_id = 42
    action = scenario if scenario in {"agree", "share"} else "agree"
    callback = SimpleNamespace(
        message=message,
        from_user=SimpleNamespace(id=7),
        answer=AsyncMock(),
        data=f"expense:{action}:{expense_id}:1",
    )
    if scenario == "stale":
        service_review.side_effect = [ConflictError("Stale"), review]
    elif scenario == "forbidden":
        service_review.side_effect = PermissionDeniedError("Forbidden")
    elif scenario == "malformed":
        callback.data = "expense:agree"

    await AiogramEngine._on_review(engine, callback)

    if scenario == "malformed":
        service_review.assert_not_awaited()
        callback.answer.assert_awaited_once_with("Nút này đã cũ.", show_alert=True)
    else:
        args = dict(expense_id=expense_id, version=1, telegram_chat_id=-100, telegram_user_id=7)
        service_review.assert_any_await(action=action, **args)
        if scenario == "stale":
            callback.answer.assert_awaited_once_with("Stale", show_alert=True)
            message.answer.assert_awaited_once()
        elif scenario == "forbidden":
            callback.answer.assert_awaited_once_with("Forbidden", show_alert=True)
        else:
            callback.answer.assert_awaited_once_with()
    if scenario in {"agree", "share"}:
        engine.wake_delivery.assert_called_once_with()
    if scenario == "stale":
        assert engine.publish_expense.await_args.args == (expense_id, -100, 7)
        assert engine.publish_expense.await_args.kwargs["fallback"] == 42
    else:
        engine.publish_expense.assert_not_awaited()


async def test_uc01_af06_no_room_window_shows_manual_and_saves_without_deadline(
    settings: Settings,
) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=None)
    engine = AiogramEngine(settings, expense_service=service)
    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append(text)

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        return None

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Ăn trưa 90k chia đều"),
                context={"bot": engine.bot},
            ),
        )
        summary_html, summary_kwargs = answered[0]
        assert "Phòng chưa có window auto-confirm" in summary_html
        assert len(summary_kwargs["reply_markup"].inline_keyboard) == 1
        assert len(expense_repo.saved) == 0

        share_cb = summary_kwargs["reply_markup"].inline_keyboard[0][0].callback_data
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    saved = expense_repo.saved[0]
    assert saved.review_deadline is None
    assert saved.review_window_minutes is None


async def test_uc01_af05_creator_turns_off_auto_confirm_before_share(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[tuple[str, dict[str, Any]]] = []
    cb_answers: list[tuple[str | None, dict[str, Any]]] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append((text, kwargs))

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        cb_answers.append((text, kwargs))

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Mua rau 60k chia đều"),
                context={"bot": engine.bot},
            ),
        )
        rows = answered[0][1]["reply_markup"].inline_keyboard
        off_cb = rows[1][0].callback_data
        share_cb = rows[0][0].callback_data

        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(off_cb), context={"bot": engine.bot}),
        )
        updated_html, updated_kwargs = edited[0]
        assert "Đã tắt (Duyệt thủ công)" in updated_html
        assert len(updated_kwargs["reply_markup"].inline_keyboard) == 1
        assert cb_answers[0] == ("Đã tắt tự động xác nhận.", {})

        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    saved = expense_repo.saved[0]
    assert saved.review_deadline is None
    assert saved.review_window_minutes is None


async def test_br03_room_window_changes_after_share_do_not_mutate_shared_expense() -> None:
    service, expense_repo, room = _build_fake_service(api_key="", review_timeout_minutes=1440)
    t1 = datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
    draft1 = await service.prepare_expense_draft(
        telegram_chat_id=-100123456,
        chat_title="Phòng 302",
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Mua gạo 100k chia đều",
    )
    assert draft1 is not None
    await service.share_expense_draft(draft1, now=t1)

    room.review_timeout_minutes = 10080  # 7 days
    t2 = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
    draft2 = await service.prepare_expense_draft(
        telegram_chat_id=-100123456,
        chat_title="Phòng 302",
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Mua nước mắm 45k chia đều",
    )
    assert draft2 is not None
    await service.share_expense_draft(draft2, now=t2)

    assert len(expense_repo.saved) == 2
    exp1, exp2 = expense_repo.saved
    assert exp1.review_window_minutes == 1440
    assert exp1.review_deadline == t1 + timedelta(minutes=1440)
    assert exp2.review_window_minutes == 10080
    assert exp2.review_deadline == t2 + timedelta(minutes=10080)


async def test_shared_card_delivery_retries_without_creating_another_expense(settings):
    service, repo, room = _build_fake_service()
    engine = AiogramEngine(settings, expense_service=service)
    draft = await service.prepare_expense_draft(
        telegram_chat_id=room.telegram_chat_id,
        chat_title="P302",
        telegram_user_id=9001,
        sender_display_name="Minh",
        sender_username=None,
        text="Mua rau 45k chia đều",
    )
    await service.share_expense_draft(draft, card_message_id=123)
    try:
        with patch.object(
            engine.bot, "edit_message_text", side_effect=[TimeoutError(), None]
        ) as edit:
            assert await service.deliver_next(engine._deliver)
            (job,) = repo.jobs
            assert job.attempts == 1 and job.available_at > datetime.now(UTC)
            assert not await service.deliver_next(engine._deliver)
            job.available_at = datetime.now(UTC)
            assert await service.deliver_next(engine._deliver)
            assert edit.await_count == 2 and edit.await_args_list[0] == edit.await_args_list[1]
            assert not repo.jobs and len(repo.saved) == 1
    finally:
        await engine.bot.session.close()


async def test_br03_room_window_latched_at_share_time() -> None:
    service, expense_repo, room = _build_fake_service(api_key="", review_timeout_minutes=1440)
    draft = await service.prepare_expense_draft(
        telegram_chat_id=-100123456,
        chat_title="Phòng 302",
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Mua trái cây 120k chia đều",
    )
    assert draft is not None
    assert draft.room_window_minutes == 1440

    room.review_timeout_minutes = 2880
    share_time = datetime(2026, 11, 26, 11, 0, tzinfo=UTC)
    created = await service.share_expense_draft(draft, now=share_time)

    assert created.review_window_minutes == 2880
    assert created.review_deadline == share_time + timedelta(minutes=2880)
    assert expense_repo.saved[0].review_window_minutes == 2880


async def test_uc01_af04_creator_cancels_draft_and_subsequent_share_alerts(
    settings: Settings,
) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[tuple[str, dict[str, Any]]] = []
    cb_answers: list[tuple[str | None, dict[str, Any]]] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append((text, kwargs))

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        cb_answers.append((text, kwargs))

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Ăn tối 180k chia đều"),
                context={"bot": engine.bot},
            ),
        )
        row = answered[0][1]["reply_markup"].inline_keyboard[0]
        share_cb = row[0].callback_data
        cancel_cb = row[2].callback_data

        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(cancel_cb), context={"bot": engine.bot}),
        )
        assert "Đã hủy ghi nhận khoản chi" in edited[0][0]
        assert edited[0][1]["reply_markup"] is None
        assert cb_answers[0] == ("Đã hủy.", {})

        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
        )
        assert cb_answers[1][1]["show_alert"] is True
        assert "hết hạn" in (cb_answers[1][0] or "")
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 0


async def test_uc01_af03_creator_edits_draft_via_force_reply(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    answered: list[tuple[str, dict[str, Any]]] = []
    edited: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_edit_text(self: Message, text: str, **kwargs: Any) -> None:
        edited.append(text)

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        return None

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(Message, "edit_text", fake_edit_text),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Đi chợ 150k chia tao với Nam"),
                context={"bot": engine.bot},
            ),
        )
        edit_cb = answered[0][1]["reply_markup"].inline_keyboard[0][1].callback_data
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(edit_cb), context={"bot": engine.bot}),
        )
        prompt_text, prompt_kwargs = answered[1]
        assert prompt_text.startswith("UC01 ")
        assert isinstance(prompt_kwargs["reply_markup"], ForceReply)

        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _reply_update(
                    "Đi chợ 200k chia tao với Nam",
                    reply_to_text=prompt_text,
                ),
                context={"bot": engine.bot},
            ),
        )
        updated_html, updated_kwargs = answered[2]
        assert "200,000đ" in updated_html
        assert len(expense_repo.saved) == 0

        share_cb = updated_kwargs["reply_markup"].inline_keyboard[0][0].callback_data
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(_callback_update(share_cb), context={"bot": engine.bot}),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    await _deliver_shared_cards(engine, fake_edit_text)
    assert expense_repo.saved[0].total_amount == 200_000
    assert "200,000đ" in edited[0]


async def test_uc01_non_creator_cannot_act_on_draft(settings: Settings) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    engine = AiogramEngine(settings, expense_service=service)
    answered: list[tuple[str, dict[str, Any]]] = []
    cb_answers: list[tuple[str | None, dict[str, Any]]] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        answered.append((text, kwargs))

    async def fake_cb_answer(self: CallbackQuery, text: str | None = None, **kwargs: Any) -> None:
        cb_answers.append((text, kwargs))

    with (
        patch.object(Message, "answer", fake_answer),
        patch.object(CallbackQuery, "answer", fake_cb_answer),
    ):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Cà phê 90k chia đều"),
                context={"bot": engine.bot},
            ),
        )
        rows = answered[0][1]["reply_markup"].inline_keyboard
        callbacks = [
            rows[0][0].callback_data,
            rows[1][0].callback_data,
            rows[0][1].callback_data,
            rows[0][2].callback_data,
        ]
        for idx, cb in enumerate(callbacks, start=200):
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(
                    _callback_update(
                        cb,
                        user_id=9002,
                        first_name="Nguyễn",
                        last_name="Nam",
                        username="nam",
                        update_id=idx,
                    ),
                    context={"bot": engine.bot},
                ),
            )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 0
    assert len(engine._drafts) == 1
    assert len(cb_answers) == 4
    assert all(kwargs.get("show_alert") is True for _, kwargs in cb_answers)
    assert all("Chỉ người tạo khoản chi" in (msg or "") for msg, _ in cb_answers)


@pytest.mark.parametrize(
    ("text", "source_type", "expected_reason"),
    [
        ("Tiền phòng tháng 11 3tr", SourceType.TEXT, "MANUAL_CATEGORY"),
        ("Tiền điện tháng 11 650k", SourceType.TEXT, "MANUAL_CATEGORY"),
        ("Đi chợ 100k chia đều", SourceType.PHOTO, "NON_TEXT"),
        ("Chỉ số công tơ 250k chia đều", SourceType.METER, "NON_TEXT"),
    ],
)
async def test_br02_manual_only_for_rent_utilities_photo_and_meter(
    text: str,
    source_type: SourceType,
    expected_reason: str,
) -> None:
    service, expense_repo, _ = _build_fake_service(api_key="", review_timeout_minutes=1440)
    draft = await service.prepare_expense_draft(
        telegram_chat_id=-100123456,
        chat_title="Phòng 302",
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text=text,
        source_type=source_type,
    )
    assert draft is not None
    assert draft.auto_confirm_eligible is False
    assert draft.auto_confirm_enabled is False
    assert draft.manual_reason == expected_reason

    created = await service.share_expense_draft(
        draft, now=datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
    )
    assert created.review_deadline is None
    assert created.review_window_minutes is None
    assert expense_repo.saved[0].review_deadline is None
    assert expense_repo.saved[0].review_window_minutes is None


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (1440, "1 ngày"),
        (2160, "1 ngày 12 giờ"),
        (43200, "30 ngày"),
        (1470, "1 ngày 30 phút"),
        (90, "1 giờ 30 phút"),
        (45, "45 phút"),
    ],
)
def test_format_review_window_cases(minutes: int, expected: str) -> None:
    assert format_review_window(minutes) == expected
