"""Finish creator-only shares that already have their sole required vote."""

from alembic import op

revision = "uc05soloshare"
down_revision = "uc05creatorvote"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        WITH confirmed AS (
            UPDATE expenses e
            SET status = 'CONFIRMED', confirmed_at = now(),
                review_deadline = NULL, version = version + 1
            WHERE e.status = 'PENDING' AND e.created_by_member_id = e.payer_member_id
              AND EXISTS (
                  SELECT 1 FROM expense_splits s WHERE s.expense_id = e.id
                    AND s.member_id = e.payer_member_id AND s.share_amount = e.total_amount
              )
              AND NOT EXISTS (
                  SELECT 1 FROM expense_splits s WHERE s.expense_id = e.id
                    AND s.member_id <> e.payer_member_id
              )
              AND EXISTS (
                  SELECT 1 FROM expense_approvals a WHERE a.expense_id = e.id
                    AND a.member_id = e.created_by_member_id AND a.decision = 'AGREE'
                    AND a.expense_version = e.version
              )
            RETURNING id, version, created_by_member_id, content_revision, card_message_id
        ), carried_vote AS (
            UPDATE expense_approvals a SET expense_version = c.version
            FROM confirmed c WHERE a.expense_id = c.id AND a.member_id = c.created_by_member_id
        )
        INSERT INTO expense_deliveries (expense_id, revision, kind, body)
        SELECT id, content_revision, 'card', '' FROM confirmed WHERE card_message_id IS NOT NULL
    """)


def downgrade():
    # A data repair preserves completed confirmations on downgrade.
    pass
