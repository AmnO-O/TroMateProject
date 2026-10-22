# Telegram Bot Library Evaluation

**Project:** TroMate — Roommate Expense & Rent Reconciliation Bot
**Task:** Initialize the Mini App backend and select a Telegram bot library
**Owner:** Nguyễn Gia Hào
**Reviewer:** Cao Quảng Hưng
**Branch:** `feat/init-mini-app-backend`  
**Pull request:** [#5](https://github.com/AmnO-O/TroMateProject/pull/5) (draft; live E2E pending)  
**Status:** **Draft** — implementation and local verification complete; live Telegram E2E pending  
**Last updated:** 2026-10-22

> **Decision status:** aiogram 3.x is the provisional recommendation. The
> recommendation is based on code integration, library documentation, and local
> automated verification. It must be confirmed by the live E2E checklist in
> Section 7 before the spike is marked accepted.

---

## 1. Executive summary

The backend spike is implemented in `src/backend` as one FastAPI application with
three interchangeable bot adapters:

| `BOT_LIBRARY` | Library | Adapter |
|---|---|---|
| `ptb` | `python-telegram-bot` 22.8 | `app/bots/ptb_bot.py` |
| `aiogram` | `aiogram` 3.31.0 | `app/bots/aiogram_bot.py` |
| `telebot` | `pyTelegramBotAPI` 4.37.1 | `app/bots/telebot_bot.py` |

All three adapters implement the same `BotEngine` interface and expose:

- `/start`, `/balance`, `/app`, `/help`, and a dev-only `/slow`
- an inline **Refresh balances** callback
- a private-chat `web_app` button
- a group/supergroup direct-link button
- webhook handoff without blocking the FastAPI event loop

The FastAPI layer includes:

- `/health`
- `/webhook/telegram` with `X-Telegram-Bot-Api-Secret-Token` verification
- `/api/miniapp/session` with official Telegram `initData` validation
- `/api/miniapp/balance` with mock balances
- `/miniapp`, a diagnostic Mini App page

### Local verification result

| Check | Result |
|---|---|
| Automated tests | **41 passed** in the full `dev + all three libraries` environment |
| Lint | `ruff check .` — **All checks passed** |
| Local HTTP smoke (real Uvicorn TCP server, fake bot engine) | Health, Mini App page, webhook secret rejection, webhook acceptance, valid session, tampered session, balance, and missing-header balance all behaved as expected |
| Signed test-data generator | Valid generated `initData` accepted; `--tamper` produced `INVALID_SIGNATURE` |
| Synthetic update dispatch | All three adapters handled `/start` and produced an inline keyboard |
| Live Telegram E2E | **Not executed** — no real bot token, public HTTPS tunnel, or Telegram client was available in the implementation environment |

### Provisional recommendation

**aiogram 3.x** is the best fit for this FastAPI/webhook architecture. It has the
cleanest update handoff (`Dispatcher.feed_update`), typed update models, a
router/filter composition model, and an async-first design. `python-telegram-bot`
is a close second and is the fallback if the team values its broader built-in
feature set or already knows it. `pyTelegramBotAPI` is the easiest to bootstrap
but has the weakest fit for this architecture and several async API quirks.

---

## 2. Context and scope

### 2.1 Goal

Choose the Telegram bot library for TroMate's Mini App backend, prove that all
three candidates can be used behind the same FastAPI webhook endpoint, and
document the Telegram platform constraints that affect the architecture.

### 2.2 Timebox and operating assumptions

- 3 working days.
- One test bot, run sequentially with each library.
- One public HTTPS tunnel at a time.
- Cloudflare Quick Tunnel preferred; ngrok as fallback.
- Mock balances only; no database or ledger implementation in this spike.
- The losing adapters stay in the repository until this report is reviewed and
  accepted, then they can be removed.

### 2.3 Non-goals

- Production authentication/session storage.
- Full Mini App UI.
- Real expense, debt, OCR, or reminder features.
- Load testing or Telegram-scale throughput measurement.
- Final BotFather configuration for production.

---

## 3. Architecture

### 3.1 Request flow

```text
Telegram client
    │
    ├── Bot update ──► HTTPS tunnel ──► POST /webhook/telegram
    │                                      │
    │                                      ├─ verify secret header
    │                                      ├─ parse/enforce body limits
    │                                      └─ BotEngine.handle_update()
    │                                            ├─ PTB: Update.de_json → update_queue.put
    │                                            ├─ aiogram: Update.model_validate → feed_update
    │                                            └─ telebot: Update.de_json → process_new_updates
    │
    └── Mini App ───► GET /miniapp
                         │
                         ├─ Telegram.WebApp.initData
                         ├─ POST /api/miniapp/session  → HMAC validation
                         └─ GET  /api/miniapp/balance  → HMAC validation → mock data
```

The webhook route returns quickly. Handler work is queued or spawned as a tracked
background task. Long-running work therefore does not hold the Telegram webhook
request open.

### 3.2 Components

| Component | Responsibility |
|---|---|
| `app/main.py` | App factory, lifespan, route registration, Mini App file response |
| `app/api/webhook.py` | Secret check, content-type/size checks, update handoff |
| `app/api/mini_app.py` | Session and mock balance API |
| `app/core/init_data.py` | Security-critical Telegram `initData` validator |
| `app/bots/base.py` | `BotEngine` contract and `TaskTracker` |
| `app/bots/factory.py` | Lazy adapter selection from `BOT_LIBRARY` |
| `app/bots/common.py` | Shared bot text and direct-link formatting |
| `app/bots/*_bot.py` | Library-specific startup, handlers, and update decoding |
| `app/web/miniapp.html` | Diagnostic Mini App page |
| `app/core/config.py` | Typed environment settings and validation |
| `scripts/manage_webhook.py` | `set`, `info`, and `delete` webhook tooling |
| `scripts/make_test_init_data.py` | Dev-only signed `initData` generator |

### 3.3 `initData` security model

The validator follows Telegram's official method:

1. Parse the raw query string with duplicate-key detection.
2. Remove `hash`; build a data-check string from the remaining fields sorted by key.
3. Derive `secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)`.
4. Compute `HMAC_SHA256(key=secret_key, message=data_check_string)`.
5. Compare with `hmac.compare_digest`.
6. Parse `user`/`chat` JSON only after the signature passes.
7. Enforce `auth_date` freshness and reject values more than 60 seconds in the
   future.
8. Enforce an application-level maximum raw length (default 8192 characters).

Important detail: the newer `signature` field stays in the HMAC data-check
string. Only `hash` is excluded. This is covered by an automated test.

The webhook endpoint separately checks the
`X-Telegram-Bot-Api-Secret-Token` header with `secrets.compare_digest`.

### 3.4 Session model for the spike

`/api/miniapp/session` returns the validated user and launch context.
`/api/miniapp/balance` re-validates the raw `initData` on each call. This is
acceptable for a spike but not the production design. Production should exchange
`initData` for a short-lived server-issued session token and optionally store the
`query_id` to prevent replay.

---

## 4. Implementation and reproducibility

### 4.1 Verified environment

| Component | Version |
|---|---|
| Python | 3.12.10 |
| FastAPI | 0.159.1 |
| Uvicorn | 0.54.0 |
| Pydantic Settings | 2.16.1 |
| HTTPX | 0.28.1 |
| `python-telegram-bot` | 22.8 |
| `aiogram` | 3.31.0 |
| `pyTelegramBotAPI` | 4.37.1 |
| pytest | 9.1.1 |
| pytest-asyncio | 1.4.0 |
| ruff | 0.17.1 |

### 4.2 Setup

From `src/backend` in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ptb,aiogram,telebot]"
Copy-Item .env.example .env
```

Fill in `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, and the current
`PUBLIC_BASE_URL`. Then:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
python scripts/manage_webhook.py set --drop-pending
python scripts/manage_webhook.py info
```

Switch libraries by changing one line and restarting:

```dotenv
BOT_LIBRARY=aiogram
```

Use `drop_pending_updates=True` when switching so stale updates are not delivered
to the new adapter.

### 4.3 Configuration notes

- `.env` is ignored by Git; only `.env.example` is committed.
- `PUBLIC_BASE_URL` must be HTTPS outside the test environment.
- `AUTO_SET_WEBHOOK=true` requires `PUBLIC_BASE_URL`.
- The webhook secret is limited to 16–256 characters from `A-Za-z0-9_-`.
- `MINIAPP_INITDATA_MAX_AGE_SECONDS` defaults to 3600.
- `MINIAPP_MAX_BODY_BYTES` defaults to 1 MiB.

---

## 5. Library integration findings

### 5.1 `python-telegram-bot` 22.8

**Integration pattern**

```python
application = (
    Application.builder()
    .token(token)
    .updater(None)          # webhook mode: no long polling updater
    .build()
)
application.add_handler(CommandHandler("start", on_start))
await application.initialize()
await application.start()
...
update = Update.de_json(payload, application.bot)
await application.update_queue.put(update)
```

**Observations**

- `Application.initialize()` performs `getMe`; the adapter can read
  `application.bot.username` after initialization instead of adding another
  `getMe` call.
- `updater(None)` is required to avoid an internal long-polling updater.
- `Update.de_json` accepts a dict and binds the bot instance, so the update queue
  can process handlers correctly.
- `CommandHandler` validates `@bot_username` mentions against the bot identity,
  which is the correct group behavior. It relies on Telegram's `bot_command`
  message entity.
- The application lifecycle (`initialize`, `start`, `stop`, `shutdown`) is more
  explicit than the other libraries, but it also gives the application clear
  ownership.
- `MenuButtonWebApp`, `set_my_commands`, `set_webhook`, and `secret_token` are
  all available in the installed version.

### 5.2 `aiogram` 3.31.0

**Integration pattern**

```python
bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)
...
update = Update.model_validate(payload, context={"bot": bot})
await dp.feed_update(bot, update)
```

**Observations**

- `Dispatcher.feed_update` is a direct, typed webhook handoff. No updater object
  or polling loop is involved.
- `Update.model_validate(..., context={"bot": bot})` provides the bot context
  needed by handlers and filters.
- `Command` mentions call `bot.me()` to validate the mention. Startup warms the
  cache with `get_me`, so group `/command@bot` handling is cheap after startup.
- The router/filter model is clean and scales to more commands, middlewares, and
  FSM flows later.
- `DefaultBotProperties` centralizes parse mode and other defaults.
- `MenuButtonWebApp`, `BotCommand`, `set_webhook`, and `secret_token` are
  available in the installed version.

### 5.3 `pyTelegramBotAPI` 4.37.1

**Integration pattern**

```python
bot = AsyncTeleBot(token)
bot.register_message_handler(on_start, commands=["start"])
...
update = types.Update.de_json(json.dumps(payload))
await bot.process_new_updates([update])
```

**Observations and fixes found during the spike**

- `types.Update.de_json` expects a **JSON string**, not a dict. Passing the
  webhook payload directly raises; the adapter wraps it with `json.dumps`.
- The `commands` filter uses `util.extract_command`, which strips the `@mention`.
  Consequently `/balance@other_bot` would match unless the application adds its
  own guard. The adapter adds `_command_for_me`, which allows private commands
  and only the configured bot's username in groups.
- `AsyncTeleBot.close_session()` raises `AttributeError` if no API call has
  initialized the session. Shutdown catches this expected case.
- `reply_to`, `edit_message_text`, `answer_callback_query`, `set_my_commands`,
  `set_chat_menu_button`, and `set_webhook` all work with the installed version.
- The synchronous-style decorator API is easy to read, but the asynchronous
  wrapper feels bolted onto a library whose primary design is synchronous.
  It also has the least explicit lifecycle contract of the three.

### 5.4 Cross-library comparison of integration points

| Concern | PTB | aiogram | telebot |
|---|---|---|---|
| Webhook handoff | `Update.de_json` → `update_queue.put` | `Update.model_validate` → `feed_update` | `Update.de_json(json.dumps(...))` → `process_new_updates` |
| Explicit startup lifecycle | Yes (`initialize`/`start`) | Lightweight (`get_me` for identity) | Lightweight (`get_me`) |
| Group command mention handling | Built in | Built in (uses cached `bot.me()`) | **Needs app guard** |
| Mini App menu button | `MenuButtonWebApp` | `MenuButtonWebApp` | `MenuButtonWebApp` |
| Private `web_app` keyboard | Supported | Supported | Supported |
| Inline callback | `CallbackQueryHandler` | `router.callback_query` | `callback_query_handler` |
| Background task pattern | Internal update queue | Explicit `TaskTracker` | Explicit `TaskTracker` |
| Main async HTTP dependency | `httpx` | `aiohttp` | `aiohttp`/`requests` |
| Main integration risk | Lifecycle ceremony | API churn between major versions | Async/lifecycle quirks |

---

## 6. Verification

### 6.1 Automated tests

Command:

```powershell
cd src/backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Result:

