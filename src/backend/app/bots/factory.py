from __future__ import annotations

from app.bots.base import BotEngine
from app.core.config import Settings


def create_engine(settings: Settings) -> BotEngine:
    """Create only the adapter selected by ``BOT_LIBRARY``."""

    if settings.bot_library == "ptb":
        from app.bots.ptb_bot import PTBEngine

        return PTBEngine(settings)
    if settings.bot_library == "aiogram":
        from app.bots.aiogram_bot import AiogramEngine

        return AiogramEngine(settings)
    if settings.bot_library == "telebot":
        from app.bots.telebot_bot import TelebotEngine

        return TelebotEngine(settings)
    raise ValueError(f"Unsupported BOT_LIBRARY: {settings.bot_library}")
