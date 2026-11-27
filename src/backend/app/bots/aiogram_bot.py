from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import suppress
from dataclasses import replace
from html import escape
from typing import Any

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
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
    group_start_text,
    help_text,
    live_balance_text,
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
from app.services.balance_service import BalanceService
from app.services.errors import ConflictError, ServiceError
from app.services.expense_service import ExpenseDraft, ExpenseReview, ExpenseService

logger = logging.getLogger(__name__)


class AiogramEngine(BotEngine):
    name = "aiogram"

    def __init__(
        self,
        settings: Settings,
        *,
        expense_service: ExpenseService | None = None,
        balance_service: BalanceService | None = None,
    ) -> None:
        self.settings = settings
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self.router = Router()
        self._delivery_event = asyncio.Event()
        self._delivery_task = None
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
        self._balance_service = balance_service or BalanceService()

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
        self.router.callback_query.register(self._on_review, F.data.startswith("expense:"))
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

        self._delivery_task = asyncio.create_task(self._delivery_loop())
        logger.info("aiogram engine ready as @%s", self.username)

    async def shutdown(self) -> None:
        if self._delivery_task:
            self._delivery_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._delivery_task
        await self._tasks.shutdown()
        await self._http_client.aclose()
        await self.bot.session.close()

    @property
    def expense_service(self):
        return self._expense_service

    async def resolve_room(self, chat_id, *, user_id=None):
        if await self.expense_service.resolve_room(chat_id, user_id=user_id):
            self.wake_delivery()

    def wake_delivery(self):
        self._delivery_event.set()

    async def _delivery_loop(self):
        while True:
            self._delivery_event.clear()
            try:
                if await self.expense_service.deliver_next(self._deliver):
                    continue
            except Exception:
                logger.exception("Expense delivery worker will retry")
            with suppress(TimeoutError):
                await asyncio.wait_for(self._delivery_event.wait(), timeout=5)

    async def _deliver(self, job, expense, review, chat_id, creator):
        if job.kind == "retire":
            try:
                await self.bot.edit_message_text(
                    "Phiên bản cũ · "
                    + escape(review.description)
                    + "\n"
                    + escape(review.last_change),
                    chat_id=chat_id,
                    message_id=job.recipient,
                    reply_markup=None,
                )
            except TelegramBadRequest as exc:
                if not any(
                    t in exc.message.lower() for t in ("not modified", "message to edit not found")
                ):
                    raise
            return
        if job.kind in {"reminder", "notice"}:
            recipient = job.recipient or creator
            text = (
                escape(job.body)
                if job.kind == "notice"
                else ("Nhắc xử lý khoản chi đang tranh chấp: " + escape(review.description))
            )
            try:
                await self.bot.send_message(recipient, text)
            except (TelegramForbiddenError, TelegramBadRequest) as exc:
                if (
                    isinstance(exc, TelegramBadRequest)
                    and "chat not found" not in exc.message.lower()
                ):
                    raise
                await self.bot.send_message(
                    chat_id, f'<a href="tg://user?id={recipient}">Thông báo</a> · ' + text
                )
            return
        card = self._review_card(chat_id, review)
        if card.rejection and len(card.rejection) > 1200:
            card = replace(card, rejection=card.rejection[:1200] + "… Xem đủ lý do trong Mini App.")
        text = render_confirmation_card_html(card)
        if review.last_change:
            text += "\n" + escape(review.last_change)
        if review.status == "DISPUTED" or expense.card_revision != review.content_revision:
            text += "\n" + " ".join(
                f'<a href="tg://user?id={uid}">{escape(name)}</a>' for uid, name in review.mentions
            )
        keyboard = (
            build_confirmation_keyboard(card) if review.status in {"PENDING", "DISPUTED"} else None
        )
        previous = expense.card_message_id
        if previous and expense.card_revision == review.content_revision:
            try:
                await self.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=previous, reply_markup=keyboard
                )
                return
            except TelegramBadRequest as exc:
                if "not modified" in exc.message.lower():
                    return
                if "message to edit not found" not in exc.message.lower():
                    raise
                previous = None
        sent = await self.bot.send_message(chat_id, text, reply_markup=keyboard)
        expense.card_message_id = sent.message_id
        expense.card_revision = review.content_revision
        return previous

    async def handle_update(self, payload: dict[str, Any]) -> None:
        update = Update.model_validate(payload, context={"bot": self.bot})

        async def dispatch():
            message = update.message or (
                update.callback_query.message if update.callback_query else None
            )
            if message and message.chat.type in {"group", "supergroup"}:
                await self.resolve_room(message.chat.id)
            await self.dp.feed_update(self.bot, update)

        self._tasks.spawn(dispatch())

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

    def _group_miniapp_keyboard(self, chat_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Open TroMate Mini App",
                        url=miniapp_direct_link(self.username, chat_id),
                    )
                ]
            ]
        )

    def _balance_keyboard(self, chat_id: int, chat_type: str) -> InlineKeyboardMarkup:
        rows = [[InlineKeyboardButton(text="🔄 Làm mới", callback_data="balance:refresh")]]
        if chat_type != "private":
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Xem chi tiết trong Mini App",
                        url=miniapp_direct_link(self.username, chat_id),
                    )
                ]
            )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    async def _balance_reply(self, chat_id: int, chat_type: str) -> dict[str, Any]:
        # Plain text: member names are user-controlled and must not be parsed as HTML.
        return {
            "text": await live_balance_text(self._balance_service, chat_id, chat_type),
            "parse_mode": None,
            "reply_markup": self._balance_keyboard(chat_id, chat_type),
        }

    async def _on_start(self, message: Message) -> None:
        if message.chat.type == "private":
            await message.answer(
                start_text(self.name, self.username),
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await message.answer(
                group_start_text(self.name, self.username, message.chat.id),
                reply_markup=self._group_miniapp_keyboard(message.chat.id),
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
                await self._expense_service.share_expense_draft(
                    draft, card_message_id=callback.message.message_id
                )
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

            self.wake_delivery()
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
        await message.answer(**await self._balance_reply(message.chat.id, message.chat.type))

    async def _on_app(self, message: Message) -> None:
        if message.chat.type == "private":
            await message.answer(
                "Open the TroMate Mini App from the button below.",
                reply_markup=self._private_miniapp_keyboard(),
            )
        else:
            await message.answer(
                f"Open the TroMate Mini App: {miniapp_direct_link(self.username, message.chat.id)}",
                reply_markup=self._group_miniapp_keyboard(message.chat.id),
            )

    async def _on_help(self, message: Message) -> None:
        await message.answer(help_text(self.name))

    async def _on_slow(self, message: Message) -> None:
        await asyncio.sleep(2)
        await message.answer("Slow handler finished after 2 seconds.")

    async def _on_callback(self, callback: CallbackQuery) -> None:
        message = callback.message
        if not isinstance(message, Message):
            await callback.answer()
            return
        # handle_update already confirmed overdue expenses of this group before dispatching.
        reply = await self._balance_reply(message.chat.id, message.chat.type)
        try:
            await message.edit_text(**reply)
        except TelegramBadRequest as exc:
            if "not modified" not in exc.message.lower():
                raise
        await callback.answer("Đã cập nhật số dư")

    async def _on_review(self, callback: CallbackQuery) -> None:
        message = callback.message
        if not isinstance(message, Message):
            await callback.answer("Expense card unavailable.", show_alert=True)
            return
        try:
            _, action, raw_id, revision = (callback.data or "").split(":")
            expense_id, version = uuid.UUID(raw_id), int(revision)
            if action not in {"agree", "share"}:
                raise ConflictError("Hãy dùng thẻ mới nhất để thực hiện thao tác này.")
            await self._expense_service.review(
                expense_id=expense_id,
                version=version,
                action=action,
                telegram_chat_id=message.chat.id,
                telegram_user_id=callback.from_user.id,
            )
        except ConflictError as exc:
            await callback.answer(exc.message, show_alert=True)
            await self.publish_expense(
                uuid.UUID(raw_id),
                message.chat.id,
                callback.from_user.id,
                fallback=message.message_id,
            )
            return
        except (ValueError, ServiceError) as exc:
            await callback.answer(
                exc.message if isinstance(exc, ServiceError) else "Nút này đã cũ.", show_alert=True
            )
            return
        await callback.answer()
        self.wake_delivery()

    def _expense_url(self, expense_id, chat_id, version):
        return f"https://t.me/{self.username}?startapp=expense_{expense_id.hex}_{chat_id}_{version}"

    async def publish_expense(self, expense_id, chat_id, user_id, *, fallback=None):
        await self._expense_service.queue_refresh(expense_id, chat_id, user_id, fallback)
        self.wake_delivery()

    def _review_card(self, chat_id: int, review: ExpenseReview) -> ConfirmationCardDTO:
        return ConfirmationCardDTO(
            miniapp_edit_url=self._expense_url(review.expense_id, chat_id, review.version),
            split_method=review.split_type.value,
            balances=review.balances,
            rejection=review.rejection,
            expense_id=review.expense_id,
            version=review.version,
            description=review.description,
            total_amount=review.total_amount,
            payer_name=review.payer_name,
            category_name=review.category_name,
            status=review.status.value,
            splits=tuple(
                SplitLineDTO(
                    s.display_name, s.share_amount, s.decision.value if s.decision else "PENDING"
                )
                for s in review.splits
            ),
            review_deadline=review.review_deadline,
            agreed_count=review.agreed_count,
            voter_count=review.voter_count,
            payer_decision=review.payer_decision.value if review.payer_decision else "PENDING",
        )
