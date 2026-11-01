from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from app.bots.base import BotEngine
from app.bots.common import (
    balance_text,
    group_start_text,
    help_text,
    miniapp_direct_link,
    start_text,
)
from app.core.config import Settings

logger = logging.getLogger(__name__)


class PTBEngine(BotEngine):
    name = "ptb"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .updater(None)
            .build()
        )
        self.application.add_handler(CommandHandler("start", self._on_start))
        self.application.add_handler(CommandHandler("balance", self._on_balance))
        self.application.add_handler(CommandHandler("app", self._on_app))
        self.application.add_handler(CommandHandler("help", self._on_help))
        self.application.add_handler(CommandHandler("slow", self._on_slow))
        self.application.add_handler(
            CallbackQueryHandler(self._on_callback, pattern=r"^balance:refresh$")
        )
        self.application.add_error_handler(self._on_error)

    async def startup(self) -> None:
        await self.application.initialize()
        await self.application.start()

        self.username = self.application.bot.username or ""

        try:
            await self.application.bot.set_my_commands(
                [
                    BotCommand("start", "Open TroMate and show the Mini App button"),
                    BotCommand("balance", "Show mock balances"),
                    BotCommand("app", "Open the TroMate Mini App"),
                    BotCommand("help", "Show available commands"),
                ]
            )
        except Exception:
            logger.exception("PTB: failed to set commands")

        try:
            await self.application.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="TroMate",
                    web_app=WebAppInfo(url=self.settings.miniapp_url),
                )
            )
        except Exception:
            logger.exception("PTB: failed to set the menu button")

        if self.settings.auto_set_webhook:
            try:
                await self.application.bot.set_webhook(
                    url=self.settings.webhook_url,
                    secret_token=self.settings.telegram_webhook_secret,
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                    max_connections=10,
                )
                info = await self.application.bot.get_webhook_info()
                logger.info(
                    "PTB webhook configured: url=%s pending=%s",
                    info.url,
                    info.pending_update_count,
                )
            except Exception:
                logger.exception("PTB: failed to configure the webhook")

        logger.info("PTB engine ready as @%s", self.username)

    async def shutdown(self) -> None:
        try:
            await self.application.stop()
        finally:
            await self.application.shutdown()

    async def handle_update(self, payload: dict[str, Any]) -> None:
        update = Update.de_json(payload, self.application.bot)
        if update is None:
            logger.warning("PTB: could not decode update payload")
            return
        await self.application.update_queue.put(update)

    def _private_miniapp_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Open TroMate Mini App",
                        web_app=WebAppInfo(url=self.settings.miniapp_url),
                    )
                ]
            ]
        )

    def _group_miniapp_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Open TroMate Mini App",
                        url=miniapp_direct_link(self.username),
                    )
                ]
            ]
        )

    def _balance_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("Refresh balances", callback_data="balance:refresh")]]
        )

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        chat = update.effective_chat
        if message is None or chat is None:
            return
        if chat.type == "private":
            await message.reply_text(
                start_text(self.name, self.username),
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await message.reply_text(
                group_start_text(self.name, self.username),
                reply_markup=self._group_miniapp_keyboard(),
            )

    async def _on_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return
        await message.reply_text(balance_text(), reply_markup=self._balance_keyboard())

    async def _on_app(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        chat = update.effective_chat
        if message is None or chat is None:
            return
        if chat.type == "private":
            await message.reply_text(
                "Open the TroMate Mini App from the button below.",
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await message.reply_text(
                f"Open the TroMate Mini App: {miniapp_direct_link(self.username)}",
                reply_markup=self._group_miniapp_keyboard(),
            )

    async def _on_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is not None:
            await message.reply_text(help_text(self.name))

    async def _on_slow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await asyncio.sleep(2)
        message = update.effective_message
        if message is not None:
            await message.reply_text("Slow handler finished after 2 seconds.")

    async def _on_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        query = update.callback_query
        if query is None:
            return
        await query.answer("Balances refreshed")
        if query.message is not None:
            await query.edit_message_text(
                balance_text(),
                reply_markup=self._balance_keyboard(),
            )

    async def _on_error(
        self,
        update: object,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        error = context.error
        logger.error(
            "PTB handler error: %s",
            error,
            exc_info=(type(error), error, error.__traceback__) if error else None,
        )
