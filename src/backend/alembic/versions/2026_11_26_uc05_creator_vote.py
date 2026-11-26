"""Record implicit creator votes for pending expenses shared before BR01."""

from alembic import op

revision = "uc05creatorvote"
down_revision = "uc05delivery"
branch_labels = None
depends_on = None


def upgrade():
    # Serialize the repair with the review service, which locks the expense before voting.
    op.execute("""
        CREATE TEMP TABLE repaired_creator_votes ON COMMIT DROP AS
        WITH repaired AS (
            INSERT INTO expense_approvals (expense_id, member_id, decision, expense_version)
            SELECT id, created_by_member_id, 'AGREE', version FROM expenses
            WHERE status = 'PENDING' AND created_by_member_id = payer_member_id
            ORDER BY id FOR UPDATE
            ON CONFLICT (expense_id, member_id) DO UPDATE
                SET decision = 'AGREE', expense_version = EXCLUDED.expense_version,
                    reason_code = NULL, reason_note = NULL, voted_at = now()
                WHERE expense_approvals.expense_version < EXCLUDED.expense_version
            RETURNING expense_id
        )
        SELECT expense_id FROM repaired
    """)
    # If everyone else already agreed, there may never be another vote to close the expense.
    op.execute("""
        CREATE TEMP TABLE newly_confirmed ON COMMIT DROP AS
        WITH confirmed AS (
            UPDATE expenses e
            SET status = 'CONFIRMED', confirmed_at = now(), review_deadline = NULL,
                version = version + 1
            WHERE id IN (SELECT expense_id FROM repaired_creator_votes)
              AND total_amount = (
                  SELECT sum(share_amount) FROM expense_splits WHERE expense_id = e.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM expense_splits s
                  WHERE s.expense_id = e.id AND NOT EXISTS (
                      SELECT 1 FROM expense_approvals a WHERE a.expense_id = e.id
                      AND a.member_id = s.member_id AND a.expense_version = e.version
                      AND a.decision = 'AGREE'
                  )
              )
            RETURNING id, room_id, payer_member_id, total_amount, version, confirmed_at
        )
        SELECT * FROM confirmed
    """)
    op.execute("""
        UPDATE expense_approvals a SET expense_version = e.version FROM newly_confirmed e
        WHERE a.expense_id = e.id AND a.expense_version = e.version - 1
    """)
    op.execute("""
        INSERT INTO ledger_entries
            (expense_id, room_id, member_id, entry_type, amount_delta, effective_at)
        SELECT e.id, e.room_id, d.member_id, 'EXPENSE', sum(d.amount), e.confirmed_at
        FROM newly_confirmed e
        CROSS JOIN LATERAL (
            SELECT e.payer_member_id AS member_id, e.total_amount AS amount
            UNION ALL
            SELECT member_id, -share_amount FROM expense_splits WHERE expense_id = e.id
        ) d
        GROUP BY e.id, e.room_id, e.confirmed_at, d.member_id HAVING sum(d.amount) <> 0
    """)
    op.execute("""
        INSERT INTO expense_deliveries (expense_id, revision, kind, body)
        SELECT id, content_revision, 'card', '' FROM expenses
        WHERE card_message_id IS NOT NULL AND id IN (SELECT expense_id FROM repaired_creator_votes)
    """)


def downgrade():
    # Restoring the previous schema preserves recorded votes and posted ledger entries.
    pass
