# TroMate Backend — Mini App Spike

FastAPI backend for the TroMate Telegram Mini App, plus interchangeable
`python-telegram-bot` / `aiogram` / `pyTelegramBotAPI` adapters used to choose
the bot library.

This is the Sprint 2 implementation of the **Initialize Mini App** task. It is
deliberately a spike: balances are mock data, there is no database, and the
Mini App page is a diagnostic shell rather than the final UI.

## What is included

- FastAPI app with `/health`, `/webhook/telegram`, `/miniapp`, and a small
  protected Mini App API.
- Official `initData` validation (HMAC-SHA256, `WebAppData`, `auth_date`
  freshness, duplicate-key rejection, `signature` included in the HMAC).
- Three bot adapters selected by `BOT_LIBRARY=ptb|aiogram|telebot`:
  - `/start`, `/balance`, `/app`, `/help`
  - inline “Refresh balances” callback
  - private-chat `web_app` button
  - group direct-link button
  - a dev-only `/slow` command for ACK/concurrency checks
- Webhook management script and a dev-only signed `initData` generator.
- Automated tests for the validator, webhook authentication, and API.

## Requirements

- Python 3.12+
- A Telegram test bot from [@BotFather](https://t.me/BotFather)
- An HTTPS tunnel for local webhook testing (Cloudflare Quick Tunnel or ngrok)
- A Telegram client for Mini App testing

## Setup

From this directory (`src/backend`), in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ptb,aiogram,telebot]"
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Without activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ptb,aiogram,telebot]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Configuration

```powershell
Copy-Item .env.example .env
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

`.env` is ignored by Git. Only `.env.example` is committed.

## Run locally

Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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

```powershell
python scripts/manage_webhook.py info
```

Manual webhook management:

```powershell
python scripts/manage_webhook.py set --drop-pending
python scripts/manage_webhook.py info
python scripts/manage_webhook.py delete --drop-pending
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

```powershell
pytest
ruff check .
```

The tests use a fake bot engine, so they do not need a real Telegram token or
network access.

Generate signed test data for manual API checks:

```powershell
python scripts/make_test_init_data.py
python scripts/make_test_init_data.py --auth-age-seconds 7200   # expired
python scripts/make_test_init_data.py --tamper                  # bad hash
```

> The generator uses the configured bot token. It is for local testing only;
> do not paste its output into public logs or reports.

Example PowerShell check:

```powershell
$init = python scripts/make_test_init_data.py
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/miniapp/session `
  -ContentType "application/json" `
  -Body (@{ init_data = $init } | ConvertTo-Json)
```

## Architecture

```text
app/
├── main.py                 # create_app, lifespan, routes
├── api/
│   ├── health.py
│   ├── webhook.py          # secret check + update handoff
│   └── mini_app.py         # session + mock balance API
├── bots/
│   ├── base.py             # BotEngine interface + TaskTracker
│   ├── factory.py          # lazy adapter selection
│   ├── common.py           # shared bot text
│   ├── ptb_bot.py
│   ├── aiogram_bot.py
│   └── telebot_bot.py
├── core/
│   ├── config.py
│   ├── init_data.py        # security-critical validator
│   ├── logging.py
│   └── sample_data.py
└── web/
    └── miniapp.html        # diagnostic Mini App
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
| `pytest` cannot import `app` | Run from `src/backend` with the venv active |
