# TroMate — Initialize Mini App: Implementation Plan

> **Task:** Initialize Mini App (Telegram bot backend + library evaluation)
> **Phase:** Elaboration / Sprint 2
> **Owner:** Technical Lead (Nguyễn Gia Hào) — confirm Jira assignee
> **Reviewer:** QA / Tester (Cao Quảng Hưng) — confirm Jira reviewer
> **Status:** Draft for approval
> **Last updated:** 2026-10-22
> **Jira ticket:** `TM-<n>` (fill in before starting)

---

## 0. One-page summary

### Goal

Create a working FastAPI backend for TroMate that:

1. Receives Telegram updates through a webhook.
2. Serves a minimal Mini App and a small API.
3. Validates Mini App `initData` using Telegram's official HMAC-SHA256 method.
4. Runs the same proof of concept on three candidate libraries:
   - `python-telegram-bot` (PTB)
   - `aiogram`
   - `pyTelegramBotAPI` (telebot)
5. Produces a technical report with setup steps, test results, Telegram limits, and a justified library recommendation.

### Delivery strategy

- **One backend skeleton, three interchangeable bot engines.** A single FastAPI app selects the active library with `BOT_LIBRARY=ptb|aiogram|telebot`. This keeps the webhook URL, Mini App page, `initData` validator, and API identical across candidates, so the comparison is fair.
- **One test bot, sequential runs.** All three candidates use the same bot token. Run one engine at a time, re-register the webhook with `drop_pending_updates=true`, and execute the same checklist. No need for three bots or three tunnels.
- **One HTTPS tunnel.** Cloudflare Quick Tunnel is the default; ngrok is the fallback. Telegram webhooks require public HTTPS.
- **Evidence-driven recommendation.** Score each library on a weighted rubric after the tests; do not pre-commit to a winner. Prior expectation: aiogram is likely to fit FastAPI best, PTB has the strongest docs/ecosystem, telebot is easiest for tiny bots. The tests decide.

### Definition of Done (high level)

- [ ] FastAPI runs locally and receives Telegram updates through the webhook.
- [ ] `/start` and `/balance` work; inline buttons work; the Mini App opens from Telegram.
- [ ] `initData` validation works and rejects tampered/expired data.
- [ ] Setup steps, test results, limits, comparison, and recommendation are in a technical report linked to the Jira task.
- [ ] Code is pushed to GitHub, reviewed, and accepted.

### Timebox

Three working days, with a buffer to the end of Sprint 2:

| Day | Focus |
|---|---|
| Day 1 | Scaffold, shared core, `initData` validation, Mini App page/API, PTB adapter |
| Day 2 | aiogram and telebot adapters, end-to-end tests, Telegram limits |
| Day 3 | Comparison, report, PR, review fixes |

If a candidate blocks for more than **3 hours**, document the blocker, score it accordingly, and move on. This is a spike, not a production rewrite.

---

## 1. Context and current state

### Repository

- Root: `C:\Users\LAPTOP_CUA_NAM\Documents\APCS\Software\project`
- GitHub: `AmnO-O/TroMateProject`
- Current state: documentation and planning only; `src/` contains only `.gitkeep`.
- Python 3.12.10, pip 25.3, Node 24.15 are installed. `uv`, `ngrok`, and `cloudflared` are not installed.
- `.gitignore` already ignores `.env`, `.env.*`, `venv/`, `.venv/`, `__pycache__/`, and `*.pyc`.

### Relevant project documents

- `README.md` — project overview, platform (Telegram Mini App), team roles.
- `docs/management/task-assignment.md` — workstream W1 (Bot & messaging), owner/reviewer convention.
- `docs/management/MVP_plan.md` — FastAPI/Node.js backend, Telegram-first, Mini App scope.
- `docs/requirements/vision.md` — product scope and constraints.
- `docs/README.md` — documentation register and naming conventions.
- `docs/analysis-and-design/ui-flows.md` — future Mini App screens (not built in this task).

### Assumptions

1. A dedicated **test bot** can be created in BotFather; its token is available locally.
2. The development machine can reach Telegram and create an outbound HTTPS tunnel.
3. At least one team member has Telegram on a phone for real Mini App testing.
4. No production database, Redis, NLP, OCR, or real ledger logic is needed for this task. Balances are mock data.
5. The Mini App UI for this task is a **single diagnostic page**, not the final TroMate UI. The real screens are a separate UI task.
6. The final library decision is reversible: bot-specific code is isolated behind a small adapter interface.

### Important platform facts to account for

- Telegram webhooks require **HTTPS**, a public URL, and one of the ports **443, 80, 88, or 8443** on Telegram's side. A tunnel exposing local port 8000 over HTTPS satisfies this.
- A bot can have **only one webhook** at a time; `getUpdates` and webhooks are mutually exclusive.
- `web_app` **inline keyboard buttons are available only in private chats**. In groups, the Mini App must be opened through a **direct link** (`https://t.me/<bot>?startapp=...`) or the bot menu button/Main Mini App. This is critical for TroMate, which is group-first.
- According to Telegram docs, `initData` is **empty** for Mini Apps launched from a **keyboard button** or inline mode. Therefore, the private-chat test must use an **inline `web_app` button**, not a reply-keyboard button.
- `initData` validation must include every field except `hash` in the data-check-string. The newer `signature` field **stays in** the HMAC data-check-string; it is only excluded for third-party Ed25519 validation.
- Group privacy mode is enabled by default. A bot receives only commands addressed to it, replies to it, inline messages via it, and service messages. To read ordinary group messages, either disable privacy mode and re-add the bot, or make the bot an admin.

---

## 2. Deliverables

