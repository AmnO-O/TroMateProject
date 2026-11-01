from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.core.config import Settings


def update_payload(text: str, chat_type: str = "private") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "date": 1700000000,
            "chat": {"id": 123, "type": chat_type, "title": "Test"},
            "from": {"id": 123, "is_bot": False, "first_name": "Nam", "username": "nam"},
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": len(text)}],
        },
    }


@pytest.mark.asyncio
async def test_ptb_dispatches_start(settings: Settings) -> None:
    telegram = pytest.importorskip("telegram")
    from app.bots.ptb_bot import PTBEngine

    engine = PTBEngine(settings)
    engine.username = "tromate_bot"
    engine.application._initialized = True
    engine.application.bot._bot_user = telegram.User(
        id=999,
        first_name="Bot",
        is_bot=True,
        username="tromate_bot",
    )
    captured = []

    async def fake_reply_text(self, text, **kwargs):
        captured.append((text, kwargs))
        return None

    update = telegram.Update.de_json(
        update_payload("/start"),
        engine.application.bot,
    )
    with patch.object(telegram.Message, "reply_text", fake_reply_text):
        await engine.application.process_update(update)

    assert len(captured) == 1
    assert "running via ptb" in captured[0][0]
    assert type(captured[0][1]["reply_markup"]).__name__ == "InlineKeyboardMarkup"


@pytest.mark.asyncio
async def test_aiogram_dispatches_start(settings: Settings) -> None:
    pytest.importorskip("aiogram")
    from aiogram.types import Message, Update

    from app.bots.aiogram_bot import AiogramEngine

    engine = AiogramEngine(settings)
    engine.username = "tromate_bot"
    captured = []

    async def fake_answer(self, text, **kwargs):
        captured.append((text, kwargs))
        return None

    update = Update.model_validate(
        update_payload("/start"),
        context={"bot": engine.bot},
    )
    with patch.object(Message, "answer", fake_answer):
        await engine.dp.feed_update(engine.bot, update)
    await engine.bot.session.close()

    assert len(captured) == 1
    assert "running via aiogram" in captured[0][0]
    assert type(captured[0][1]["reply_markup"]).__name__ == "InlineKeyboardMarkup"


@pytest.mark.asyncio
async def test_telebot_dispatches_start(settings: Settings) -> None:
    telebot = pytest.importorskip("telebot")
    from telebot.async_telebot import AsyncTeleBot

    from app.bots.telebot_bot import TelebotEngine

    engine = TelebotEngine(settings)
    engine.username = "tromate_bot"
    captured = []

    async def fake_reply_to(self, message, text, **kwargs):
        captured.append((text, kwargs))
        return None

    update = telebot.types.Update.de_json(json.dumps(update_payload("/start")))
    with patch.object(AsyncTeleBot, "reply_to", fake_reply_to):
        await engine.bot.process_new_updates([update])

    assert len(captured) == 1
    assert "running via telebot" in captured[0][0]
    assert type(captured[0][1]["reply_markup"]).__name__ == "InlineKeyboardMarkup"


@pytest.mark.asyncio
async def test_ptb_dispatches_group_start_link(settings: Settings) -> None:
    telegram = pytest.importorskip("telegram")
    from app.bots.ptb_bot import PTBEngine

    engine = PTBEngine(settings)
    engine.username = "tromate_bot"
    engine.application._initialized = True
    engine.application.bot._bot_user = telegram.User(
        id=999,
        first_name="Bot",
        is_bot=True,
        username="tromate_bot",
    )
    captured = []

    async def fake_reply_text(self, text, **kwargs):
        captured.append((text, kwargs))
        return None

    update = telegram.Update.de_json(
        update_payload("/start", chat_type="supergroup"),
        engine.application.bot,
    )
    with patch.object(telegram.Message, "reply_text", fake_reply_text):
        await engine.application.process_update(update)

    assert len(captured) == 1
    assert "https://t.me/tromate_bot?startapp=group" in captured[0][0]
    button = captured[0][1]["reply_markup"].inline_keyboard[0][0]
    assert button.url == "https://t.me/tromate_bot?startapp=group"
