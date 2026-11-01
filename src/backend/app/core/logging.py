from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure application logging once, to stdout."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def redact(value: str, visible: int = 4) -> str:
    """Return a short, non-sensitive representation of a secret."""

    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"
