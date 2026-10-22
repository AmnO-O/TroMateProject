from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.config import Settings

pytest.importorskip("telebot")

from app.bots.telebot_bot import TelebotEngine  # noqa: E402


@pytest.mark.asyncio
async def test_telebot_handle_update_decodes_json(settings: Settings) -> None:
    engine = TelebotEngine(settings)
    captured = []

    async def fake_process(updates):
        captured.extend(updates)

    engine.bot.process_new_updates = fake_process
    await engine.handle_update(
        {
            "update_id": 11,
            "message": {
                "message_id": 22,
                "date": 0,
                "chat": {"id": 33, "type": "private"},
                "text": "/start",
            },
        }
    )
    await engine._tasks.shutdown()
    assert len(captured) == 1
    assert captured[0].update_id == 11
    assert captured[0].message.text == "/start"


def test_telebot_rejects_commands_for_other_bots(settings: Settings) -> None:
    engine = TelebotEngine(settings)
    engine.username = "tromate_bot"

    assert engine._command_for_me(SimpleNamespace(text="/balance")) is True
    assert engine._command_for_me(SimpleNamespace(text="/balance@tromate_bot")) is True
    assert engine._command_for_me(SimpleNamespace(text="/balance@other_bot")) is False
    assert engine._command_for_me(SimpleNamespace(text="hello")) is False