| ID | Deliverable | Path / location | Acceptance |
|---|---|---|---|
| D1 | FastAPI backend scaffold | `src/backend/` | Starts with `uvicorn app.main:app`; `/health` returns 200 |
| D2 | Telegram webhook endpoint | `app/api/webhook.py` | Valid secret + update → 200; invalid secret → 403; malformed JSON → 400 |
| D3 | Mini App API | `app/api/mini_app.py` | `POST /api/miniapp/session` validates `initData`; `GET /api/miniapp/balance` returns mock data |
| D4 | `initData` validator | `app/core/init_data.py` | Official algorithm; positive and negative tests pass |
| D5 | Mini App diagnostic page | `app/web/miniapp.html` | Opens in Telegram; shows validated user and mock balance |
| D6 | Three bot engine PoCs | `app/bots/ptb_bot.py`, `aiogram_bot.py`, `telebot_bot.py` | `/start`, `/balance`, inline callback, Mini App launch work or failures are documented |
| D7 | Webhook/bot setup script | `scripts/manage_webhook.py`, `scripts/make_test_init_data.py` | Set/get/delete webhook; generate signed test `initData` |
| D8 | Automated tests | `tests/` | `pytest` and `ruff check` pass |
| D9 | Technical report | `docs/analysis-and-design/telegram-bot-library-evaluation.md` (proposed) | Setup, results, limits, comparison, recommendation, Jira link |
| D10 | Documentation index updates | `docs/README.md`, root `README.md` | Report is discoverable |
| D11 | GitHub PR | `feat/TM-<n>-init-mini-app` → `main` | Reviewed and approved |

---

## 3. Technical decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Installed; supported by all three candidates |
| Web framework | FastAPI + Uvicorn | Required by task; async, typed, easy test client |
| Settings | `pydantic-settings` + `.env` | Typed config, validation, `.env` support |
| Bot engines | Adapter per library, selected by `BOT_LIBRARY` | Fair comparison; production can keep only the winner |
| HTTP client | `httpx` | Used by PTB and tests; raw Bot API calls in scripts |
| Tests | `pytest`, `pytest-asyncio`, `httpx.ASGITransport` | Fast, no live Telegram needed for core tests |
| Lint/format | `ruff` | Single fast tool; no separate formatter config |
| Tunnel | Cloudflare Quick Tunnel | No account required; HTTPS; fallback to ngrok |
| Bot count | One test bot, sequential runs | Simpler; Mini App configuration stays stable |
| Data | Mock balances | Spike scope; no DB/Redis |
| Mini App auth | Validate raw `initData` on each API call | Stateless and easy to test; production should add a short-lived session token |

### Pinned versions (verified 2026-10-22)

| Package | Version |
|---|---|
| Python | 3.12.10 |
| FastAPI | 0.159.1 |
| Uvicorn | 0.54.0 |
| pydantic-settings | 2.16.1 |
| httpx | 0.28.1 |
| python-telegram-bot | 22.8 |
| aiogram | 3.31.0 |
| pyTelegramBotAPI | 4.37.1 |
| pytest / pytest-asyncio / ruff | latest stable at install time |

> Re-check versions before installing. If a transitive dependency conflict appears, use separate virtual environments per adapter and record it as a setup-friction finding.

---

## 4. Proposed repository structure

```text
src/backend/
├── pyproject.toml                 # project metadata, pinned deps, optional extras
├── .env.example                   # committed template; real .env is ignored
├── README.md                      # setup, run, switch library, test, troubleshoot
├── app/
│   ├── __init__.py
│   ├── main.py                    # create_app(), lifespan, router mounting
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py              # GET /health
│   │   ├── webhook.py             # POST /webhook/telegram
│   │   └── mini_app.py            # POST /api/miniapp/session, GET /api/miniapp/balance
│   ├── bots/
│   │   ├── __init__.py
│   │   ├── base.py                # BotEngine protocol/ABC + shared task tracking
│   │   ├── factory.py             # create_engine(settings)
│   │   ├── ptb_bot.py             # python-telegram-bot adapter + handlers
│   │   ├── aiogram_bot.py         # aiogram adapter + handlers
│   │   └── telebot_bot.py         # pyTelegramBotAPI adapter + handlers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings, env validation
│   │   ├── logging.py             # log configuration and redaction helpers
│   │   └── init_data.py           # official initData validation
│   └── web/
│       └── miniapp.html           # self-contained diagnostic Mini App
├── scripts/
│   ├── manage_webhook.py          # set / info / delete webhook via raw Bot API
│   └── make_test_init_data.py     # dev-only signed initData generator
└── tests/
    ├── conftest.py
    ├── test_init_data.py
    ├── test_miniapp_api.py
    └── test_webhook.py
```

### Why this structure

- `api/` contains framework-level HTTP concerns.
- `bots/` contains only library-specific integration and handlers; all expose the same `BotEngine` interface.
- `core/` is shared and library-agnostic, especially the security-critical `initData` validator.
- `web/miniapp.html` is deliberately a single file so there is no front-end build step.
- `scripts/` keeps operational tooling out of the request path.
- The losing adapters can be deleted in a follow-up PR after the decision, or kept behind optional extras for reproducibility.

---

## 5. Phase 0 — Preconditions and environment

### 5.1 Create the test bot

In Telegram, open **@BotFather**:

1. `/newbot` → name `TroMate Spike`, username e.g. `tromate_spike_bot`.
2. Save the token to a password manager; never commit it.
3. `/setcommands`:
   ```text
   start - Open TroMate and show the Mini App button
   balance - Show mock balances
   app - Open the TroMate Mini App
   help - Show available commands
   ```
4. Leave privacy mode at its default (ON) for the first group test. It will be changed later in the limits test.
5. Do **not** configure the Main Mini App yet; do it after the tunnel URL is known.

Create a test group:

- Add the bot and at least two test accounts.
- Prefer a **supergroup** to test realistic `chat_type=supergroup` behavior.
- Keep a second basic group if time permits, to compare `group` vs `supergroup`.

### 5.2 Create the Python environment

From the repository root, in PowerShell:

```powershell
cd src/backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ptb,aiogram,telebot]"
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Alternative without activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ptb,aiogram,telebot]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 5.3 Configure `.env`

```powershell
Copy-Item .env.example .env
```

`.env.example` (commit this; never commit `.env`):

```dotenv
APP_ENV=local
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000

# Public HTTPS base URL from the tunnel, no trailing slash
PUBLIC_BASE_URL=https://replace-me.trycloudflare.com

# ptb | aiogram | telebot
BOT_LIBRARY=ptb

TELEGRAM_BOT_TOKEN=123456:replace-me
TELEGRAM_WEBHOOK_SECRET=replace-with-32-plus-url-safe-chars
TELEGRAM_WEBHOOK_PATH=/webhook/telegram
AUTO_SET_WEBHOOK=true

MINIAPP_INITDATA_MAX_AGE_SECONDS=3600
MINIAPP_INITDATA_MAX_LENGTH=8192
```

Add an exception to `.gitignore` so the template is committed:

```gitignore
.env
.env.*
!.env.example
```

Config validation must fail fast if:

- `TELEGRAM_BOT_TOKEN` is missing or has no `:`.
- `TELEGRAM_WEBHOOK_SECRET` is missing, shorter than 16 characters, or contains characters outside `A-Za-z0-9_-`.
- `PUBLIC_BASE_URL` is not `https://` when `APP_ENV != test`.
- `BOT_LIBRARY` is not one of the three allowed values.

