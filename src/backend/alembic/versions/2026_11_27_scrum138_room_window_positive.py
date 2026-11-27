"""room window: only require > 0; range is validated by the app (SCRUM-138)

The BR03 range (production: 1 to 30 days) now comes from DurationSettings so the test
environment can use a 5-minute window. Expense windows are already latched per expense in
``expenses.review_window_minutes``, so existing deadlines are unaffected.

Revision ID: scrum138window
Revises: uc05creatorvote
Create Date: 2026-11-27 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "scrum138window"
down_revision: str | Sequence[str] | None = "uc05creatorvote"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_rooms_review_timeout_allowed"), "rooms", type_="check")
    op.create_check_constraint(
        op.f("ck_rooms_review_timeout_allowed"),
        "rooms",
        "review_timeout_minutes IS NULL OR review_timeout_minutes > 0",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_rooms_review_timeout_allowed"), "rooms", type_="check")
    # Windows outside the production range (e.g. 5-minute test windows) are reset to
    # "not adopted", as in revision a3c7e91f4b20.
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