```text
41 passed in 6.49s
All checks passed!
```

Test coverage:

| Area | What is covered |
|---|---|
| `initData` | Valid data, deterministic HMAC vector, tampered user, missing/malformed hash, expiry, future timestamps, missing/non-integer `auth_date`, duplicate keys, empty/oversized input, malformed query string, `signature` inclusion, wrong bot token, Unicode/`+` handling, invalid user payload, chat payload |
| Mini App API | `/health`, valid session, tampered session, empty session, missing body field, expired session, valid balance, missing header, invalid header, Mini App HTML |
| Webhook | Valid update, missing/wrong secret, wrong content type, malformed JSON, non-object JSON, oversized body, handler exception acknowledged |
| Adapters | Telebot update decoding and mention guard; PTB/aiogram/telebot synthetic `/start` dispatch; PTB group direct-link keyboard |

The adapter dispatch tests use synthetic Telegram update payloads and monkeypatch
the send methods, so they do not contact Telegram. They verify handler
registration, update decoding, and keyboard construction.

### 6.2 Local HTTP smoke test

A real Uvicorn server was started on `127.0.0.1:8765` with a fake `BotEngine`.
Requests were sent over TCP with HTTPX:

| Check | Result |
|---|---|
| `GET /health` | `200`, `library=ptb`, `bot_username=fake_bot` |
| `GET /miniapp` | `200 text/html`, page contains “TroMate Mini App” |
| `POST /webhook/telegram` with wrong secret | `403` |
| `POST /webhook/telegram` with correct secret | `200`, fake engine received `update_id=2` |
| `POST /api/miniapp/session` with valid signed data | `200`, user id `123456789` |
| `POST /api/miniapp/session` with tampered user | `401`, `INVALID_SIGNATURE` |
| `GET /api/miniapp/balance` with valid header | `200`, 3 mock balances |
| `GET /api/miniapp/balance` without header | `401`, `MISSING_INIT_DATA` |