### 5.4 Start the HTTPS tunnel

Preferred (no account):

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://127.0.0.1:8000
```

Copy the printed `https://<random>.trycloudflare.com` into `PUBLIC_BASE_URL`.

Fallbacks:

- **ngrok** (requires account/authtoken): `ngrok http 8000`; a free static domain is preferable.
- **localtunnel** (Node): `npx localtunnel --port 8000`. Not recommended for webhooks because of the browser interstitial and unstable URLs.
- **Deploy to a free host** only if local tunneling is impossible; this changes the DoD from “runs locally”.

Verify the tunnel is reachable:

```powershell
Invoke-RestMethod "$env:PUBLIC_BASE_URL/health"
```

> The tunnel URL changes on restart. Re-run the webhook setup and update BotFather’s Mini App URL whenever it changes. Use a cache-busting query string (`?v=2`) if Telegram shows an old Mini App page.

### 5.5 Verify the bot token

Before writing code, confirm the token and get the username:

```powershell
$token = (Get-Content .env | Select-String '^TELEGRAM_BOT_TOKEN=').ToString().Split('=',2)[1]
Invoke-RestMethod "https://api.telegram.org/bot$token/getMe"
```

Expected: `ok: true` and the bot’s `username`.

---

## 6. Phase 1 — Backend scaffold and shared core

### 6.1 `pyproject.toml`

Use PEP 621 metadata, pinned dependencies, optional extras, and tool config:

```toml
[project]
name = "tromate-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.159.1",
  "uvicorn[standard]==0.54.0",
  "pydantic-settings==2.16.1",
  "httpx==0.28.1",
]

[project.optional-dependencies]
ptb = ["python-telegram-bot==22.8"]
aiogram = ["aiogram==3.31.0"]
telebot = ["pyTelegramBotAPI==4.37.1"]
dev = ["pytest", "pytest-asyncio", "ruff"]
all = [
  "python-telegram-bot==22.8",
  "aiogram==3.31.0",
  "pyTelegramBotAPI==4.37.1",
]
```

Add `[tool.ruff]`, `[tool.pytest.ini_options]`, and package discovery for `app*`.

### 6.2 App factory and lifespan

`app/main.py`:

```python
def create_app(settings: Settings | None = None, engine: BotEngine | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bot_engine = engine or create_engine(settings)
        await bot_engine.startup()
        app.state.bot_engine = bot_engine
        try:
            yield
        finally:
            await bot_engine.shutdown()

    app = FastAPI(title="TroMate Backend", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(webhook.router)
    app.include_router(mini_app.router, prefix="/api/miniapp")
    app.add_api_route("/miniapp", miniapp_page, methods=["GET"], include_in_schema=False)
    return app
```

Key rules:

- Never create the bot engine at import time. It must be created inside the lifespan so it uses the same event loop as FastAPI.
- `engine` injection exists for tests: pass a `FakeEngine` and avoid real libraries/network.
- On shutdown, close HTTP sessions, stop PTB’s application, cancel/wait for tracked background tasks with a timeout, and log cleanly.

### 6.3 `BotEngine` interface

`app/bots/base.py`:

```python
class BotEngine(ABC):
    name: str

    @abstractmethod
    async def startup(self) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...

    @abstractmethod
    async def handle_update(self, payload: dict[str, Any]) -> None: ...
```

Optional methods implemented by adapters:

- `set_webhook()`, `delete_webhook()`, `get_webhook_info()`
- `set_commands()`, `set_menu_button()`

The interface should stay small. Do not hide each library’s idioms behind a large abstraction before the evaluation; the point is to see the friction.

### 6.4 Logging

- Configure once at startup: timestamp, level, logger name, message.
- Log `update_id`, update type, chat id, chat type, and handler latency.
- Do **not** log message text by default (privacy), bot tokens, webhook secrets, or raw `initData`.
- Add a request/update correlation id for troubleshooting.
- Redact secrets if configuration is ever dumped.

### 6.5 Health endpoint

`GET /health`:

```json
{
  "status": "ok",
  "library": "ptb",
  "version": "0.1.0",
  "bot_username": "tromate_spike_bot",
  "webhook_path": "/webhook/telegram"
}
```

Implementation notes:

- `bot_username` is fetched once at startup via `getMe` and cached in the engine.
- Do not call Telegram on every health request.
- Do not return the token, secret, or full webhook URL if it might contain sensitive data.

### Phase 1 acceptance checks

- [ ] `pip install -e ".[dev,ptb,aiogram,telebot]"` succeeds.
- [ ] `uvicorn app.main:app --reload` starts without errors.
- [ ] `GET /health` returns 200 with the active library.
- [ ] `ruff check .` passes.
- [ ] `.env` is not tracked by Git; `.env.example` is tracked.

---

## 7. Phase 2 — `initData` validation (security-critical)

### 7.1 Official algorithm

Given raw `initData` (a URL-encoded query string):

1. Reject empty data or data longer than `MINIAPP_INITDATA_MAX_LENGTH`.
2. Parse with `urllib.parse.parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)`.
3. Reject duplicate keys. Ambiguous duplicates make the signed string unsafe.
4. Extract `hash`; require exactly 64 hexadecimal characters.
5. Build `data_check_string` from **all fields except `hash`**, sorted by key, as `key=value`, joined by `\n`.
   - Include `signature` if present. Do not exclude it for bot-token HMAC validation.
6. Compute:
   ```python
   secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
   expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
   ```
7. Compare with `hmac.compare_digest(expected, provided_hash.lower())`.
8. Validate `auth_date`:
   - Must be present and an integer.
   - Reject if more than 60 seconds in the future (clock skew).
   - Reject if older than `MINIAPP_INITDATA_MAX_AGE_SECONDS` (default 3600).
9. Parse `user` JSON if present; require an object with an integer `id`. Parse `chat` if present.
10. Return a typed result containing: `user`, `auth_date`, `query_id`, `chat`, `chat_type`, `chat_instance`, `start_param`, and the parsed fields.

### 7.2 Implementation notes

