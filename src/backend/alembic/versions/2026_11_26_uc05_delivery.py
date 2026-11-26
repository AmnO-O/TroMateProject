"""Transactional Telegram delivery and dispute review history."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "uc05delivery"
down_revision = "uc01uc05merge"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "expenses",
        sa.Column("dispute_reasons", JSONB(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "expenses", sa.Column("last_change", sa.Text(), nullable=False, server_default="")
    )
    op.add_column(
        "expenses", sa.Column("card_revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.execute("UPDATE expenses SET card_revision=content_revision")
    op.create_table(
        "expense_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "expense_id",
            sa.Uuid(),
            sa.ForeignKey("expenses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("recipient", sa.BigInteger()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_expense_deliveries_available_at", "expense_deliveries", ["available_at"])
    op.execute("""INSERT INTO expense_deliveries (expense_id, revision,kind,body,available_at)
                  SELECT id,content_revision,'reminder','',now()+interval '3 days'
                  FROM expenses WHERE status='DISPUTED'""")


def downgrade():
    op.drop_table("expense_deliveries")
    for col in ("card_revision", "last_change", "dispute_reasons"):
        op.drop_column("expenses", col)
