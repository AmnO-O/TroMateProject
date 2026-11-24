"""Interface contract and command definitions for the TroMate Telegram Bot (Subtask 3).

This module defines ONLY the boundary DTOs, command specifications, callback schemas,
and Protocol interfaces. Concrete aiogram 3 handlers will be wired in a later step.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class BotCommandSpec:
    """Metadata for one Telegram slash command registered via ``set_my_commands``."""

    command: str
    description: str
    scope: Literal["all", "private", "group"] = "all"
    usage_example: str = ""


TROMATE_BOT_COMMANDS: tuple[BotCommandSpec, ...] = (
    BotCommandSpec(
        command="start",
        description="Khởi động bot & mở liên kết TroMate Mini App",
        scope="all",
        usage_example="/start",
    ),
    BotCommandSpec(
        command="help",
        description="Xem hướng dẫn sử dụng và cú pháp nhập chi tiêu tự nhiên",
        scope="all",
        usage_example="/help",
    ),
    BotCommandSpec(
        command="app",
        description="Mở nhanh giao diện TroMate Mini App",
        scope="all",
        usage_example="/app",
    ),
    BotCommandSpec(
        command="balance",
        description="Xem tóm tắt số dư công nợ hiện tại của phòng",
        scope="group",
        usage_example="/balance",
    ),
    BotCommandSpec(
        command="log",
        description="Ghi nhận khoản chi tiêu chung mới (hoặc nhắn trực tiếp trong group)",
        scope="group",
        usage_example="/log Đi chợ 150k chia tao với Nam",
    ),
    BotCommandSpec(
        command="pending",
        description="Liệt kê các khoản chi tiêu đang chờ xác nhận trong phòng",
        scope="group",
        usage_example="/pending",
    ),
)

CALLBACK_PREFIX_EXPENSE_AGREE = "expense:agree"
CALLBACK_PREFIX_EXPENSE_REJECT = "expense:reject"
CALLBACK_PREFIX_EXPENSE_EDIT = "expense:edit"
CALLBACK_PREFIX_BALANCE_REFRESH = "balance:refresh"


def build_agree_callback(expense_id: uuid.UUID, version: int) -> str:
    """Build callback data for ``[✅ Đồng ý / Agree]`` within Telegram's 64-byte limit."""

    return f"{CALLBACK_PREFIX_EXPENSE_AGREE}:{expense_id}:{version}"


def build_reject_callback(expense_id: uuid.UUID, version: int) -> str:
    """Build callback data for ``[❌ Từ chối / Reject]`` within Telegram's 64-byte limit."""

    return f"{CALLBACK_PREFIX_EXPENSE_REJECT}:{expense_id}:{version}"


def build_edit_callback(expense_id: uuid.UUID) -> str:
    """Build callback data / Mini App deep-link identifier for ``[✏️ Sửa / Edit]``."""

    return f"{CALLBACK_PREFIX_EXPENSE_EDIT}:{expense_id}"


@dataclass(frozen=True, slots=True)
class IncomingGroupMessage:
    """Normalized incoming Telegram group message passed from router to controller."""

    telegram_chat_id: int
    chat_title: str
    telegram_user_id: int
    sender_display_name: str
    sender_username: str | None
    message_id: int
    text: str


@dataclass(frozen=True, slots=True)
class SplitLineDTO:
    """One participant line displayed inside a confirmation card."""

    display_name: str
    share_amount: int
    decision: Literal["PENDING", "AGREE", "REJECT"] = "PENDING"


@dataclass(frozen=True, slots=True)
class ConfirmationCardDTO:
    """Presentation payload for the UC01/UC05 inline confirmation card."""

    expense_id: uuid.UUID
    version: int
    description: str
    total_amount: int
    payer_name: str
    category_name: str
    status: Literal["PENDING", "DISPUTED", "CONFIRMED", "CANCELLED"]
    splits: tuple[SplitLineDTO, ...]
    review_deadline: datetime | None = None
    miniapp_edit_url: str = ""


@dataclass(frozen=True, slots=True)
class BotActionReply:
    """Renderable bot reply returned by controller methods to the Telegram transport."""

    text: str
    confirmation_card: ConfirmationCardDTO | None = None
    reply_to_message_id: int | None = None


class ConfirmationCardBuilderProtocol(Protocol):
    """Formats a ``ConfirmationCardDTO`` into Telegram HTML text and inline buttons."""

    def render_html(self, card: ConfirmationCardDTO) -> str:
        """Render the expense summary, splits, and approval status as Telegram HTML."""

    def build_inline_buttons(self, card: ConfirmationCardDTO) -> list[list[dict[str, str]]]:
        """Build button rows for ``[Agree]``, ``[Reject]``, and ``[Edit]``."""


class ExpenseBotControllerProtocol(Protocol):
    """Boundary interface connecting Telegram bot handlers to application services."""

    async def handle_expense_text(self, message: IncomingGroupMessage) -> BotActionReply | None:
        """Handle a ``/log`` command or natural-language expense message in a group chat.

        Returns ``None`` when the message is ordinary chatter (not an expense log).
        """

    async def handle_list_pending(self, telegram_chat_id: int) -> BotActionReply:
        """Return a summary of ``PENDING`` expenses awaiting confirmation in the room."""

    async def handle_balance_summary(self, telegram_chat_id: int) -> BotActionReply:
        """Return the room's current net balance summary."""

    async def handle_approval_callback(
        self,
        *,
        telegram_chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> ConfirmationCardDTO:
        """Process ``expense:agree`` or ``expense:reject`` and return the updated card."""