- Use decoded values from `parse_qsl` when building the data-check-string. Do not re-encode.
- `parse_qsl` turns `+` into a space; Telegram percent-encodes literal plus signs, so this is correct. Add a test with `%2B` and Vietnamese/Unicode text.
- Keep user IDs and chat IDs as Python `int`; they can exceed 32 bits. Do not cast to `int32`.
- Never use `initDataUnsafe` on the server. The front-end may use it only for non-security display, and even then prefer the validated response.
- `auth_date` is Unix seconds in UTC. Use `datetime.now(timezone.utc).timestamp()`.
- Replay is possible within the max-age window. Document that production should exchange `initData` for a short-lived session token or use one-time `query_id` handling for sensitive actions.
- Return generic error messages to clients; log details without secrets.

### 7.3 API contract

`POST /api/miniapp/session`

Request:

```json
{ "init_data": "auth_date=...&query_id=...&user=...&hash=..." }
```

Success `200`:

```json
{
  "ok": true,
  "user": {
    "id": 123456789,
    "first_name": "Nam",
    "last_name": null,
    "username": "nam",
    "language_code": "vi",
    "is_premium": false
  },
  "auth_date": 1760000000,
  "query_id": "AAH...",
  "chat_type": "supergroup",
  "chat_instance": "-123...",
  "start_param": "group"
}
```

Errors:

| Status | Code | When |
|---|---|---|
| 400 | `INVALID_INIT_DATA` | Malformed query string, duplicate key, missing hash, bad JSON |
| 401 | `INVALID_SIGNATURE` | Hash mismatch |
| 401 | `EXPIRED_INIT_DATA` | `auth_date` too old or too far in the future |
| 413 | `INIT_DATA_TOO_LARGE` | Exceeds configured max length |
| 422 | `VALIDATION_ERROR` | FastAPI body schema failure |

`GET /api/miniapp/balance`

Header: `X-Telegram-Init-Data: <raw initData>`

Success `200`:

```json
{
  "ok": true,
  "currency": "VND",
  "generated_at": "2026-10-22T10:00:00Z",
  "balances": [
    { "user_id": 1, "name": "Nam", "amount": 120000 },
    { "user_id": 2, "name": "Hào", "amount": -50000 },
    { "user_id": 3, "name": "Hưng", "amount": -70000 }
  ]
}
```

This endpoint validates `initData` on every call. It demonstrates the protected Mini App API without adding JWT/session infrastructure. The report must note the production upgrade path.

### 7.4 Test cases (`tests/test_init_data.py`)

| ID | Case | Expected |
|---|---|---|
| SEC-01 | Valid signed `initData` | Accepted; user and fields parsed |
| SEC-02 | Tampered `user` (change id/name), same hash | Rejected 401 |
| SEC-03 | Missing `hash` | Rejected 400 |
| SEC-04 | Invalid hash length/non-hex | Rejected 401/400 |
| SEC-05 | `auth_date` older than max age | Rejected 401 |
| SEC-06 | `auth_date` in the future beyond skew | Rejected 401 |
| SEC-07 | Missing `auth_date` | Rejected 401 |
| SEC-08 | Duplicate key | Rejected 400 |
| SEC-09 | Empty / oversized `init_data` | Rejected 400/413 |
| SEC-10 | `signature` field present and included in HMAC | Accepted |
| SEC-11 | Wrong bot token | Rejected 401 |
| SEC-12 | Unicode and `%2B` in user name | Parsed correctly; accepted |
| SEC-13 | Known deterministic test vector | Matches expected hash |

Generate test data with `scripts/make_test_init_data.py` (dev-only). The script signs arbitrary fields with the configured bot token and prints a query string. It must carry a warning that it is for local testing only.

### Phase 2 acceptance checks

- [ ] Valid real `initData` from Telegram validates.
- [ ] All SEC cases pass in `pytest` and at least three are re-run with `curl` against the live server.
- [ ] No raw `initData` or token appears in logs.

---

## 8. Phase 3 — Mini App diagnostic page and mock API

### 8.1 `web/miniapp.html`

Single self-contained page:

- Load `<script src="https://telegram.org/js/telegram-web-app.js"></script>` in `<head>` **before** any other script.
- Call `Telegram.WebApp.ready()` and `Telegram.WebApp.expand()`.
- Read `Telegram.WebApp.initData` (raw string only).
- If `initData` is empty:
  - Show a clear “Open this page from Telegram” warning.
  - Do not call the session API with empty data.
- If present:
  - `POST /api/miniapp/session` with `{init_data}`.
  - Show: validation status, user id/name/username, `chat_type`, `start_param`, and `auth_date`.
  - `GET /api/miniapp/balance` with `X-Telegram-Init-Data`; render the mock balances.
- Use Telegram theme CSS variables (`var(--tg-theme-bg-color)`, etc.) for a basic native look.
- Include a “Re-check” button and a compact raw-result `<pre>` block for debugging.
- No secrets, no bot token, no server-side trust of `initDataUnsafe`.

### 8.2 Launch paths

| Path | How | Expected `initData` |
|---|---|---|
| Private chat, inline `web_app` button | `/start` → tap button | Present; `user` available |
| Private chat, menu button | `setChatMenuButton` or BotFather menu button | Present |
| Group/supergroup, direct link | URL button to `https://t.me/<bot>?startapp=group` | Present; `chat_type`, `chat_instance`, `start_param` available |
| Group, inline `web_app` button | Attempt to send in group | Unsupported; must branch to URL button |
| Private chat, reply keyboard `web_app` button | Optional test | Official docs: empty; verify and document |
| Browser, direct URL | Open tunnel `/miniapp` | Empty; page shows warning; API rejects |

**Implementation rule:** in `/start` and `/app`, branch on `message.chat.type`:

- private → inline `web_app` button to `MINIAPP_URL`.
- group/supergroup → inline `url` button to `https://t.me/<bot_username>?startapp=group`, plus a short instruction.
- Never send a `web_app` inline button to a group without testing it; expect unsupported behavior.

### Phase 3 acceptance checks

- [ ] Page opens inside Telegram over HTTPS.
- [ ] Valid session shows the correct Telegram user.
- [ ] Mock balance renders.
- [ ] Browser launch shows the warning and does not crash.
- [ ] Group direct link includes `chat_type` and `start_param` in the response.

---

## 9. Phase 4 — Webhook endpoint and bot setup tooling

### 9.1 `POST /webhook/telegram`

Order of operations:

