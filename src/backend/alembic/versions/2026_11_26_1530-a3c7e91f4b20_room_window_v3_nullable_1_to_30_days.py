"""room window v3 nullable 1 to 30 days (BR03)

Revision ID: a3c7e91f4b20
Revises: bd5bbd1d9957
Create Date: 2026-11-26 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c7e91f4b20"
down_revision: str | Sequence[str] | None = "bd5bbd1d9957"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("ck_rooms_review_timeout_allowed"), "rooms", type_="check")
    op.alter_column(
        "rooms",
        "review_timeout_minutes",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
    op.execute(
        "UPDATE rooms SET review_timeout_minutes = NULL "
        "WHERE review_timeout_minutes < 1440 OR review_timeout_minutes > 43200"
    )
    op.create_check_constraint(
        op.f("ck_rooms_review_timeout_allowed"),
        "rooms",
        "review_timeout_minutes IS NULL OR "
        "(review_timeout_minutes >= 1440 AND review_timeout_minutes <= 43200)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_rooms_review_timeout_allowed"), "rooms", type_="check")
    op.execute(
        "UPDATE rooms SET review_timeout_minutes = 5 "
        "WHERE review_timeout_minutes IS NULL "
        "OR review_timeout_minutes NOT IN (5, 15, 30, 60, 360, 720, 1440)"
    )
    op.alter_column(
        "rooms",
        "review_timeout_minutes",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("5"),
    )
    op.create_check_constraint(
        op.f("ck_rooms_review_timeout_allowed"),
        "rooms",
        "review_timeout_minutes IN (5, 15, 30, 60, 360, 720, 1440)",
    )