This verifies the FastAPI app over an actual TCP socket, not only through ASGI
test transport.

### 6.3 Synthetic adapter dispatch

| Adapter | Private `/start` | Inline keyboard | Group direct link |
|---|---|---|---|
| PTB | Handled | `InlineKeyboardMarkup` | Tested; button URL is `https://t.me/<bot>?startapp=group` |
| aiogram | Handled | `InlineKeyboardMarkup` | Same helper/keyboard construction |
| telebot | Handled | `InlineKeyboardMarkup` | Same helper/keyboard construction |

### 6.4 What was not verified

The following require a real bot token, a public HTTPS tunnel, and a Telegram
client, none of which were available in the implementation environment:

- Actual `setWebhook`/`getWebhookInfo` against Telegram.
- `getMe`, command registration, and menu-button registration against Telegram.
- `/start` from a real Telegram client.
- Opening the Mini App from the inline `web_app` button.
- A real `initData` string from Telegram.
- Group direct-link launch and `chat_type`/`chat_instance`/`start_param` values.
- Group privacy behavior with a real bot.
- Callback-query edit behavior in Telegram clients.
- Telegram-side retry behavior and 429 handling.

These are **pending verification**, not failures. The code paths and API
signatures were checked locally, and the webhook/API behavior was verified with
synthetic payloads.