1. Read `X-Telegram-Bot-Api-Secret-Token`.
2. Compare with the configured secret using `secrets.compare_digest`; missing/wrong → `403`.
3. Check `Content-Type: application/json`; otherwise → `415`.
4. Read the body with a size cap (e.g., 1 MB); oversized → `413`.
5. Parse JSON; malformed → `400`.
6. Pass the payload to `request.app.state.bot_engine.handle_update(payload)`.
7. Return `{"ok": true}` with status 200.

Rules:

- **ACK quickly.** Telegram retries non-2xx responses and can mark the webhook unhealthy. Target < 1 second.
- PTB’s queue returns immediately; aiogram/telebot must use a tracked background task if a handler can be slow. Measure this in ASYNC tests.
- Never return a 500 for a handler exception after the update is accepted; log it and return 200 to avoid a retry storm. (If the update was not processed, a retry may be desirable; document the choice. For this spike, log and 200.)
- Do not log the raw body by default.
- Reject requests before parsing the body to reduce attack surface.

### 9.2 `scripts/manage_webhook.py`

Commands:

```powershell
python scripts/manage_webhook.py set --url "$env:PUBLIC_BASE_URL/webhook/telegram" --drop-pending
python scripts/manage_webhook.py info
python scripts/manage_webhook.py delete --drop-pending
```

Behavior:

- Reads `.env` via `Settings`.
- Calls `https://api.telegram.org/bot<token>/setWebhook` etc. with `httpx`.
- `set` passes `secret_token`, `max_connections=10` (local), and `allowed_updates=["message", "callback_query", "my_chat_member"]`.
- `info` prints URL, `pending_update_count`, `last_error_date`, `last_error_message`, `max_connections`, and `allowed_updates`.
- Never prints the bot token or webhook secret.
- Non-2xx Bot API responses are printed with `description` and exit non-zero.

### 9.3 Adapter startup responsibilities

Each adapter’s `startup()` should:

1. Create its bot/application object.
2. Call `getMe` and cache the username (fail fast on an invalid token).
3. Register the same logical handlers.
4. Set commands with `setMyCommands`.
5. Optionally set the private-chat menu button to the Mini App.
6. If `AUTO_SET_WEBHOOK=true`, set the webhook with the secret and `drop_pending_updates=true`.
7. Log the active library, bot username, webhook path, and `getWebhookInfo` summary.

Each `shutdown()` should:

- Stop the library cleanly.
- Close HTTP sessions (`bot.session.close()` in aiogram, `close_session()` in telebot, `application.stop()/shutdown()` in PTB).
- Wait for tracked background tasks with a short timeout and log leftovers.

### Phase 4 acceptance checks

- [ ] `set`, `info`, and `delete` work.
- [ ] `getWebhookInfo` shows the tunnel URL and 0 pending updates after processing.
- [ ] Wrong secret → 403; missing secret → 403; malformed JSON → 400; valid update → 200.
- [ ] Telegram retries are not observed for normal commands.

---

## 10. Phase 5 — Library adapters (the comparison core)

Each adapter must implement the same behavior, using the library’s idiomatic style. Do not force one abstraction over the handlers; the friction is part of the evaluation.

### 10.1 Common behavior contract

| Feature | Requirement |
|---|---|
| `/start` | Reply with library name and usage; private → inline `web_app` button; group → direct-link URL button |
| `/balance` | Reply with mock balances and an inline “Refresh” callback |
| `/app` | Send the Mini App button/link only |
| `/help` | List commands |
| Callback `balance:refresh` | Answer callback; edit the message with a fresh timestamp |
| `/balance@bot` in group | Must work; test library behavior |
| `/slow` (dev-only) | `await asyncio.sleep(2)`; used for concurrency/ACK tests |
| Optional `web_app_data` | Echo received data; documents keyboard-button flow |
| Optional `/boom` (dev-only) | Raise an exception; verify logging and 200 ACK behavior |

Mock balance text:

```text
Balances (mock, VND)
• Nam   +120,000
• Hào    -50,000
• Hưng   -70,000

Updated: 2026-10-22 10:00:00 UTC
```

### 10.2 A — python-telegram-bot 22.8

Dependency: `python-telegram-bot==22.8`

Core integration:

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

self.application = Application.builder().token(token).updater(None).build()
self.application.add_handler(CommandHandler("start", self.on_start))
self.application.add_handler(CommandHandler("balance", self.on_balance))
self.application.add_handler(CallbackQueryHandler(self.on_callback, pattern=r"^balance:refresh$"))

await self.application.initialize()
await self.application.start()
```

Webhook feed:

```python
update = Update.de_json(payload, self.application.bot)
await self.application.update_queue.put(update)
```

Notes to test and record:

- No official FastAPI example in the PTB docs; the Starlette custom-webhook example is directly adaptable. Record this as documentation friction.
- `Application` lifecycle must be inside FastAPI’s lifespan.
- The update queue decouples ACK from handler execution; measure ACK latency.
- PTB’s `concurrent_updates` setting controls whether handlers run one-at-a-time or concurrently. Test the default and, if needed, `concurrent_updates=True`.
- PTB has `AIORateLimiter`; note it as a built-in advantage for later.
- PTB’s `ConversationHandler` is a strong fit for TroMate’s PENDING/Agree/Reject/Edit state machine.

### 10.3 B — aiogram 3.31

Dependency: `aiogram==3.31.0`

Core integration:

```python
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

self.bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
self.dp = Dispatcher()
self.router = Router()
self.dp.include_router(self.router)

@self.router.message(CommandStart())
async def on_start(message: Message) -> None: ...

@self.router.message(Command("balance"))
async def on_balance(message: Message) -> None: ...

@self.router.callback_query(F.data == "balance:refresh")
async def on_refresh(callback: CallbackQuery) -> None: ...
```

Webhook feed:

```python
update = Update.model_validate(payload, context={"bot": self.bot})
await self.dp.feed_update(self.bot, update)
```

For fast ACK with slow handlers, wrap in a tracked background task:

```python
self._tasks.add(asyncio.create_task(self._feed(payload)))
self._tasks.discard(task)  # callback removes completed tasks
```

Notes to test and record:

- `Dispatcher.feed_update` is framework-agnostic, but aiogram’s documented webhook handler (`SimpleRequestHandler`) is aiohttp-specific. For FastAPI, manual feeding is needed. Record this friction.
- aiogram is async-native with typed Bot API models, routers, filters, middlewares, and built-in FSM. Strong fit for TroMate.
- `DefaultBotProperties` is the current way to set parse mode.
- `Command("balance")` behavior with `/balance@bot` must be tested.
- Close `bot.session` on shutdown.

### 10.4 C — pyTelegramBotAPI 4.37.1

Dependency: `pyTelegramBotAPI==4.37.1`

Core integration:

```python
from telebot.async_telebot import AsyncTeleBot
from telebot import types

