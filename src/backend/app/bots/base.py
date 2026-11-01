from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any


class BotEngine(ABC):
    """Minimal interface shared by the three Telegram library adapters."""

    name: str = "base"
    username: str = ""

    @abstractmethod
    async def startup(self) -> None:
        """Initialize the library client and register handlers/webhook."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Close the library client and drain background work."""

    @abstractmethod
    async def handle_update(self, payload: dict[str, Any]) -> None:
        """Accept one Telegram update payload from the webhook."""


class TaskTracker:
    """Track fire-and-forget handler tasks and surface their exceptions."""

    def __init__(self, logger_name: str) -> None:
        self._tasks: set[asyncio.Task[Any]] = set()
        self._logger = logging.getLogger(logger_name)

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            self._logger.error(
                "Background bot task failed: %s",
                exc,
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    async def shutdown(self, grace_seconds: float = 5.0) -> None:
        if not self._tasks:
            return
        tasks = list(self._tasks)
        _, pending = await asyncio.wait(tasks, timeout=grace_seconds)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
