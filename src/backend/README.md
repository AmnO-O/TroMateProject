# TroMate Backend — Mini App Spike

FastAPI backend for the TroMate Telegram Mini App, plus interchangeable
`python-telegram-bot` / `aiogram` / `pyTelegramBotAPI` adapters used to choose
the bot library.

It started as the Sprint 2 **Initialize Mini App** spike (mock balances,
diagnostic Mini App page). Sprint 4 adds the PostgreSQL (Neon) storage layer:
SQLAlchemy 2.0 async models, Alembic migrations, a Unit of Work, repositories
and a services layer (SCRUM-122). See [Database](#database).

## What is included

- FastAPI app with `/health`, `/webhook/telegram`, `/miniapp`, and a small
  protected Mini App API.
- Official `initData` validation (HMAC-SHA256, `WebAppData`, `auth_date`
  freshness, duplicate-key rejection, `signature` included in the HMAC).
- Three bot adapters selected by `BOT_LIBRARY=ptb|aiogram|telebot`:
  - `/start`, `/balance`, `/app`, `/help` (Vietnamese help text in `common.py`)
  - `/new [text]` (`AiogramEngine` — UC01 + UC03b expense logging in group chats)
  - inline “Refresh balances” callback and UC01 inline confirmation card (`[✓ Đồng ý]`, `[✕ Từ chối]`, `[✎ Chỉnh sửa]`)
  - private-chat `web_app` button
  - group direct-link button
  - a dev-only `/slow` command for ACK/concurrency checks
- UC01 natural-language extraction & split parsing (SCRUM-123):
  - `AIExtractionAdapter` (`gemini-3.5-flash-lite` via `GEMINI_API_KEY`) with automatic fallback to rule-based `vnd_parser.py`
  - `ExpenseParser` (VND slang normalization `k`/`nghìn`/`lít`/`tr`/`củ`, equal & `CUSTOM_AMOUNT` splits, §2.5.3 remainder absorption)
  - `ExpenseService` (single-`UnitOfWork` persistence with `RoomService.ensure_room_and_member_in_uow`, `BR02` manual approval for `Rent`/`Utilities`)
- Webhook management script and a dev-only signed `initData` generator.
- Automated tests for the validator, webhook authentication, API, UC01 parser/extractor, and `/new` bot flow.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (manages Python 3.12,
  the virtual environment and dependencies)
- A PostgreSQL database: a [Neon](https://neon.tech) project, or a local PostgreSQL 16
- A Telegram test bot from [@BotFather](https://t.me/BotFather)
- An HTTPS tunnel for local webhook testing (Cloudflare Quick Tunnel or ngrok)
- A Telegram client for Mini App testing

## Setup

From this directory (`src/backend`):

```bash
uv sync --all-extras   # creates .venv with Python 3.12, installs deps + bot libraries + dev tools
```

`uv sync` reads `pyproject.toml` and the committed `uv.lock`, so everyone gets the
same versions. Run any command inside the environment with `uv run`, no activation
needed (`uv run pytest`, `uv run alembic ...`, `uv run uvicorn ...`).

Managing dependencies:

```bash
uv add <package>          # runtime dependency (updates pyproject.toml and uv.lock)
uv add --dev <package>    # dev-only tool (dependency group "dev")
uv lock --upgrade-package <package>
```

Commit both `pyproject.toml` and `uv.lock` after changing dependencies.

## Configuration

```bash
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
```

Fill in:

| Variable | Meaning |
|---|---|
| `PUBLIC_BASE_URL` | Public HTTPS tunnel base URL, no trailing slash |
| `BOT_LIBRARY` | `ptb`, `aiogram`, or `telebot` |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | 16–256 characters from `A-Za-z0-9_-` |
| `AUTO_SET_WEBHOOK` | `true` to register the webhook on startup |
| `MINIAPP_INITDATA_MAX_AGE_SECONDS` | Accepted `initData` age; default 3600 |
| `DATABASE_URL` | Neon connection string (see [Database](#database)) |
| `GEMINI_API_KEY` | Google Gemini key for the AI Extraction Adapter; empty = VND parser fallback |

`.env` is ignored by Git. Only `.env.example` is committed.

## Run locally

Start the API:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Start a tunnel in a second terminal:

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://127.0.0.1:8000
```

Copy the printed `https://<random>.trycloudflare.com` into `PUBLIC_BASE_URL`,
restart the API if `AUTO_SET_WEBHOOK=true`, then verify:

```bash
uv run python scripts/manage_webhook.py info
```

Manual webhook management:

```bash
uv run python scripts/manage_webhook.py set --drop-pending
uv run python scripts/manage_webhook.py info
uv run python scripts/manage_webhook.py delete --drop-pending
```

## Switching bot libraries

Change one line in `.env` and restart:

```dotenv
BOT_LIBRARY=aiogram
```

The FastAPI routes and Mini App page stay the same. The active adapter sets its
own commands, menu button, and webhook. Use `drop_pending_updates=true` when
switching so stale updates are not delivered to the new engine.

## Mini App launch paths

| Launch path | `initData` | Notes |
|---|---|---|
| Private chat → inline `web_app` button | Present | Primary auth test |
| Private chat → menu button | Present | Set by the adapter |
| Group/supergroup → `https://t.me/<bot>?startapp=group` | Present | Includes `chat_type`, `chat_instance`, `start_param` |
| Group → inline `web_app` button | Unsupported | Telegram only supports `web_app` inline buttons in private chats |
| Reply-keyboard `web_app` button | Empty per Telegram docs | Do not use for auth |
| Browser tab | Empty | Diagnostic page shows a warning; API rejects |

For the group direct link, configure the bot's **Main Mini App** in BotFather
with the current tunnel URL plus `/miniapp`. Telegram caches Mini App pages;
use a cache-busting query string (for example `?v=2`) when iterating.

## API

### `GET /health`

```json
{
  "status": "ok",
  "library": "ptb",
  "version": "0.1.0",
  "bot_username": "tromate_spike_bot",
  "webhook_path": "/webhook/telegram"
}
```

### `POST /api/miniapp/session`

```json
{ "init_data": "<raw Telegram WebApp.initData>" }
```

Returns the validated user and launch context. Errors include a stable code:

- `INVALID_INIT_DATA` (400)
- `INVALID_SIGNATURE` (401)
- `EXPIRED_INIT_DATA` (401)
- `INIT_DATA_TOO_LARGE` (413)

### `GET /api/miniapp/balance`

Requires the raw `initData` in the `X-Telegram-Init-Data` header. Returns mock
balances for the spike. Production should exchange `initData` for a short-lived
session token instead of re-validating it on every request.

### `POST /webhook/telegram`

Requires `X-Telegram-Bot-Api-Secret-Token`. The route acknowledges quickly;
adapters enqueue or spawn handler work. A handler exception is logged and does
not crash the webhook process.

## Tests and lint

```bash
uv run --extra all pytest
uv run ruff check .
```

`aiogram` is an optional extra required for the UC01 bot tests (`tests/test_uc01_new_command.py`);
running `uv run pytest` without `--extra all` (or `--extra aiogram`) skips them.
The tests use a fake bot engine, so they do not need a real Telegram token or
network access. Database integration tests (`tests/db/`) are skipped unless
`TEST_DATABASE_URL` is set; see [Database tests](#database-tests).

Generate signed test data for manual API checks:

```bash
uv run python scripts/make_test_init_data.py
uv run python scripts/make_test_init_data.py --auth-age-seconds 7200   # expired
uv run python scripts/make_test_init_data.py --tamper                  # bad hash
```

> The generator uses the configured bot token. It is for local testing only;
> do not paste its output into public logs or reports.

Example PowerShell check:

```powershell
$init = uv run python scripts/make_test_init_data.py
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/miniapp/session `
  -ContentType "application/json" `
  -Body (@{ init_data = $init } | ConvertTo-Json)
```

## Architecture

Layered as in the SCRUM-116 component diagram (Figure 2): routers call services,
services call repositories (through a Unit of Work) and adapters, repositories
work through the ORM models.

```text
app/
├── main.py                 # create_app, lifespan (SELECT 1 DB warmup), routes
├── api/                    # Routers: FastAPI endpoints (health, webhook, Mini App)
├── bots/                   # Routers: Telegram bot adapters & UC01 confirmation card
│   ├── aiogram_bot.py      # /start, /new, /balance, /app, /help handlers
│   ├── expense_card.py     # HTML card renderer + [✓ Đồng ý]/[✕ Từ chối]/[✎ Chỉnh sửa]
│   └── interface.py        # Command specs, DTOs, callback builders, Protocols
├── adapters/               # External NLU & fallback extractors
│   ├── ai_extraction.py    # Google Gemini API adapter (gemini-3.5-flash-lite)
│   └── vnd_parser.py       # Rule-based Vietnamese VND extractor (fallback)
├── services/               # Business rules, one class per use-case area
│   ├── errors.py           # NotFound / PermissionDenied / Conflict (409) / Validation
│   ├── expense_parser.py   # VND slang normalization, equal/custom splits (§2.5.3)
│   ├── expense_service.py  # UC01 orchestration in one UnitOfWork + BR02 check
│   └── room_service.py     # rooms, members, default categories
├── repositories/           # Persistence only: queries and writes, never commit
│   ├── room_repository.py      # users, rooms, room_members, categories
│   ├── expense_repository.py   # expenses, expense_splits, expense_approvals, attachments
│   └── ledger_repository.py    # ledger_entries (append-only)
├── db/                     # ORM models and Unit of Work
│   ├── base.py             # DeclarativeBase, naming convention, UUID/created_at mixins
│   ├── enums.py            # statuses and other VARCHAR+CHECK enumerations
│   ├── session.py          # async engine (asyncpg), Neon URL handling, warmup_engine()
│   ├── unit_of_work.py     # one AsyncSession per use case, commit once
│   └── models/             # one *_model.py per table
├── core/                   # config, initData validator, logging
└── web/miniapp.html        # diagnostic Mini App
alembic/                    # migrations (alembic/versions/*.py)
```

| Layer | May call | Must not |
|---|---|---|
| Routers (`api/`, `bots/`) | Services | Run SQL or open sessions |
| Services | `UnitOfWork` repositories, adapters, other services | Import FastAPI/aiogram, touch `AsyncSession` |
| Repositories | ORM models, the session | Hold business rules, commit |

### UC01 Expense Logging & Parser (SCRUM-123)

- **Trigger (`/new [text]`):** Because Telegram Group Privacy Mode is enabled by default and to avoid unnecessary Gemini calls on casual chatter, `AiogramEngine` triggers UC01 on `/new <natural Vietnamese text>` in group chats.
- **Extraction (`AIExtractionAdapter`):** Uses Google Gemini (`gemini-3.5-flash-lite`) when `GEMINI_API_KEY` is configured and falls back automatically to `vnd_parser.py` when the key is missing, rate-limited, or unreachable.
- **Parsing (`ExpenseParser`):** Accepts `RawExtractionResult` directly, normalizes Vietnamese currency slang (`k`, `nghìn`, `lít`, `tr`, `củ rưỡi`, `150.000đ`), validates `share_amount > 0` (BR05), and applies the deterministic remainder rule (§2.5.3: remainder `Total % N` goes to the payer if participating, otherwise the first participant sorted by `display_name` A–Z).
- **Persistence (`ExpenseService`):** Resolves `Room` + sender membership in RAM (via eager-loaded `room.members`) and writes the `PENDING` expense + `ExpenseSplit` rows in **one `UnitOfWork`**. `Rent` and `Utilities` expenses set `review_deadline = None` for manual unanimous approval (BR02).
- **Startup DB Warmup:** `main.py` runs `warmup_engine()` (`SELECT 1`) on startup outside `test` env to avoid first-request Neon TLS cold-pool latency.

## Database

PostgreSQL on Neon, SQLAlchemy 2.0 (async) with `asyncpg`, Alembic migrations.

### Connect to Neon

1. In the Neon Console open the project, click **Connect**, and copy the
   connection string. For migrations prefer the **direct** endpoint (host without
   `-pooler`).
2. Put it in `.env` as is:

   ```dotenv
   DATABASE_URL=postgresql://<user>:<password>@<endpoint>.<region>.aws.neon.tech/neondb?sslmode=require
   ```

   `app/db/session.py` switches the scheme to `postgresql+asyncpg`, turns
   `sslmode=require` into asyncpg's `ssl=require` and drops `channel_binding`.
   Pooled (`-pooler`) hosts automatically get PgBouncer-safe settings.
3. Check the connection and apply the migrations:

   ```bash
   uv run python scripts/check_db.py
   uv run alembic upgrade head
   uv run python scripts/check_db.py   # now shows the revision
   ```

### Migrations

```bash
uv run alembic upgrade head                          # apply all migrations
uv run alembic downgrade -1                          # undo the last one
uv run alembic current                               # applied revision
uv run alembic revision --autogenerate -m "add x"    # after changing app/db/models
uv run alembic check                                 # fail if models and DB differ
uv run alembic upgrade head --sql                    # print SQL without running it
```

Always read an autogenerated revision before committing it: Alembic does not
detect CHECK-constraint or enum value changes, and cyclic foreign keys need
`op.create_foreign_key` after both tables exist (see the initial revision).
New revision files are formatted with ruff automatically.

### Unit of Work and repositories

```python
from app.db.unit_of_work import UnitOfWork

async with UnitOfWork() as uow:                      # one AsyncSession
    expense = await uow.expenses.get(expense_id, for_update=True)
    ok = await uow.expenses.update_if_version(
        expense.id, client_version,                  # optimistic lock
        expected_statuses=[ExpenseStatus.PENDING],
        status=ExpenseStatus.CONFIRMED, confirmed_at=now,
    )
    if not ok:
        raise ConflictError("Expense was changed by someone else")
    await uow.ledger.append_many(entries)
    await uow.commit()                               # status + ledger in one transaction
# leaving the block without commit() discards the work
```

- `Expense.version` is the optimistic-locking counter. Change an expense only
  through `ExpenseRepository.update_if_version`, which runs
  `UPDATE ... WHERE id = :id AND version = :v` and increments `version`; `False`
  means stale data (answer 409).
- `LedgerRepository` is append-only (no update/delete methods). Correct a balance
  with a compensating entry.
- Services take a `UnitOfWork` factory (`RoomService(uow_factory)`), so tests can
  pass one bound to a test database.

### Schema

The tables follow the SCRUM-117 ERD
([`docs/analysis-and-design/database-schema-erd.md`](../../docs/analysis-and-design/database-schema-erd.md)),
with the SCRUM-122 table names and corrections from the Use-case Specification v2.0:

| Change | Reason |
|---|---|
| `members` → `room_members`, `expense_shares` → `expense_splits`, `expense_votes` → `expense_approvals` | SCRUM-122 naming |
| Expense status `PENDING / DISPUTED / CONFIRMED / CANCELLED` (ERD had `REJECTED`) | BR01, BR04: a rejection disputes the expense; the room's `DECLINE` default action cancels it |
| `expenses.review_window_minutes`, `expenses.auto_resolved` | UC06 records that an expense was auto-resolved and which window applied |
| `expense_approvals.expense_version`, `reason_code`, `reason_note` | UC05-AF03 clears approvals of older versions; UC05-AF02 stores the rejection reason |
| `ledger_entries.effective_at` | Entries of an overdue expense are dated at its review deadline; `created_at` stays the write time |
| `expense_splits.share_amount > 0` (ERD `>= 0`) | BR05 |
| `categories.name` 2–30 chars, unique per room ignoring case; 7 default categories seeded | BR06 |
| `rooms.review_timeout_minutes IN (5, 15, 30, 60, 360, 720, 1440)` | BR03 |
| At most one `ROOM_REP` per room (partial unique index); the first member becomes Room Rep | BR09 |
| `webhook_state` singleton row seeded by the migration | Telegram `update_id` deduplication |

Amounts are whole VND in `BIGINT`. A `PENDING` expense with `review_deadline IS NULL`
needs manual approval (photo, meter and rent expenses, BR02).

### Database tests

`tests/db/` runs the migrations and exercises the repositories against a real
PostgreSQL. Point `TEST_DATABASE_URL` at a **disposable** database: each run drops
and recreates its `public` schema. A Neon branch or a local PostgreSQL works; the
suite refuses to run if it points at `DATABASE_URL`.

```bash
TEST_DATABASE_URL=postgresql://<user>:<password>@<host>/<test_db> uv run pytest tests/db
```

## Telegram limits to remember

- Webhooks require HTTPS; supported Telegram-side ports are 443, 80, 88, 8443.
- One webhook per bot; `getUpdates` and webhooks are mutually exclusive.
- Group privacy mode is ON by default. To read ordinary group messages, disable
  privacy and re-add the bot, or make the bot an admin.
- `web_app` inline buttons are private-chat only; use direct links in groups.
- `initData` is empty for keyboard-button/inline-mode launches.
- Rate limits: about 1 message/second per chat, 20 messages/minute per group,
  and about 30 messages/second globally. Handle 429 `retry_after`.

See the full evaluation report:
[`docs/analysis-and-design/telegram-bot-library-evaluation.md`](../../docs/analysis-and-design/telegram-bot-library-evaluation.md).

## Troubleshooting

| Symptom | Check |
|---|---|
| `ValidationError` on startup | `.env` copied and all required values set |
| `getMe` fails | Token is correct and not revoked |
| Webhook 403 from Telegram | `TELEGRAM_WEBHOOK_SECRET` matches the value passed to `setWebhook` |
| Mini App shows “Telegram context missing” | Open from the inline button/direct link, not a browser tab |
| Group Mini App link opens the bot chat | Configure BotFather Main Mini App with the current tunnel URL |
| Changes not visible | Telegram caches Mini App pages; add `?v=N` to the BotFather URL |
| `pytest` cannot import `app` | Run from `src/backend` with `uv run pytest` (after `uv sync --all-extras`) |
| `DatabaseNotConfiguredError` | `DATABASE_URL` is empty in `.env` |
| `connect() got an unexpected keyword argument 'sslmode'` | Use the URL through `app.db.session` (it rewrites `sslmode`); do not pass it to `create_async_engine` directly |
| `prepared statement "__asyncpg_stmt_..." already exists` | Pooled Neon host without `-pooler` in the name: use the direct endpoint |
| `alembic` connects to the wrong database | Alembic reads `DATABASE_URL`; override with `uv run alembic -x database_url=... upgrade head` |