self.bot = AsyncTeleBot(token)

@self.bot.message_handler(commands=["start"])
async def on_start(message: types.Message) -> None: ...

@self.bot.message_handler(commands=["balance"])
async def on_balance(message: types.Message) -> None: ...

@self.bot.callback_query_handler(func=lambda call: call.data == "balance:refresh")
async def on_refresh(call: types.CallbackQuery) -> None: ...
```

Webhook feed:

```python
update = types.Update.de_json(payload)
await self.bot.process_new_updates([update])
```

For fast ACK with slow handlers, use the same tracked background task pattern.

Notes to test and record:

- The package is sync-first; `AsyncTeleBot` is a separate async facade. Some examples/docs still assume `TeleBot`.
- `run_webhooks()` is a built-in FastAPI + uvicorn runner. It creates its own `fastapi.FastAPI()` app, validates the secret header, ACKs 200, and processes updates in a background task. This is convenient for a bot-only service but awkward when the same FastAPI app must also serve the Mini App API. Record this as a limitation/fit issue.
- `process_new_updates` processes updates sequentially within one call; concurrent webhook requests can still run concurrently. Measure.
- FSM exists via `state_storage`, but it is less structured than aiogram’s routers/FSM. Record.
- Close the aiohttp session on shutdown (`await bot.close_session()`).

### 10.5 Handler parity checklist

For each adapter, verify:

- [ ] `/start` in private chat returns the inline `web_app` button.
- [ ] Tapping it opens the Mini App; `initData` validates.
- [ ] `/start` in group returns the direct-link URL button.
- [ ] `/balance` returns mock balances.
- [ ] `/balance@bot` in group works.
- [ ] “Refresh” callback is answered and edits the message.
- [ ] `/app` opens the Mini App.
- [ ] `/help` lists commands.
- [ ] `/slow` does not block unrelated `/balance` (or the limitation is documented).
- [ ] Handler exceptions are logged and do not crash the process.
- [ ] Shutdown closes sessions/tasks cleanly.

### Phase 5 acceptance checks

- [ ] All three adapters start with the same `.env` except `BOT_LIBRARY`.
- [ ] All three pass the core E2E checklist, or every failure has a recorded cause.
- [ ] Adapter line counts and integration LOC are recorded for the report.
- [ ] No library-specific code leaks into `api/` or `core/`.

---

## 11. Phase 6 — Test execution

### 11.1 Test procedure per library

1. Start the tunnel; update `PUBLIC_BASE_URL` if it changed.
2. Set `BOT_LIBRARY=<lib>` in `.env`; restart uvicorn.
3. Confirm `/health` reports the correct library.
4. Run `manage_webhook.py set --drop-pending`; run `info`.
5. Run the E2E checklist in Telegram (private chat first, then group).
6. Run the security tests with `scripts/make_test_init_data.py` and `curl`/`Invoke-RestMethod`.
7. Run the Telegram limits checks for this library (privacy/permissions once per bot, not per library, but record any library-specific differences).
8. Capture evidence: screenshots, `getWebhookInfo` JSON, session response JSON, sanitized logs, latency numbers.
9. Stop the app; switch to the next library; repeat.
10. After all three, restore the recommended library and leave the bot in a clean state.

### 11.2 End-to-end test matrix

| ID | Scenario | Expected | Evidence |
|---|---|---|---|
| E2E-01 | `GET /health` | 200; active library name | JSON |
| E2E-02 | Valid webhook POST | 200; update processed | Log |
| E2E-03 | Missing/wrong webhook secret | 403; no processing | Response |
| E2E-04 | Malformed JSON | 400 | Response |
| E2E-05 | `/start` private | Reply + inline `web_app` button | Screenshot |
| E2E-06 | Tap Mini App button | Page opens; session validates; user shown | Screenshot + response |
| E2E-07 | `/balance` private | Mock balances + Refresh button | Screenshot |
| E2E-08 | Tap Refresh | Callback answered; message edited | Screenshot |
| E2E-09 | `/balance@bot` in group | Reply in group | Screenshot |
| E2E-10 | Group direct link | Mini App opens; `chat_type` + `start_param` in session | Screenshot + JSON |
| E2E-11 | Group inline `web_app` button | Document actual behavior (expected unsupported) | Log/screenshot |
| E2E-12 | Reply-keyboard `web_app` launch | Document `initData` behavior (expected empty) | Screenshot |
| E2E-13 | Browser `/miniapp` | Warning shown; API rejects empty initData | Screenshot |
| E2E-14 | `/slow` then `/balance` | Measure ACK latency and concurrency | Timing table |
| E2E-15 | `getWebhookInfo` after tests | URL correct; pending 0; no last error | JSON |
| E2E-16 | Restart app | Webhook re-set; no duplicate replies | Log |

### 11.3 Security test matrix

Run SEC-01…SEC-13 from section 7.4 for the shared validator (once), then re-run SEC-01, SEC-02, SEC-05 against each live adapter to prove the wiring is correct.

### 11.4 Telegram limits and permissions checklist

Mark each as **Tested** (empirical) or **Documented** (official source). Do not spam a real group to force rate limits; use official documentation plus one controlled check if safe.

| ID | Limit / behavior | Method | Result to record |
|---|---|---|---|
| LIM-01 | Privacy mode ON: plain group message not delivered | Test | Bot sees only `/start@bot`, `/balance@bot`, replies |
| LIM-02 | Bot as admin receives all group messages | Test | Promote bot; send plain message; confirm delivery |
| LIM-03 | Privacy mode OFF + re-add receives all messages | Test | Disable via BotFather; remove/re-add; confirm |
| LIM-04 | Bots cannot see messages from other bots | Document/optional test | Document |
| LIM-05 | Webhook requires HTTPS; HTTP URL rejected | Test | Bot API error |
| LIM-06 | Webhook ports 443/80/88/8443 | Document | Tunnel uses 443; local port is irrelevant |
| LIM-07 | `max_connections` 1–100, default 40 | Test | Set 10; reject 0/101 |
| LIM-08 | One webhook per bot; `getUpdates` conflict | Document/test | `getWebhookInfo` + error |
| LIM-09 | Updates retained ≤24h; non-2xx retried | Document | Retry behavior |
| LIM-10 | Rate limits: 1 msg/s per chat, 20/min per group, ~30/s global; 429 + `retry_after` | Document; optional controlled test | Record handling strategy |
| LIM-11 | Commands ≤32 chars, Latin/numbers/underscore; `setMyCommands` | Test | Command menu shows |
| LIM-12 | `web_app` inline buttons private only | Test | Group behavior documented; code branches |
| LIM-13 | `initData` empty for keyboard-button/inline-mode launches | Test | Documented in report |
| LIM-14 | Webhook redirects unsupported; CN must match; self-signed needs upload | Document | Note |
| LIM-15 | Group permissions: `can_delete_messages`, `can_pin_messages`, `can_invite_users` | Test as admin | Record required rights |
| LIM-16 | `chat_member` updates require admin + `allowed_updates` | Test/document | Note for membership tracking |
| LIM-17 | Mini App requires HTTPS; Telegram caches pages | Test | Cache-busting note |

### 11.5 Metrics to record per library

- Install time and dependency count (`pip install` wall time; `pip list` count).
- Lines of adapter code and lines to first successful webhook response.
- Webhook ACK latency for a normal command and for `/slow` (p50/p95 of 5 runs).
- Whether `/balance` is processed while `/slow` is running.
- Built-in secret validation: yes/no.
- Built-in background processing: yes/no; extra code required.
- Clean shutdown: yes/no; warnings/errors.
- Number of deviations from the common behavior contract.
- Any documentation gaps encountered.

### Phase 6 acceptance checks

- [ ] All E2E tests executed for all three adapters.
- [ ] All security tests pass for the shared validator and live endpoints.
- [ ] Limits checklist completed with Tested/Documented status and sources.
- [ ] Evidence is attached to Jira and indexed in the report.

---

## 12. Phase 7 — Comparison and recommendation

### 12.1 Scoring rubric

Score each criterion 1–5 (1 = poor, 5 = excellent), multiply by weight:

| Criterion | Weight | What “5” looks like |
|---|---:|---|
| Async/FastAPI fit | 30% | Native async; simple webhook feed; fast ACK; clean lifecycle; no blocking |
| Ease of setup and webhook integration | 20% | Few steps, clear errors, built-in secret handling, minimal glue |
| Documentation and examples | 20% | Official FastAPI/webhook/Mini App examples; current docs; clear API reference |
| Feature fit for TroMate | 20% | Routers, filters, FSM, middlewares, typed models, callbacks, Mini App support |
| Ecosystem, maintenance, limitations | 10% | Active releases, community, no blocking limitations for the MVP |

Tie-breaker: prefer the library with the simpler FastAPI integration and the stronger FSM/structure for the expense confirmation state machine.

### 12.2 Comparison table template

| Criterion | PTB 22.8 | aiogram 3.31 | telebot 4.37.1 |
|---|---|---|---|
| Setup time | | | |
| Install/dependency friction | | | |
| FastAPI integration approach | `update_queue.put` | `Dispatcher.feed_update` | `process_new_updates` |
| Lines of glue code | | | |
| Webhook secret validation | manual | manual (aiohttp handler built-in) | manual (built-in runner) |
| Fast ACK / background processing | built-in queue | manual task | manual task |
| Async model | native | native | async facade over sync-first API |
| Commands | `CommandHandler` | `Router` + `Command` | decorators |
| Inline callbacks | `CallbackQueryHandler` | `callback_query` + `F` | `callback_query_handler` |
| Mini App button | `WebAppInfo` | `WebAppInfo` | `WebAppInfo` |
| FSM / state machine | `ConversationHandler` | built-in FSM | state storage |
| Middlewares/filters | good | strong | basic |
| Typing/IDE support | good | excellent | fair |
| Docs for FastAPI | no official example | framework-agnostic `feed_update`; aiohttp handler official | built-in FastAPI runner |
| Limitations observed | | | |
| Weighted score | | | |

### 12.3 Recommendation requirements

The report must state:

- The recommended library and the weighted score.
- The three strongest reasons, tied to evidence (not just preference).
- The main trade-off accepted.
- What would cause the team to revisit the decision.
- Migration cost if the choice is wrong (the adapter layer keeps it modest).
- Impact on the TroMate architecture: expense confirmation state machine, group message ingestion, Mini App auth, future OCR/NLP handlers.

### 12.4 Report outline

`docs/analysis-and-design/telegram-bot-library-evaluation.md`:

1. Header: task link `TM-<n>`, owner, reviewer, date, status.
2. Executive summary and recommendation.
3. Context, scope, and non-goals.
4. Candidates and pinned versions.
5. Reproducible setup steps (environment, bot, tunnel, env vars).
6. Architecture: FastAPI + webhook + Mini App + `initData` validation.
7. PoC implementation per library (key code snippets, LOC, friction).
8. Test methodology, results, and evidence links.
9. `initData` security results.
10. Telegram limits, privacy mode, and bot permissions findings.
11. Comparison matrix and weighted score.
12. Recommendation and rationale.
13. Risks, limitations, and follow-ups.
14. References (official Telegram docs, library docs).
15. Appendix: commands, env vars, test data, evidence index.

### 12.5 Documentation index updates

- Add a row to `docs/README.md` → Document Register:
  - Name: Telegram Bot Library Evaluation
  - Discipline: Analysis & Design
  - Living copy: `analysis-and-design/telegram-bot-library-evaluation.md`
  - Owner: Technical Lead; Reviewer: QA/Tester; Phase: Elaboration.
- Add the report to the root `README.md` Documentation Index.
- Add a short `src/backend/README.md` with run instructions and a link to the report.
- Link the report and PR in the Jira ticket; attach evidence.

---

## 13. Git, review, and acceptance

### 13.1 Branch and commits

Branch from `main`:

```text
feat/TM-<n>-init-mini-app
```

Suggested commits:

```text
chore(backend): scaffold FastAPI project and configuration
feat(miniapp): add initData validation and session API
feat(bot): add python-telegram-bot adapter
feat(bot): add aiogram adapter
feat(bot): add pyTelegramBotAPI adapter
test(backend): cover initData, webhook auth, and Mini App API
docs: add Telegram bot library evaluation report
```

Keep `.env`, `.venv`, and evidence binaries out of Git. Commit only sanitized evidence and links.

### 13.2 PR checklist

- [ ] `ruff check .` and `pytest` pass.
- [ ] `.env.example` is committed; `.env` is not.
- [ ] Webhook secret is required and verified with constant-time comparison.
- [ ] `initData` validation follows the official algorithm and covers tamper/expiry/duplicate/signature.
- [ ] All three adapters implement the common behavior contract, or failures are documented.
- [ ] Mini App opens in private chat; group direct-link behavior is documented.
- [ ] No secrets, tokens, or raw `initData` in logs, screenshots, or the report.
- [ ] Report contains setup steps, results, limits, comparison, recommendation, and Jira link.
- [ ] README steps work on a clean machine.
- [ ] Jira ticket updated with report/PR links and evidence.

### 13.3 Reviewer verification steps

The reviewer should independently:

1. Check out the branch; create a fresh venv; install `.[dev,all]`.
2. Copy `.env.example` → `.env`; use their own test bot token.
3. Start uvicorn and a tunnel; run `manage_webhook.py set`.
4. Run `pytest` and `ruff check`.
5. Test `/start`, `/balance`, the inline callback, and the Mini App in private chat.
6. Test the group direct link and privacy-mode behavior.
7. Run SEC-02 and SEC-05 against the live API.
8. Read the report and confirm every claim is backed by evidence.
9. Approve or request changes on the PR.

### 13.4 DoD traceability

| DoD item | Evidence | Status |
|---|---|---|
| FastAPI runs locally and receives webhook updates | Uvicorn log + `getWebhookInfo` + E2E-02/E2E-15 | |
| Bot replies to `/start`, `/balance` | E2E-05/07 screenshots | |
| Mini App opens from Telegram | E2E-06/10 screenshots | |
| `initData` check works | SEC-01 + real Mini App session | |
| Library comparison and recommendation documented | Report section 11 + Jira link | |
| Code pushed, reviewed, accepted | PR URL + approval | |

---

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Tunnel URL changes or is blocked by the network | Webhook/Mini App stops working | Cloudflare Quick Tunnel; fallback ngrok; update `PUBLIC_BASE_URL` + BotFather; use mobile hotspot if needed |
| Telegram caches the Mini App page | Old page during tests | Cache-busting `?v=N` in the BotFather URL; restart tunnel |
| Group `web_app` inline button is unsupported | Group flow fails | Branch on chat type; use direct link/URL button in groups; document |
| Reply-keyboard Mini App has empty `initData` | Auth test fails | Use inline `web_app` button for private-chat auth; test keyboard path separately |
| Privacy mode prevents reading group messages | Core NLP use case blocked | Test privacy ON/OFF/admin; document required setup (disable privacy + re-add or admin) |
| Bot permissions missing | Cannot delete/pin/manage | Promote to admin with the required rights; document the minimum rights |
| Webhook secret/token leaked | Security incident | Dedicated test bot; `.env` ignored; rotate token if leaked; no secrets in logs/report |
| `initData` replay | Unauthorized reuse within max age | Short max age; production session token/one-time `query_id`; document |
| Dependency conflict among three libraries | Setup friction | Pinned versions; fallback to separate venvs per adapter; record it |
| PTB/aiogram/telebot lifecycle mismatch with FastAPI | Startup/shutdown errors | Create engines in lifespan; close sessions; test restart |
| Slow handlers cause webhook retries | Duplicate processing | Measure ACK; PTB queue; tracked background tasks for aiogram/telebot; production queue/worker |
| Rate limit 429 during testing | Interrupted tests | Use a small test group; avoid bursts; handle `retry_after`; document |
| Windows encoding/activation issues | Setup friction | `Set-ExecutionPolicy -Scope Process`; `chcp 65001` or Windows Terminal; use `.venv\Scripts\python.exe` directly |
| Time overrun on one library | Delays report | 3-hour timebox per candidate; document blockers and move on |

---

## 15. Out of scope / follow-ups

Out of scope for this task:

- Real ledger, database, Redis, authentication/JWT, NLP, OCR, debt simplification, VietQR.
- Final Mini App UI/screens (separate W6 task).
- Production deployment, CI/CD, observability, load testing.
- Zalo integration.
- Full Telegram Bot API coverage.

Recommended follow-ups after acceptance:

1. Delete the losing adapters (or keep them behind optional extras) and remove their dependencies from the production install.
2. Replace raw `initData`-per-request auth with a short-lived signed session token.
3. Add update-id deduplication (Redis/DB) and a background task queue for slow OCR/NLP work.
4. Add structured logging/metrics and alerting for webhook errors and `pending_update_count`.
5. Add CI (ruff + pytest) on pull requests.
6. Design the group-to-Mini-App binding using a signed `startapp` token and `chat_instance`/group id mapping.
7. Document the required BotFather settings (privacy mode, Main Mini App, commands, menu button) in the deployment guide.

---

## 16. Decisions needed before implementation

| # | Decision | Proposed default | Why it matters |
|---|---|---|---|
| 1 | Report location | `docs/analysis-and-design/telegram-bot-library-evaluation.md` | Matches the design/decision nature; `docs/test/` is for test plans/results |
| 2 | Tunnel | Cloudflare Quick Tunnel | No account; fallback ngrok if blocked |
| 3 | Losing adapters | Keep until the report is accepted, then remove in a follow-up PR | Evidence vs production leanness |
| 4 | Test bot | One dedicated bot, sequential runs | Fair comparison; stable Mini App config |
| 5 | Jira owner/reviewer | Technical Lead / QA-Tester per task assignment | Confirms review path |
| 6 | Timebox | 3 working days | Keeps the spike inside Sprint 2 |

---

## 17. Immediate next actions (in order)

1. Confirm the six decisions above and the Jira ticket key.
2. Create the test bot in BotFather and the test group.
3. Create the branch `feat/TM-<n>-init-mini-app`.
4. Scaffold `src/backend` and commit the first working `/health`.
5. Implement and test `initData` validation before any bot library code.
6. Add the PTB adapter and complete the first end-to-end webhook + Mini App run.
7. Repeat for aiogram and telebot.
8. Run the limits/permissions tests once, then the per-library E2E tests.
9. Write the report, update the docs index, open the PR, and request review.
10. Attach evidence to Jira and link the report/PR; move the ticket to In Review.

---

*End of plan.*
