from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    Update,
    WebAppInfo,
)

from app.bots.base import BotEngine, TaskTracker
from app.bots.common import (
    balance_text,
    group_start_text,
    help_text,
    miniapp_direct_link,
    start_text,
)
from app.core.config import Settings

logger = logging.getLogger(__name__)


class AiogramEngine(BotEngine):
    name = "aiogram"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self.router = Router()
        self._tasks = TaskTracker("app.bots.aiogram_bot")

        self.router.message.register(self._on_start, CommandStart())
        self.router.message.register(self._on_balance, Command("balance"))
        self.router.message.register(self._on_app, Command("app"))
        self.router.message.register(self._on_help, Command("help"))
        self.router.message.register(self._on_slow, Command("slow"))
        self.router.callback_query.register(
            self._on_callback,
            F.data == "balance:refresh",
        )
        self.dp.include_router(self.router)

    async def startup(self) -> None:
        me = await self.bot.get_me()
        self.username = me.username or ""

        try:
            await self.bot.set_my_commands(
                [
                    BotCommand(command="start", description="Open TroMate Mini App"),
                    BotCommand(command="balance", description="Show mock balances"),
                    BotCommand(command="app", description="Open the Mini App"),
                    BotCommand(command="help", description="Show available commands"),
                ]
            )
        except Exception:
            logger.exception("aiogram: failed to set commands")

        try:
            await self.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="TroMate",
                    web_app=WebAppInfo(url=self.settings.miniapp_url),
                )
            )
        except Exception:
            logger.exception("aiogram: failed to set the menu button")

        if self.settings.auto_set_webhook:
            try:
                await self.bot.set_webhook(
                    url=self.settings.webhook_url,
                    secret_token=self.settings.telegram_webhook_secret,
                    allowed_updates=["message", "callback_query", "my_chat_member"],
                    drop_pending_updates=True,
                    max_connections=10,
                )
                info = await self.bot.get_webhook_info()
                logger.info(
                    "aiogram webhook configured: url=%s pending=%s",
                    info.url,
                    info.pending_update_count,
                )
            except Exception:
                logger.exception("aiogram: failed to configure the webhook")

        logger.info("aiogram engine ready as @%s", self.username)

    async def shutdown(self) -> None:
        await self._tasks.shutdown()
        await self.bot.session.close()

    async def handle_update(self, payload: dict[str, Any]) -> None:
        update = Update.model_validate(payload, context={"bot": self.bot})
        self._tasks.spawn(self.dp.feed_update(self.bot, update))

    def _private_miniapp_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Open TroMate Mini App",
                        web_app=WebAppInfo(url=self.settings.miniapp_url),
                    )
                ]
            ]
        )

    def _group_miniapp_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Open TroMate Mini App",
                        url=miniapp_direct_link(self.username),
                    )
                ]
            ]
        )

    def _balance_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Refresh balances",
                        callback_data="balance:refresh",
                    )
                ]
            ]
        )

    async def _on_start(self, message: Message) -> None:
        if message.chat.type == "private":
            await message.answer(
                start_text(self.name, self.username),
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await message.answer(
                group_start_text(self.name, self.username),
                reply_markup=self._group_miniapp_keyboard(),
            )

    async def _on_balance(self, message: Message) -> None:
        await message.answer(balance_text(), reply_markup=self._balance_keyboard())

    async def _on_app(self, message: Message) -> None:
        if message.chat.type == "private":
            await message.answer(
                "Open the TroMate Mini App from the button below.",
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await message.answer(
                f"Open the TroMate Mini App: {miniapp_direct_link(self.username)}",
                reply_markup=self._group_miniapp_keyboard(),
            )

    async def _on_help(self, message: Message) -> None:
        await message.answer(help_text(self.name))

    async def _on_slow(self, message: Message) -> None:
        await asyncio.sleep(2)
        await message.answer("Slow handler finished after 2 seconds.")

    async def _on_callback(self, callback: CallbackQuery) -> None:
        await callback.answer("Balances refreshed")
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                balance_text(),
                reply_markup=self._balance_keyboard(),
            )