---

## 7. Live E2E checklist

### 7.1 Prerequisites

- Telegram test bot from BotFather.
- Bot token in `.env`; never in the report or Git.
- Webhook secret in `.env`.
- Public HTTPS tunnel (Cloudflare Quick Tunnel or ngrok).
- A Telegram account and a test group/supergroup.
- BotFather Main Mini App configured with `<PUBLIC_BASE_URL>/miniapp` for group
  direct-link testing.

### 7.2 Procedure

Run the same sequence for each `BOT_LIBRARY` value:

```powershell
cd src/backend
.\.venv\Scripts\Activate.ps1
# set BOT_LIBRARY, token, secret, PUBLIC_BASE_URL in .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
python scripts/manage_webhook.py set --drop-pending
python scripts/manage_webhook.py info
```

Then perform the checks below and record the evidence (timestamp, Telegram
client, bot username, screenshot/log reference).

### 7.3 Checks

| # | Check | Expected | Status |
|---|---|---|---|
| 1 | Bot starts and `getMe` succeeds | `/health` shows the bot username | Pending |
| 2 | `setWebhook` succeeds | `getWebhookInfo.url` matches the tunnel URL; `pending_update_count` is 0 | Pending |
| 3 | Private `/start` | Reply with commands and an **Open TroMate Mini App** `web_app` button | Pending |
| 4 | Open Mini App from private chat | Page loads; session API returns the real Telegram user | Pending |
| 5 | Mini App context | `chat_type=private`; user id/name match Telegram | Pending |
| 6 | Tampered `initData` | Session/balance API returns 401 `INVALID_SIGNATURE` | Pending |
| 7 | `/balance` | Mock balances render; refresh callback edits the message | Pending |
| 8 | Group direct link | `https://t.me/<bot>?startapp=group` opens the Mini App | Pending |
| 9 | Group context | `chat_type`, `chat_instance`, `start_param` are present | Pending |
| 10 | Group command with mention | `/balance@<bot>` responds; `/balance@other_bot` does not | Pending |
| 11 | Group privacy mode | Bot behavior matches the configured privacy/admin state | Pending |
| 12 | `/slow` | Handler finishes; webhook ACK is not blocked by the sleep | Pending |
| 13 | Restart and re-register | Webhook still points at the new tunnel/process; no stale update replay | Pending |
| 14 | Wrong webhook secret | Direct request returns 403 | Pending |
| 15 | Logs | No token, raw `initData`, or webhook secret is logged | Pending |
| 16 | 429 handling | Document observed behavior; custom retry/backoff is a production follow-up | Pending |

