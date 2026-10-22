from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from telebot import types
from telebot.async_telebot import AsyncTeleBot

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


class TelebotEngine(BotEngine):
    name = "telebot"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bot = AsyncTeleBot(settings.telegram_bot_token)
        self._tasks = TaskTracker("app.bots.telebot_bot")
        self._register_handlers()

    def _command_for_me(self, message: types.Message) -> bool:
        text = message.text or ""
        if not text.startswith("/"):
            return False
        command = text.split(maxsplit=1)[0][1:]
        if "@" not in command:
            return True
        mention = command.split("@", 1)[1]
        return not self.username or mention.lower() == self.username.lower()

    def _register_handlers(self) -> None:
        @self.bot.message_handler(commands=["start"], func=self._command_for_me)
        async def on_start(message: types.Message) -> None:
            await self._on_start(message)

        @self.bot.message_handler(commands=["balance"], func=self._command_for_me)
        async def on_balance(message: types.Message) -> None:
            await self._on_balance(message)

        @self.bot.message_handler(commands=["app"], func=self._command_for_me)
        async def on_app(message: types.Message) -> None:
            await self._on_app(message)

        @self.bot.message_handler(commands=["help"], func=self._command_for_me)
        async def on_help(message: types.Message) -> None:
            await self._on_help(message)

        @self.bot.message_handler(commands=["slow"], func=self._command_for_me)
        async def on_slow(message: types.Message) -> None:
            await self._on_slow(message)

        @self.bot.callback_query_handler(func=lambda call: call.data == "balance:refresh")
        async def on_refresh(call: types.CallbackQuery) -> None:
            await self._on_callback(call)

    async def startup(self) -> None:
        me = await self.bot.get_me()
        self.username = me.username or ""

        try:
            await self.bot.set_my_commands(
                [
                    types.BotCommand("start", "Open TroMate Mini App"),
                    types.BotCommand("balance", "Show mock balances"),
                    types.BotCommand("app", "Open the Mini App"),
                    types.BotCommand("help", "Show available commands"),
                ]
            )
        except Exception:
            logger.exception("telebot: failed to set commands")

        try:
            await self.bot.set_chat_menu_button(
                menu_button=types.MenuButtonWebApp(
                    text="TroMate",
                    web_app=types.WebAppInfo(url=self.settings.miniapp_url),
                )
            )
        except Exception:
            logger.exception("telebot: failed to set the menu button")

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
                    "telebot webhook configured: url=%s pending=%s",
                    info.url,
                    info.pending_update_count,
                )
            except Exception:
                logger.exception("telebot: failed to configure the webhook")

        logger.info("telebot engine ready as @%s", self.username)

    async def shutdown(self) -> None:
        await self._tasks.shutdown()
        try:
            await self.bot.close_session()
        except Exception:
            logger.debug("telebot: session was not open during shutdown", exc_info=True)

    async def handle_update(self, payload: dict[str, Any]) -> None:
        update = types.Update.de_json(json.dumps(payload))
        if update is None:
            logger.warning("telebot: could not decode update payload")
            return
        self._tasks.spawn(self.bot.process_new_updates([update]))

    def _private_miniapp_keyboard(self) -> types.InlineKeyboardMarkup:
        return types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        "Open TroMate Mini App",
                        web_app=types.WebAppInfo(url=self.settings.miniapp_url),
                    )
                ]
            ]
        )

    def _group_miniapp_keyboard(self) -> types.InlineKeyboardMarkup:
        return types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        "Open TroMate Mini App",
                        url=miniapp_direct_link(self.username),
                    )
                ]
            ]
        )

    def _balance_keyboard(self) -> types.InlineKeyboardMarkup:
        return types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        "Refresh balances",
                        callback_data="balance:refresh",
                    )
                ]
            ]
        )

    async def _on_start(self, message: types.Message) -> None:
        if message.chat.type == "private":
            await self.bot.reply_to(
                message,
                start_text(self.name, self.username),
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await self.bot.reply_to(
                message,
                group_start_text(self.name, self.username),
                reply_markup=self._group_miniapp_keyboard(),
            )

    async def _on_balance(self, message: types.Message) -> None:
        await self.bot.reply_to(
            message,
            balance_text(),
            reply_markup=self._balance_keyboard(),
        )

    async def _on_app(self, message: types.Message) -> None:
        if message.chat.type == "private":
            await self.bot.reply_to(
                message,
                "Open the TroMate Mini App from the button below.",
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await self.bot.reply_to(
                message,
                f"Open the TroMate Mini App: {miniapp_direct_link(self.username)}",
                reply_markup=self._group_miniapp_keyboard(),
            )

    async def _on_help(self, message: types.Message) -> None:
        await self.bot.reply_to(message, help_text(self.name))

    async def _on_slow(self, message: types.Message) -> None:
        await asyncio.sleep(2)
        await self.bot.reply_to(message, "Slow handler finished after 2 seconds.")

    async def _on_callback(self, call: types.CallbackQuery) -> None:
        await self.bot.answer_callback_query(call.id, text="Balances refreshed")
        if call.message is not None:
            await self.bot.edit_message_text(
                balance_text(),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self._balance_keyboard(),
            )
