from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import replace
from html import escape
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
    ForceReply,
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
from app.bots.expense_card import (
    build_confirmation_keyboard,
    build_draft_summary_keyboard,
    render_confirmation_card_html,
    render_draft_summary_html,
)
from app.bots.interface import (
    TROMATE_BOT_COMMANDS,
    ConfirmationCardDTO,
    DraftSummaryDTO,
    SplitLineDTO,
)
from app.core.config import Settings
from app.services.errors import ServiceError
from app.services.expense_service import ExpenseDraft, ExpenseService

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
        # shortcut: in-memory draft store is lost on restart and not shared across workers; upgrade
        # to Redis/DB when running multiple replicas
        self._drafts: dict[uuid.UUID, ExpenseDraft] = {}
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
        self.router.message.register(
            self._on_draft_edit_reply,
            F.text,
            F.reply_to_message.text.startswith("UC01 "),
        )
        self.router.callback_query.register(
            self._on_draft_action,
            F.data.startswith("draft:"),
        )
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

    def _store_draft(self, draft: ExpenseDraft) -> None:
        if draft.draft_id not in self._drafts and len(self._drafts) >= 1000:
            oldest_id = next(iter(self._drafts))
            del self._drafts[oldest_id]
        self._drafts[draft.draft_id] = draft

    @staticmethod
    def _draft_to_summary(draft: ExpenseDraft) -> DraftSummaryDTO:
        return DraftSummaryDTO(
            draft_id=draft.draft_id,
            description=draft.description,
            total_amount=draft.total_amount,
            payer_name=draft.payer_name,
            category_name=draft.category_name,
            splits=tuple(
                SplitLineDTO(display_name=s.display_name, share_amount=s.share_amount)
                for s in draft.splits
            ),
            room_window_minutes=draft.room_window_minutes,
            auto_confirm_enabled=draft.auto_confirm_enabled,
            manual_reason=draft.manual_reason,
            extraction_source=draft.extraction_source,
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
            draft = await self._expense_service.prepare_expense_draft(
                telegram_chat_id=message.chat.id,
                chat_title=message.chat.title or f"Room {message.chat.id}",
                telegram_user_id=message.from_user.id,
                sender_display_name=message.from_user.full_name,
                sender_username=message.from_user.username,
                text=raw_text,
            )
        except ServiceError as exc:
            await message.answer(f"⚠️ Không thể ghi nhận chi tiêu: {escape(exc.message)}")
            return

        if draft is None:
            await message.answer(
                "⚠️ Không nhận diện được số tiền hợp lệ.\n"
                "Ví dụ: <code>/new Tiền điện 650k chia đều cả phòng</code>"
            )
            return

        self._store_draft(draft)
        summary = self._draft_to_summary(draft)
        await message.answer(
            render_draft_summary_html(summary),
            reply_markup=build_draft_summary_keyboard(summary),
        )

    async def _on_draft_action(self, callback: CallbackQuery) -> None:
        parts = (callback.data or "").split(":")
        if len(parts) != 3 or parts[0] != "draft":
            return
        _, action, raw_id = parts
        try:
            draft_id = uuid.UUID(raw_id)
        except ValueError:
            await callback.answer("Yêu cầu không hợp lệ.", show_alert=True)
            return

        if not isinstance(callback.message, Message) or callback.from_user is None:
            return

        draft = self._drafts.get(draft_id)
        if draft is None:
            await callback.answer("Bản nháp đã hết hạn hoặc đã xử lý.", show_alert=True)
            return

        if callback.from_user.id != draft.creator_telegram_user_id:
            await callback.answer(
                "Chỉ người tạo khoản chi mới được thao tác trên bản nháp này.",
                show_alert=True,
            )
            return

        if action == "off":
            updated = draft.with_auto_confirm_disabled()
            self._store_draft(updated)
            summary = self._draft_to_summary(updated)
            await callback.message.edit_text(
                render_draft_summary_html(summary),
                reply_markup=build_draft_summary_keyboard(summary),
            )
            await callback.answer("Đã tắt tự động xác nhận.")
            return

        if action == "cancel":
            self._drafts.pop(draft_id, None)
            await callback.message.edit_text(
                "🗑️ Đã hủy ghi nhận khoản chi. Không có dữ liệu nào được lưu.",
                reply_markup=None,
            )
            await callback.answer("Đã hủy.")
            return

        if action == "edit":
            await callback.answer()
            await callback.message.answer(
                f"UC01 {draft_id}\nNhập lại nội dung khoản chi để cập nhật bản nháp:",
                reply_markup=ForceReply(force_reply=True),
            )
            return

        if action == "share":
            self._drafts.pop(draft_id, None)
            try:
                created = await self._expense_service.share_expense_draft(draft)
            except ServiceError as exc:
                self._store_draft(draft)
                await callback.answer(
                    f"⚠️ Không thể chia sẻ khoản chi: {exc.message}"[:200],
                    show_alert=True,
                )
                return
            except Exception:
                self._store_draft(draft)
                raise

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
                review_window_minutes=created.review_window_minutes,
                miniapp_edit_url=edit_url,
                extraction_source=created.extraction_source,
            )
            await callback.message.edit_text(
                render_confirmation_card_html(card),
                reply_markup=build_confirmation_keyboard(card),
            )
            await callback.answer("Đã chia sẻ khoản chi.")
            return

        await callback.answer("Thao tác không hợp lệ.", show_alert=True)

    async def _on_draft_edit_reply(self, message: Message) -> None:
        prompt = message.reply_to_message
        if prompt is None or not prompt.text:
            return
        if prompt.from_user is not None and prompt.from_user.id != self.bot.id:
            return

        first_line = prompt.text.splitlines()[0]
        tokens = first_line.split()
        if len(tokens) < 2:
            return
        try:
            draft_id = uuid.UUID(tokens[1])
        except ValueError:
            return

        existing = self._drafts.get(draft_id)
        if existing is None:
            await message.answer("Bản nháp đã hết hạn hoặc đã xử lý.")
            return
        if message.from_user is None or message.from_user.id != existing.creator_telegram_user_id:
            await message.answer("Chỉ người tạo khoản chi mới được chỉnh sửa bản nháp này.")
            return

        raw_text = (message.text or "").strip()
        if not raw_text:
            await message.answer(
                "⚠️ Vui lòng nhập nội dung chi tiêu hợp lệ.\n"
                "Ví dụ: <code>Đi chợ 200k chia tao với Nam</code>"
            )
            return

        try:
            new_draft = await self._expense_service.prepare_expense_draft(
                telegram_chat_id=existing.telegram_chat_id,
                chat_title=existing.chat_title,
                telegram_user_id=existing.creator_telegram_user_id,
                sender_display_name=existing.creator_display_name,
                sender_username=existing.creator_username,
                text=raw_text,
                source_type=existing.source_type,
            )
        except ServiceError as exc:
            await message.answer(f"⚠️ Không thể cập nhật bản nháp: {escape(exc.message)}")
            return

        if new_draft is None:
            await message.answer(
                "⚠️ Không nhận diện được số tiền hợp lệ.\n"
                "Ví dụ: <code>Tiền điện 650k chia đều cả phòng</code>"
            )
            return

        updated = replace(new_draft, draft_id=draft_id)
        if not existing.auto_confirm_enabled and existing.manual_reason == "CREATOR_DISABLED":
            updated = updated.with_auto_confirm_disabled()
        self._store_draft(updated)
        summary = self._draft_to_summary(updated)
        await message.answer(
            render_draft_summary_html(summary),
            reply_markup=build_draft_summary_keyboard(summary),
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