### 7.4 Per-library result table

| Library | Private E2E | Mini App E2E | Group E2E | Notes |
|---|---|---|---|---|
| PTB | Pending | Pending | Pending | |
| aiogram | Pending | Pending | Pending | |
| telebot | Pending | Pending | Pending | |

### 7.5 Acceptance rule

Do not delete the losing adapters or mark the spike accepted until the live E2E
checks have been run for all three libraries and this section has been updated
with evidence. If a library fails a check, record the failure and whether it is a
library limitation or an application issue.

---

## 8. Telegram platform limits and constraints

### 8.1 Webhook

| Constraint | Implication for TroMate |
|---|---|
| Webhooks require HTTPS | Local development needs a tunnel or a TLS-terminating proxy |
| Supported public ports are 443, 80, 88, and 8443 | Cloudflare/ngrok terminate TLS on 443 |
| One webhook per bot | `setWebhook` replaces the previous URL |
| `getUpdates` and webhooks are mutually exclusive | Do not run polling and webhook delivery for the same bot |
| `secret_token` is sent as `X-Telegram-Bot-Api-Secret-Token` | The FastAPI route verifies it before parsing |
| `max_connections` controls webhook concurrency | The spike uses 10; production should size it against the worker/queue capacity |
| `drop_pending_updates` discards queued updates | Use while switching libraries or resetting test state |
| Slow webhook responses can trigger retries | Handlers are queued/spawned; the route returns quickly |

### 8.2 Group privacy and permissions

- Group privacy mode is **ON by default**.
- With privacy on, the bot receives commands addressed to it and other limited
  updates; it does not receive all ordinary group messages.
- To read ordinary messages, disable privacy mode in BotFather and re-add the bot
  to the group.
- Making the bot an admin is another way to receive more group content, but it
  grants broader permissions and should be a deliberate product decision.
- The spike only needs commands, callback queries, and Mini App launches, so it
  does not require full message access.
- Group commands should be written as `/command@<bot>` in documentation and
  tests to avoid ambiguity.

### 8.3 Mini App launch constraints

| Launch path | `initData` | Notes |
|---|---|---|
| Private chat → inline `web_app` button | Present | Primary secure launch path |
| Private chat → bot menu button | Present | Set by each adapter |
| Group → `https://t.me/<bot>?startapp=group` | Present | Requires BotFather Main Mini App configuration |
| Group → inline `web_app` button | Unsupported | Telegram only supports `web_app` inline buttons in private chats |
| Reply-keyboard `web_app` button | Empty per Telegram docs | Do not use for authentication |
| Normal browser tab | Empty | The diagnostic page shows a warning; the API rejects |

