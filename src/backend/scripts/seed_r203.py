"""Seed / reset the PA4 common test data (room R203) for UC01 & UC05 manual testing.

Common test data (TestCases.xlsx, sheet "Features"): Telegram group "Phòng 203", Free plan,
auto-confirmation window 5 minutes, 0 of 10 scans used, no expenses, members Minh (Room Rep),
Lan, Huy, An, default categories.

Usage (from src/backend, with DATABASE_URL pointing at the QA Neon branch):

    # 1. See which rooms/users the bot has registered (find chat id and Telegram user ids)
    uv run python scripts/seed_r203.py list

    # 2. Seed (or re-seed) the room; --reset deletes every expense/ledger row of that room
    uv run python scripts/seed_r203.py seed --chat-id -100123 \
        --rep Minh:111 --member Lan:222 --member Huy:333 --member An:444 \
        --window 5 --reset --yes

Notes:
- The bot overwrites ``display_name`` with the Telegram full name on every interaction, so
  each test account's Telegram name must be exactly Minh / Lan / Huy / An (no last name).
- A 5-minute window needs migration ``scrum138window``; on plain v0.2.0 the database only
  accepts 1440..43200 minutes (use ``--window 1440``).
- Never point this at a production database: ``seed`` refuses to run without ``--yes``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text

from app.db.session import dispose_engine, get_engine

DEFAULT_CATEGORIES = (
    "Food & Drinks",
    "Groceries",
    "Household Supplies",
    "Utilities",
    "Rent",
    "Internet",
    "Other",
)
ROOM_NAME = "Phòng 203"


def _person(value: str) -> tuple[str, int]:
    name, _, tg_id = value.partition(":")
    if not name or not tg_id.lstrip("-").isdigit():
        raise argparse.ArgumentTypeError(f"expected Name:telegram_id, got {value!r}")
    return name, int(tg_id)


async def cmd_list() -> int:
    engine = get_engine()
    async with engine.connect() as conn:
        print(f"Database host: {engine.url.host}\n")
        print("ROOMS (telegram_chat_id | name | window_min | plan | scans_remaining)")
        rooms = await conn.execute(
            text(
                "SELECT id, telegram_chat_id, name, review_timeout_minutes, plan_type, "
                "scans_remaining FROM rooms ORDER BY created_at"
            )
        )
        for r in rooms:
            print(f"  {r.telegram_chat_id} | {r.name} | {r.review_timeout_minutes} | "
                  f"{r.plan_type} | {r.scans_remaining}")
            members = await conn.execute(
                text(
                    "SELECT u.display_name, u.telegram_user_id, m.role FROM room_members m "
                    "JOIN users u ON u.id = m.user_id WHERE m.room_id = :rid ORDER BY m.joined_at"
                ),
                {"rid": r.id},
            )
            for m in members:
                print(f"      - {m.display_name} ({m.telegram_user_id}) {m.role}")
        print("\nUSERS (telegram_user_id | display_name | username)")
        users = await conn.execute(
            text("SELECT telegram_user_id, display_name, username FROM users ORDER BY created_at")
        )
        for u in users:
            print(f"  {u.telegram_user_id} | {u.display_name} | {u.username}")
    return 0


async def cmd_seed(args: argparse.Namespace) -> int:
    engine = get_engine()
    people = [(args.rep, "ROOM_REP"), *((m, "MEMBER") for m in args.member)]
    if not args.yes:
        print(f"Would seed room {args.chat_id} on host {engine.url.host}. Re-run with --yes.")
        return 1

    async with engine.begin() as conn:
        print(f"Database host: {engine.url.host}")
        room_id = await conn.scalar(
            text("SELECT id FROM rooms WHERE telegram_chat_id = :c"), {"c": args.chat_id}
        )
        if room_id is None:
            room_id = await conn.scalar(
                text(
                    "INSERT INTO rooms (id, telegram_chat_id, name, plan_type, scans_remaining, "
                    "review_timeout_minutes, review_default_action) VALUES (gen_random_uuid(), "
                    ":c, :n, 'FREE', 10, :w, 'CONFIRM') RETURNING id"
                ),
                {"c": args.chat_id, "n": ROOM_NAME, "w": args.window or None},
            )
            print("Created room")
        else:
            await conn.execute(
                text(
                    "UPDATE rooms SET name = :n, plan_type = 'FREE', scans_remaining = 10, "
                    "review_timeout_minutes = :w, review_default_action = 'CONFIRM' WHERE id = :r"
                ),
                {"n": ROOM_NAME, "w": args.window or None, "r": room_id},
            )
            print("Updated room")

        if args.reset:
            p = {"r": room_id}
            await conn.execute(text("DELETE FROM ledger_entries WHERE room_id = :r"), p)
            await conn.execute(text("DELETE FROM payments WHERE room_id = :r"), p)
            n = await conn.execute(text("DELETE FROM expenses WHERE room_id = :r"), p)
            await conn.execute(
                text("DELETE FROM categories WHERE room_id = :r AND NOT is_default"), p
            )
            print(f"Reset: deleted {n.rowcount} expenses and all ledger/payment rows")

        for name in DEFAULT_CATEGORIES:
            await conn.execute(
                text(
                    "INSERT INTO categories (id, room_id, name, is_default, is_archived) "
                    "SELECT gen_random_uuid(), CAST(:r AS uuid), CAST(:n AS varchar), true, false "
                    "WHERE NOT EXISTS (SELECT 1 FROM categories "
                    "WHERE room_id = CAST(:r AS uuid) AND lower(name) = lower(CAST(:n AS varchar)))"
                ),
                {"r": room_id, "n": name},
            )
        await conn.execute(
            text("UPDATE categories SET is_archived = false WHERE room_id = :r AND is_default"),
            {"r": room_id},
        )

        # Demote everyone first so the one-Room-Rep unique index never trips.
        await conn.execute(
            text("UPDATE room_members SET role = 'MEMBER' WHERE room_id = :r"), {"r": room_id}
        )
        keep = []
        for (name, tg_id), role in people:
            user_id = await conn.scalar(
                text(
                    "INSERT INTO users (id, telegram_user_id, display_name) "
                    "VALUES (gen_random_uuid(), :t, :n) ON CONFLICT (telegram_user_id) "
                    "DO UPDATE SET display_name = EXCLUDED.display_name RETURNING id"
                ),
                {"t": tg_id, "n": name},
            )
            member_id = await conn.scalar(
                text(
                    "INSERT INTO room_members (id, room_id, user_id, role) "
                    "VALUES (gen_random_uuid(), :r, :u, :role) ON CONFLICT (room_id, user_id) "
                    "DO UPDATE SET role = EXCLUDED.role RETURNING id"
                ),
                {"r": room_id, "u": user_id, "role": role},
            )
            keep.append(member_id)
            has_bank = await conn.scalar(
                text("SELECT 1 FROM bank_accounts WHERE user_id = :u LIMIT 1"), {"u": user_id}
            )
            if not has_bank:
                bank_id = await conn.scalar(
                    text(
                        "INSERT INTO bank_accounts (id, user_id, bank_bin, account_number, "
                        "account_name) VALUES (gen_random_uuid(), :u, '970436', :a, :n) "
                        "RETURNING id"
                    ),
                    {"u": user_id, "a": f"00000{tg_id}"[-10:], "n": name.upper()},
                )
                await conn.execute(
                    text("UPDATE users SET default_bank_account_id = :b WHERE id = :u"),
                    {"b": bank_id, "u": user_id},
                )
            print(f"  {name} ({tg_id}) -> {role}")

        if args.reset:
            removed = await conn.execute(
                text(
                    "DELETE FROM room_members "
                    "WHERE room_id = :r AND NOT (id = ANY(CAST(:k AS uuid[])))"
                ),
                {"r": room_id, "k": keep},
            )
            if removed.rowcount:
                print(f"Removed {removed.rowcount} extra member(s)")
    print("Done.")
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show rooms, members and users")
    seed = sub.add_parser("seed", help="create or reset the R203 test room")
    seed.add_argument("--chat-id", type=int, required=True, help="Telegram group chat id")
    seed.add_argument("--rep", type=_person, required=True, help="Room Rep as Name:telegram_id")
    seed.add_argument("--member", type=_person, action="append", default=[],
                      help="member as Name:telegram_id (repeat)")
    seed.add_argument("--window", type=int, default=5,
                      help="auto-confirmation window in minutes (default 5; 0 = no window)")
    seed.add_argument("--reset", action="store_true",
                      help="delete the room's expenses, ledger rows, custom categories, "
                      "extra members")
    seed.add_argument("--yes", action="store_true", help="really write to the database")
    args = parser.parse_args()
    try:
        return await (cmd_list() if args.cmd == "list" else cmd_seed(args))
    finally:
        await dispose_engine()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
