"""Persist draft state and the active Telegram card."""

import sqlalchemy as sa

from alembic import op

revision = "124draft"
down_revision = "bd5bbd1d9957"
branch_labels = None
depends_on = None


def _statuses(include_draft):
    values = "'PENDING','CONFIRMED','DISPUTED','CANCELLED'"
    if include_draft:
        values += ",'DRAFT'"
    name = op.f("ck_expenses_expense_status")
    op.drop_constraint(name, "expenses", type_="check")
    op.create_check_constraint(name, "expenses", f"status IN ({values})")


def upgrade():
    _statuses(True)
    op.add_column(
        "expenses", sa.Column("content_revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("expenses", sa.Column("cancelled_at", sa.DateTime(timezone=True)))
    op.add_column(
        "expenses",
        sa.Column(
            "cancelled_by_member_id",
            sa.Uuid(),
            sa.ForeignKey("room_members.id", ondelete="RESTRICT"),
        ),
    )
    op.add_column("expenses", sa.Column("card_message_id", sa.BigInteger(), nullable=True))


def downgrade():
    op.execute("UPDATE expenses SET status='CANCELLED' WHERE status='DRAFT'")
    _statuses(False)
    op.drop_column("expenses", "content_revision")
    op.drop_column("expenses", "cancelled_at")
    op.drop_column("expenses", "cancelled_by_member_id")
    op.drop_column("expenses", "card_message_id")