Telegram caches Mini App pages. When iterating on a tunnel URL or HTML, add a
cache-busting query string such as `?v=2` to the BotFather Main Mini App URL.

### 8.4 `initData` lifecycle and replay

- `auth_date` must be checked; the spike defaults to a one-hour maximum age.
- `query_id` can be stored server-side to make a launch single-use. The spike
  does not implement a replay cache; production should.
- The signature must be checked before trusting `user`, `chat`, or `start_param`.
- Do not log raw `initData`; it contains user data and is a bearer-like artifact
  for the Mini App session.
- The bot token is the HMAC key. Rotating it invalidates all outstanding
  `initData`.

### 8.5 Rate limits

Telegram's Bot API FAQ gives approximate limits:

- about 1 message per second in a single chat;
- about 20 messages per minute to the same group;
- about 30 messages per second globally.

A 429 response includes `retry_after`. The spike does not add custom retry/backoff
logic; the libraries may expose some retry behavior, but production must handle
429 explicitly and avoid bursty notification loops.

### 8.6 Tunnel and hosting

- Cloudflare Quick Tunnel URLs are ephemeral and change on restart. They are fine
  for a spike but not for a stable bot deployment.
- Use a named Cloudflare tunnel or a stable HTTPS host for Sprint 3+.
- Keep the tunnel and FastAPI process alive during the E2E run; a dropped tunnel
  makes Telegram retries fail.
- The public URL is not a secret, but the bot token and webhook secret are.

---

## 9. Comparison and recommendation

### 9.1 Weighted decision matrix

Weights are a project decision aid, not a benchmark. Scores are 1–5.

| Criterion | Weight | PTB | aiogram | telebot |
|---|---:|---:|---:|---:|
| Async/FastAPI fit | 30% | 4 | 5 | 3 |
| Setup/integration effort | 20% | 4 | 4 | 5 |
| Docs/examples | 20% | 4 | 4 | 3 |
| Features | 20% | 5 | 5 | 3 |
| Ecosystem/maintenance | 10% | 5 | 5 | 4 |
| **Weighted total** | **100%** | **4.30** | **4.60** | **3.50** |

### 9.2 Why aiogram is the provisional choice

1. **Best webhook fit.** `Dispatcher.feed_update(bot, update)` is exactly the
   handoff a FastAPI route needs; no updater lifecycle or polling fallback.
2. **Typed and composable.** `Update.model_validate`, routers, filters, and
   middlewares provide a clean path from this spike to the real command set.
3. **Async-first.** The library is designed around asyncio rather than wrapping a
   synchronous core.
4. **Good feature ceiling.** FSM, middlewares, callback handling, and Mini App
   keyboard types are available without adding another framework.
5. **Competitive ecosystem.** Active project, current documentation, and broad
   usage.

### 9.3 Why PTB is a close second

PTB has the strongest built-in feature set and a very mature lifecycle. It is the
right choice if the team already knows it, or if `ConversationHandler`, `JobQueue`,
and its persistence/rate-limiter features will be used heavily. The main cost is
more lifecycle ceremony around FastAPI and an extra updater concept to disable.

### 9.4 Why telebot is not the default

telebot is the fastest to start, and its decorator style is approachable. For
this architecture, however:

- `Update.de_json` needs a JSON string, which is an easy integration trap.
- The command filter strips `@mention`, requiring an application-level guard.
- Async session lifecycle has rough edges (`close_session` before initialization).
- The async API is a wrapper around a synchronous-first library rather than an
  async-native design.
- Fewer built-in advanced features for the next stages.

It remains a reasonable fallback for a very small bot with a team already
comfortable with it.

### 9.5 Decision gate

The recommendation is **provisional** until:

- all three live E2E runs in Section 7 are complete;
- the team confirms the maintenance/ownership model;
- the production hosting and session strategy are agreed;
- the report is reviewed and accepted.

If aiogram passes E2E, remove the PTB and telebot adapters only after acceptance.
If aiogram has a blocking issue, PTB is the next candidate; telebot is the last
resort.

---

## 10. Risks and follow-ups

