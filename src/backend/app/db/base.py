"""Declarative base and shared column helpers for the ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, func, text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names so Alembic can create, compare and drop them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for every TroMate table.

    ``AsyncAttrs`` exposes ``await obj.awaitable_attrs.<relationship>`` for lazy loads
    under ``AsyncSession``; relationships that are always needed are eager-loaded instead.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class UUIDPrimaryKeyMixin:
    """``id UUID PRIMARY KEY DEFAULT gen_random_uuid()``.

    The Python-side ``uuid4`` default makes the id available before flush, so related rows
    can reference it inside the same unit of work.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        sort_order=-100,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class CreatedAtMixin:
    """``created_at TIMESTAMPTZ NOT NULL DEFAULT now()``."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


def str_enum(enum_cls: type[StrEnum], *, length: int = 16) -> Enum:
    """Store a ``StrEnum`` as ``VARCHAR(length)`` plus a named ``CHECK (col IN (...))``.

    A VARCHAR + CHECK (rather than a native PostgreSQL ENUM type) matches the data
    dictionary in SCRUM-117 and keeps later value changes to a plain constraint swap.
    """

    return Enum(
        enum_cls,
        name=_snake(enum_cls.__name__),
        native_enum=False,
        create_constraint=True,
        length=length,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


def _snake(name: str) -> str:
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")
