"""Interface contract and command definitions for the TroMate Telegram Bot (SCRUM-123)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


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


def build_edit_callback(expense_id: uuid.UUID, version: int) -> str:
    """Build fallback callback data for ``[Edit]`` when Mini App deep link is unavailable."""

    return f"{CALLBACK_PREFIX_EXPENSE_EDIT}:{expense_id}:{version}"


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
    agreed_count: int = 0
    voter_count: int = 0
    payer_decision: str = "PENDING"
