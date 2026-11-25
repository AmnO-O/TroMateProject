"""End-to-end tests and latency benchmark for UC01 `/new` command in AiogramEngine."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

pytest.importorskip("aiogram")

from aiogram.types import Message, Update  # noqa: E402

from app.adapters.ai_extraction import AIExtractionAdapter  # noqa: E402
from app.bots.aiogram_bot import AiogramEngine  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.enums import DEFAULT_CATEGORIES, ExpenseStatus  # noqa: E402
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

    async def list_members(self, room_id: uuid.UUID) -> list[Any]:
        return self.members if self.room.id == room_id else []

    async def get_category_by_name(self, room_id: uuid.UUID, name: str) -> Any:
        return self.categories.get(name.strip().lower())


@dataclass
class _FakeExpenseRepo:
    saved: list[Any] = field(default_factory=list)

    async def add(self, expense: Any) -> Any:
        if expense.id is None:
            expense.id = uuid.uuid4()
        if expense.version is None:
            expense.version = 1
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

    async def commit(self) -> None:
        self.committed = True


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
) -> tuple[ExpenseService, _FakeExpenseRepo]:
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
        review_timeout_minutes=5,
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
    return service, expense_repo


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
    service, expense_repo = _build_fake_service(api_key="")
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"

    captured: list[tuple[str, dict[str, Any]]] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        captured.append((text, kwargs))

    update = Update.model_validate(
        _group_command_update("/new Đi chợ mua thịt cá hết 150k chia tao với Nam"),
        context={"bot": engine.bot},
    )
    with patch.object(Message, "answer", fake_answer):
        await engine.dp.feed_update(engine.bot, update)
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 1
    saved = expense_repo.saved[0]
    assert saved.status == ExpenseStatus.PENDING
    assert saved.total_amount == 150_000
    assert [s.share_amount for s in saved.splits] == [75_000, 75_000]

    assert len(captured) == 1
    html_text, kwargs = captured[0]
    assert "Đi chợ mua thịt cá" in html_text
    assert "150,000đ" in html_text
    assert "Chờ xác nhận" in html_text
    assert "Hạn xác nhận:" in html_text

    keyboard = kwargs["reply_markup"].inline_keyboard[0]
    assert [btn.text for btn in keyboard] == ["✓ Đồng ý", "✕ Từ chối", "✎ Chỉnh sửa"]
    assert keyboard[0].callback_data == f"expense:agree:{saved.id}:{saved.version}"
    assert keyboard[1].callback_data == f"expense:reject:{saved.id}:{saved.version}"
    assert keyboard[2].url == f"https://t.me/tromate_bot?startapp=expense_{saved.id}"


async def test_new_command_br02_manual_approval_for_utilities_and_rent(settings: Settings) -> None:
    service, expense_repo = _build_fake_service(api_key="")
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"
    captured: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        captured.append(text)

    with patch.object(Message, "answer", fake_answer):
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Tiền điện tháng 10 hết 650k chia đều cả phòng"),
                context={"bot": engine.bot},
            ),
        )
        await engine.dp.feed_update(
            engine.bot,
            Update.model_validate(
                _group_command_update("/new Tiền trọ tháng 10 hết 3tr"),
                context={"bot": engine.bot},
            ),
        )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 2
    utilities_exp, rent_exp = expense_repo.saved
    assert utilities_exp.review_deadline is None
    assert utilities_exp.review_window_minutes is None
    assert rent_exp.review_deadline is None
    assert "Chờ xác nhận (Duyệt thủ công — BR02)" in captured[0]
    assert "Không tự động xác nhận" in captured[0]


async def test_new_command_category_inference_and_br02_vs_br03(settings: Settings) -> None:
    service, expense_repo = _build_fake_service(api_key="")
    engine = AiogramEngine(settings, expense_service=service)
    engine.username = "tromate_bot"
    captured: list[str] = []

    async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
        captured.append(text)

    with patch.object(Message, "answer", fake_answer):
        for cmd in (
            "/new Tiền phòng tháng 12 3tr",
            "/new Tiền điện căn hộ 650k",
            "/new Mua nước uống 45k",
        ):
            await engine.dp.feed_update(
                engine.bot,
                Update.model_validate(_group_command_update(cmd), context={"bot": engine.bot}),
            )
    await engine.bot.session.close()

    assert len(expense_repo.saved) == 3
    rent_exp, utilities_exp, drink_exp = expense_repo.saved
    assert rent_exp.review_deadline is None
    assert utilities_exp.review_deadline is None
    assert drink_exp.review_deadline is not None

    assert "Danh mục: Rent" in captured[0]
    assert "Danh mục: Utilities" in captured[1]
    assert "Danh mục: Food &amp; Drinks" in captured[2]


async def test_new_command_escapes_html_in_validation_error(settings: Settings) -> None:
    service, expense_repo = _build_fake_service(api_key="")
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
    service, expense_repo = _build_fake_service(api_key="")
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


async def test_new_command_e2e_latency_fallback_vs_gemini(settings: Settings) -> None:
    sample_cmd = "/new Trà sữa 120k tao trả, Minh 70k, An 50k"

    async def _run_once(api_key: str) -> tuple[float, int]:
        service, repo = _build_fake_service(api_key=api_key)
        engine = AiogramEngine(settings, expense_service=service)
        engine.username = "tromate_bot"
        update = Update.model_validate(
            _group_command_update(sample_cmd),
            context={"bot": engine.bot},
        )

        async def fake_answer(self: Message, text: str, **kwargs: Any) -> None:
            return None

        t0 = time.perf_counter()
        with patch.object(Message, "answer", fake_answer):
            await engine.dp.feed_update(engine.bot, update)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        await engine.bot.session.close()
        return elapsed_ms, len(repo.saved)

    fb_ms, fb_saved = await _run_once("")
    assert fb_saved == 1

    gemini_key = _load_gemini_key()
    if not gemini_key:
        print(f"\n[UC01 /new E2E Timing] Fallback={fb_ms:.3f} ms (Gemini skipped: no API key)")
        return

    gm_ms, gm_saved = await _run_once(gemini_key)
    assert gm_saved == 1
    print(
        f"\n[UC01 /new E2E Timing] Fallback={fb_ms:.3f} ms vs Gemini={gm_ms:.2f} ms "
        f"(Fallback is {gm_ms / max(fb_ms, 1e-6):,.1f}x faster)"
    )
