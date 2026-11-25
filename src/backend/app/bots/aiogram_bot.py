from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    Update,
    WebAppInfo,
)

from app.adapters.ai_extraction import AIExtractionAdapter
from app.bots.base import BotEngine, TaskTracker
from app.bots.common import (
    balance_text,
    group_start_text,
    help_text,
    miniapp_direct_link,
    start_text,
)
from app.bots.expense_card import build_confirmation_keyboard, render_confirmation_card_html
from app.bots.interface import (
    TROMATE_BOT_COMMANDS,
    ConfirmationCardDTO,
    SplitLineDTO,
)
from app.core.config import Settings
from app.services.errors import ServiceError
from app.services.expense_service import ExpenseService

logger = logging.getLogger(__name__)


class AiogramEngine(BotEngine):
    name = "aiogram"

    def __init__(
        self,
        settings: Settings,
        *,
        expense_service: ExpenseService | None = None,
    ) -> None:
        self.settings = settings
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self.router = Router()
        self._tasks = TaskTracker("app.bots.aiogram_bot")
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._expense_service = expense_service or ExpenseService(
            extractor=AIExtractionAdapter(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                client=self._http_client,
            ),
        )

        self.router.message.register(self._on_start, CommandStart())
        self.router.message.register(self._on_new_expense, Command("new"))
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
            private_commands = [
                BotCommand(command=spec.command, description=spec.description)
                for spec in TROMATE_BOT_COMMANDS
                if spec.scope in {"all", "private"}
            ]
            group_commands = [
                BotCommand(command=spec.command, description=spec.description)
                for spec in TROMATE_BOT_COMMANDS
                if spec.scope in {"all", "group"}
            ]
            await self.bot.set_my_commands(
                private_commands,
                scope=BotCommandScopeAllPrivateChats(),
            )
            await self.bot.set_my_commands(
                group_commands,
                scope=BotCommandScopeAllGroupChats(),
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
        await self._http_client.aclose()
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

    async def _on_new_expense(self, message: Message, command: CommandObject) -> None:
        if message.chat.type not in {"group", "supergroup"}:
            await message.answer(
                "Lệnh /new chỉ dùng trong nhóm chat phòng trọ.\n"
                "Ví dụ: <code>/new Đi chợ 150k chia tao với Nam</code>"
            )
            return

        if message.from_user is None:
            return

        raw_text = (command.args or "").strip()
        if not raw_text:
            await message.answer(
                "Vui lòng nhập nội dung chi tiêu sau lệnh /new.\n"
                "Ví dụ: <code>/new Đi chợ 150k chia tao với Nam</code>"
            )
            return

        try:
            created = await self._expense_service.log_expense_from_text(
                telegram_chat_id=message.chat.id,
                chat_title=message.chat.title or f"Room {message.chat.id}",
                telegram_user_id=message.from_user.id,
                sender_display_name=message.from_user.full_name,
                sender_username=message.from_user.username,
                text=raw_text,
            )
        except ServiceError as exc:
            await message.answer(f"⚠️ Không thể ghi nhận chi tiêu: {exc.message}")
            return

        if created is None:
            await message.answer(
                "⚠️ Không nhận diện được số tiền hợp lệ.\n"
                "Ví dụ: <code>/new Tiền điện 650k chia đều cả phòng</code>"
            )
            return

        edit_url = (
            f"https://t.me/{self.username}?startapp=expense_{created.expense_id}"
            if self.username
            else ""
        )
        card = ConfirmationCardDTO(
            expense_id=created.expense_id,
            version=created.version,
            description=created.description,
            total_amount=created.total_amount,
            payer_name=created.payer_name,
            category_name=created.category_name,
            status=created.status.value,
            splits=tuple(
                SplitLineDTO(display_name=s.display_name, share_amount=s.share_amount)
                for s in created.splits
            ),
            review_deadline=created.review_deadline,
            miniapp_edit_url=edit_url,
            extraction_source=created.extraction_source,
        )
        await message.answer(
            render_confirmation_card_html(card),
            reply_markup=build_confirmation_keyboard(card),
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
