"""Interface contract and command definitions for the TroMate Telegram Bot (SCRUM-123)."""

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
        description="Open TroMate Mini App",
        scope="all",
        usage_example="/start",
    ),
    BotCommandSpec(
        command="help",
        description="Show available commands and /new usage",
        scope="all",
        usage_example="/help",
    ),
    BotCommandSpec(
        command="app",
        description="Open the Mini App",
        scope="all",
        usage_example="/app",
    ),
    BotCommandSpec(
        command="balance",
        description="Show room balances",
        scope="group",
        usage_example="/balance",
    ),
    BotCommandSpec(
        command="new",
        description="Log a shared expense via Vietnamese text",
        scope="group",
        usage_example="/new Đi chợ 150k chia tao với Nam",
    ),
)

CALLBACK_PREFIX_EXPENSE_AGREE = "expense:agree"
CALLBACK_PREFIX_EXPENSE_REJECT = "expense:reject"
CALLBACK_PREFIX_EXPENSE_EDIT = "expense:edit"
CALLBACK_PREFIX_BALANCE_REFRESH = "balance:refresh"


def build_agree_callback(expense_id: uuid.UUID, version: int) -> str:
    """Build callback data for ``[Agree]`` within Telegram's 64-byte limit."""

    return f"{CALLBACK_PREFIX_EXPENSE_AGREE}:{expense_id}:{version}"


def build_reject_callback(expense_id: uuid.UUID, version: int) -> str:
    """Build callback data for ``[Reject]`` within Telegram's 64-byte limit."""

    return f"{CALLBACK_PREFIX_EXPENSE_REJECT}:{expense_id}:{version}"


def build_edit_callback(expense_id: uuid.UUID) -> str:
    """Build fallback callback data for ``[Edit]`` when Mini App deep link is unavailable."""

    return f"{CALLBACK_PREFIX_EXPENSE_EDIT}:{expense_id}"


@dataclass(frozen=True, slots=True)
class IncomingGroupMessage:
    """Normalized incoming ``/new`` group message passed from router to controller."""

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
    """Presentation payload for the UC01 inline confirmation card."""

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
    extraction_source: str = "fallback"


class ConfirmationCardBuilderProtocol(Protocol):
    """Formats a ``ConfirmationCardDTO`` into Telegram HTML text and inline buttons."""

    def render_html(self, card: ConfirmationCardDTO) -> str:
        """Render the expense summary, splits, and status as Telegram HTML."""

    def build_inline_buttons(self, card: ConfirmationCardDTO) -> object:
        """Build inline keyboard rows for ``[Agree]``, ``[Reject]``, and ``[Edit]``."""


class ExpenseBotControllerProtocol(Protocol):
    """Boundary interface connecting ``/new`` bot handler to application services."""

    async def handle_new_expense(
        self,
        message: IncomingGroupMessage,
    ) -> ConfirmationCardDTO | None:
        """Process a ``/new <text>`` command and return a confirmation card payload."""