| Risk / follow-up | Impact | Action |
|---|---|---|
| Live E2E not yet run | Cannot claim Telegram-side acceptance | Run Section 7 with a real bot/tunnel/client; attach evidence |
| Jira key unavailable | Branch/PR naming is descriptive, not `feat/TM-<n>-...` | Rename branch/PR when the key is assigned |
| Ephemeral Quick Tunnel URL | Webhook breaks after tunnel restart | Use a named tunnel/stable host for Sprint 3+ |
| Re-validating `initData` per API call | Extra work and replay window | Exchange for a short-lived session token; cache `query_id` if single-use is required |
| No custom 429/backoff | Burst notifications may be throttled | Add a sender queue with `retry_after` handling |
| No auth-failure rate limit | Brute-force/abuse surface | Add per-IP/user throttling at the proxy or app |
| Logging discipline | Token/initData leakage | Keep secrets out of logs; review log statements before production |
| Telegram Mini App caching | Stale HTML after deploy | Use cache-busting URLs during iteration; plan asset versioning |
| Adapter code duplication | Maintenance cost after the spike | Keep one adapter after acceptance; archive the rest in the report history |
| Group privacy assumptions | Missing updates in real groups | Verify with a real group; document required BotFather settings |

---

## 11. References

Telegram official documentation:

- Mini Apps and `initData` validation:
  <https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app>
- Mini App direct links:
  <https://core.telegram.org/bots/webapps#direct-link-mini-apps>
- Bot API `setWebhook`:
  <https://core.telegram.org/bots/api#setwebhook>
- Bot features and privacy mode:
  <https://core.telegram.org/bots/features#privacy-mode>
- Bot API FAQ: rate limits:
  <https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this>

Library documentation:

- `python-telegram-bot`: <https://docs.python-telegram-bot.org/>
- PTB webhook example:
  <https://docs.python-telegram-bot.org/en/stable/examples.customwebhookbot.html>
- `aiogram`: <https://docs.aiogram.dev/>
- aiogram webhook guide:
  <https://docs.aiogram.dev/en/latest/dispatcher/webhook.html>
- `pyTelegramBotAPI`: <https://pytba.readthedocs.io/>
- `pyTelegramBotAPI` repository:
  <https://github.com/eternnoir/pyTelegramBotAPI>

Project artifacts:

- Backend README: [`../../src/backend/README.md`](../../src/backend/README.md)
- Validator: [`../../src/backend/app/core/init_data.py`](../../src/backend/app/core/init_data.py)
- Webhook route: [`../../src/backend/app/api/webhook.py`](../../src/backend/app/api/webhook.py)
- Adapters: [`../../src/backend/app/bots/`](../../src/backend/app/bots/)
- Tests: [`../../src/backend/tests/`](../../src/backend/tests/)

---

## Appendix A — Evidence log

### A.1 Commands and captured output

```text
$ cd src/backend
$ .\.venv\Scripts\python.exe -m pytest -q
41 passed in 6.49s

$ .\.venv\Scripts\python.exe -m ruff check .
All checks passed!
```

Local HTTP smoke (fake engine, Uvicorn on `127.0.0.1:8765`):

```text
health 200 {'status': 'ok', 'library': 'ptb', 'version': '0.1.0', 'bot_username': 'fake_bot', 'webhook_path': '/webhook/telegram'}
miniapp 200 text/html; charset=utf-8 True
webhook wrong secret 403
webhook 200 [{'update_id': 2}]
session 200 123456789
tampered session 401 INVALID_SIGNATURE
balance 200 3
balance without header 401 MISSING_INIT_DATA
```

### A.2 Repository changes in this spike

- `src/backend/pyproject.toml`
- `src/backend/.env.example`
- `src/backend/README.md`
- `src/backend/app/**`
- `src/backend/scripts/manage_webhook.py`
- `src/backend/scripts/make_test_init_data.py`
- `src/backend/tests/**`
- `.gitignore` (allow `.env.example`)
- Root `README.md` and `docs/README.md` document indexes
- `plan.md`

### A.3 Pending evidence

- Screenshots/logs from each library's live Telegram run.
- `getWebhookInfo` output for each library (redact any sensitive URL if needed).
- Real Mini App `initData` validation result (do not commit raw `initData`).
- Group launch context values.
- Callback-query edit result.
- 429/retry observation if a safe test is possible.

---

*This report is a living document. Update Sections 6, 7, and 9 after the live E2E
run and before the spike is marked accepted.*
