# Technical Spike — Mini App Backend and Telegram Bot Library Selection

**Spike ID:** TS-001 (provisional; no Jira key assigned)
**Version:** 1.0
**Status:** `In Progress` — live infrastructure verified; Telegram-client E2E and review pending

**Project:** TroMate
**Sprint / Iteration:** Sprint 2 — Elaboration / Mini App Backend
**Prepared by:** Pham Huu Nam (PHN)
**Reviewed by:** Cao Quảng Hưng (CQH) — pending
**Date created:** 25/10/2026
**Date completed:** Pending

---

## Revision History

| Date | Version | Description | Author |
|---|---|---|---|
| 25/10/2026 | 1.0 | Initial spike document; consolidated implementation and verification evidence | Pham Huu Nam |

---

## 1. Context & Motivation

TroMate needs a Telegram Mini App backend that can receive bot updates through a
webhook, validate Telegram `initData`, and serve the Mini App API. The team also
needs to choose one Telegram bot library before building the real command and
expense features.

Three candidate libraries were implemented behind the same FastAPI application:
`python-telegram-bot`, `aiogram`, and `pyTelegramBotAPI`. The spike checks their
webhook integration, async behavior, documentation, and limitations. It also
records the Telegram platform constraints that affect the design: group privacy
mode, bot permissions, webhook delivery, and rate limits.

**Related items:**

- Task description: [`src/description.md`](description.md)
- Epic / feature: Initialize Mini App — Sprint 2
- Technical report:
  [`docs/analysis-and-design/telegram-bot-library-evaluation.md`](../docs/analysis-and-design/telegram-bot-library-evaluation.md)
- Implementation: `src/backend/`
- Pull request: [#5](https://github.com/AmnO-O/TroMateProject/pull/5) (draft)
- Jira issue: not assigned; branch and PR use `feat/init-mini-app-backend`

---

## 2. Goal

**We need to learn / decide:**

1. Can one FastAPI application expose a Telegram webhook and the Mini App API
   while supporting `python-telegram-bot`, `aiogram`, and `pyTelegramBotAPI`
   through an interchangeable adapter?
2. Which library gives the best fit for an async FastAPI backend, considering
   setup effort, documentation, features, and limitations?
3. Does the backend validate Telegram Mini App `initData` correctly?
4. What Telegram webhook, privacy, permission, and rate limits must the
   implementation respect?
5. Is the implementation complete enough to move from the spike to the real
   Mini App feature work?

**Out of scope:**

- Production database, ledger, authentication/session store, and real balances.
- The final multi-screen Mini App UI.
- OCR, debt reminders, and expense workflows.
- Load testing and Telegram-scale throughput measurement.
- Final BotFather production configuration and a permanent domain.

---

## 3. Timebox

| Field | Value |
|---|---|
| **Max effort** | 3 working days |
| **Deadline** | 25/10/2026 |
| **Assigned to** | Pham Huu Nam (PHN) |

> [!IMPORTANT]
> The spike timebox has been reached. The implementation and local/live
> infrastructure checks are complete. The remaining work is the Telegram-client
> E2E pass and review; it should be completed before the spike is marked
> `Completed`.

---

## 4. Approach / Plan

1. [x] Read the official Telegram Bot API, webhook, privacy, permission, and
   rate-limit documentation.
2. [x] Set up the Python 3.12 virtual environment, dependencies, `.env`
   configuration, and FastAPI project structure.
3. [x] Implement `/health`, `/webhook/telegram`, `/miniapp`, and the protected
   Mini App session/balance API.
4. [x] Implement the official `initData` HMAC validation and reject invalid,
   expired, oversized, and tampered data.
5. [x] Implement interchangeable adapters for PTB, aiogram, and telebot behind
   one `BotEngine` contract.
6. [x] Add automated tests, lint checks, webhook tooling, and a signed test-data
   generator.
7. [x] Start Uvicorn and Cloudflare Quick Tunnel; register the webhook; verify
   public health, Mini App page, webhook authentication, and signed `initData`.
8. [ ] Run the real Telegram-client E2E checks for all three libraries:
   `/start`, `/balance`, inline refresh, Mini App launch, group launch, privacy,
   and permissions.
9. [x] Record setup steps, limits, comparison, tests, and recommendation in the
   technical report and this spike document.

**Proof-of-concept location:** `src/backend/` on branch
`feat/init-mini-app-backend`.

---

## 5. Acceptance Criteria

Legend: `☑` met, `◐` partially met, `☐` not met.

| # | Criterion | Target | Met? |
|---|---|---|---|
| AC1 | FastAPI backend runs locally and receives Telegram updates through the webhook | Webhook registered and real update delivered | ◐ Infrastructure verified; synthetic authenticated POST returns 200; real Telegram delivery still needs a client test |
| AC2 | Bot replies to `/start` and `/balance` and opens the Mini App from Telegram | Pass with a real Telegram account | ☐ Pending; requires the Telegram client |
| AC3 | Mini App `initData` validation works on the backend | Valid data accepted; tampered data rejected | ◐ Signed valid data returns 200; tampered data returns 401; real Telegram `initData` still pending |
| AC4 | Telegram limits documented | Privacy, permissions, webhook, rate limits | ☑ Report Section 8 |
| AC5 | Library comparison and recommendation documented | Comparison and one recommendation | ☑ Report Section 9; aiogram 3.x is provisional |
| AC6 | Automated quality checks pass | Tests and lint pass | ☑ 41 tests pass; `ruff` passes |
| AC7 | Code pushed to GitHub and reviewed | PR reviewed and accepted | ◐ Pushed to draft PR #5; review not complete |

### 5.1 Definition of Done check

From [`src/description.md`](description.md):

| Definition of Done item | Status | Evidence / blocker |
|---|---|---|
| FastAPI backend runs locally and receives Telegram updates through the webhook | ◐ Partial | App is running on `127.0.0.1:8000`; public webhook is registered; valid-secret synthetic POST returns 200. A real Telegram update has not yet been observed. |
| Bot replies to test commands and opens the Mini App from Telegram | ☐ Pending | `/start` and `/balance` handlers exist, but no Telegram-client interaction has been recorded. |
| Mini App `initData` check works on the backend | ◐ Partial | Signed valid data and tampered data were tested through the public tunnel. A real `Telegram.WebApp.initData` value is still needed. |
| Library comparison and recommendation are documented in a technical report linked to the task | ☑ Met | Technical report is written; Jira link is pending because no Jira key was assigned. |
| Code is pushed to GitHub, and the work is reviewed and accepted | ◐ Partial | Code is pushed and PR #5 is open; it is still a draft and not accepted. |

**Verdict: not fully done yet.** The backend, public tunnel, webhook, signed
`initData` checks, automated tests, and documentation are in place. Two
completion items remain: (1) a real Telegram-client E2E pass, and (2) final
review/acceptance. Do not mark the spike `Completed` until both are recorded.

---

## 6. Findings

### 6.1 Summary

The FastAPI backend is implemented and locally verified. All three adapters
share the same `BotEngine` interface and webhook route. Local verification
passes with **41 tests** and a clean `ruff` run. The public Cloudflare tunnel,
Telegram webhook, bot commands, menu button, Mini App page, webhook secret, and
signed `initData` flow were also checked live.

`aiogram 3.x` is the provisional library recommendation because
`Dispatcher.feed_update` gives the cleanest FastAPI handoff and the library is
async-native. `python-telegram-bot` is a close second and is the current live
adapter; `pyTelegramBotAPI` is the last option because of its JSON-string
decoding, mention handling, and async-wrapper quirks.

### 6.2 Detailed Results

Live infrastructure checks run on **25/10/2026** with
`BOT_LIBRARY=ptb`, `@tromate_dev_bot`, and the Cloudflare Quick Tunnel URL.

| Metric | Result | Target | Pass? |
|---|---|---|---|
| Local `GET /health` | `200`; `library=ptb`; `bot_username=tromate_dev_bot` | `200` | ☑ |
| Public `GET /health` through tunnel | `200` | `200` | ☑ |
| Public `GET /miniapp` | `200`; page contains “TroMate Mini App” and the Telegram Web App script | `200` | ☑ |
| `getMe` | `ok=true`; username `tromate_dev_bot` | Valid test bot | ☑ |
| `getMyCommands` | `ok=true`; 4 commands | Command menu registered | ☑ |
| `getChatMenuButton` | `web_app`; URL is `<PUBLIC_BASE_URL>/miniapp` | Mini App menu button | ☑ |
| `getWebhookInfo` | URL matches tunnel; `pending_update_count=0`; no `last_error_message`; `max_connections=10` | Webhook healthy | ☑ |
| Webhook with correct secret | `200`; `{"ok":true}` | `2XX` | ☑ |
| Webhook with wrong secret | `403`; `Invalid webhook secret` | `403` | ☑ |
| Session API with signed valid data | `200`; user payload and launch context returned | `200` | ☑ |
| Balance API with signed valid data | `200`; mock balances returned | `200` | ☑ |
| Session API with tampered data | `401`; `INVALID_SIGNATURE` | `401` | ☑ |
| Automated tests | `41 passed in 6.30s` | All pass | ☑ |
| Lint | `ruff check .` — `All checks passed` | Clean | ☑ |
| Synthetic `/start` dispatch for all three adapters | Handled; inline keyboard produced | All pass | ☑ |
| Real Telegram `/start` and Mini App launch | Not executed | Pass | ☐ |
| Real Telegram `initData` | Not captured | Valid | ☐ |
| Group direct link and privacy behavior | Not executed | Pass | ☐ |

The synthetic webhook request used only `{"update_id": ...}` to verify the public
route and secret check. It is **not** a substitute for a real Telegram update.
No raw `initData`, bot token, or webhook secret is recorded in this document.

### 6.3 Risks & Limitations Discovered

| Risk | Severity (H/M/L) | Mitigation |
|---|---|---|
| Cloudflare Quick Tunnel URL is ephemeral | H | Use a named tunnel or stable host for Sprint 3+; re-register the webhook after a tunnel restart |
| Real Telegram-client E2E is not recorded | H | Run the Section 7 checklist with a real account before accepting the spike |
| Real `initData` has not been validated | H | Open the Mini App from Telegram and record the session/balance result; do not log the raw value |
| Group privacy/permission behavior is unverified | M | Test in a dedicated group: regular member, privacy off, and administrator cases |
| Only PTB has been exercised against the live tunnel | M | Repeat the live sequence for aiogram and telebot before deleting any adapter |
| No production session/replay protection | M | Exchange `initData` for a short-lived server token; consider storing `query_id` |
| No custom 429/backoff | M | Add a sender queue that respects `retry_after` |
| No database or real ledger | L | Expected for this spike; out of scope |
| No Jira key | L | Rename branch/PR and link the report when the key is assigned |

### 6.4 Alternatives Considered

| Option | Pros | Cons | Decision |
|---|---|---|---|
| aiogram 3.x | Best `Dispatcher.feed_update` webhook handoff; typed updates; routers/filters; async-native | Another dependency; live E2E still pending | ✅ Provisional recommendation |
| python-telegram-bot 22.8 | Mature; strong feature set; current live adapter works | More lifecycle ceremony (`updater(None)`, initialize/start, queue) | ◐ Close second / fallback |
| pyTelegramBotAPI 4.37.1 | Fastest bootstrap; simple decorators | JSON-string update decoding; mention guard; async wrapper and close-session quirks | ❌ Not the default |

---

## 7. Recommendation

> [!NOTE]
> **⚠️ Proceed with conditions.**

The architecture is feasible, and the spike should proceed to implementation
with **aiogram 3.x** as the library, subject to the live Telegram-client E2E
pass. PTB is the fallback if aiogram fails a blocking check; telebot is the last
resort.

Conditions before acceptance:

1. Run the real Telegram E2E checklist for all three libraries.
2. Validate a real `Telegram.WebApp.initData` value through the public API.
3. Test group direct-link launch, privacy mode, and permission inspection.
4. Record the evidence in the report and this document.
5. Obtain reviewer approval before removing the losing adapters.

**Estimated implementation effort after the spike:** ~2 person-days for the
final E2E evidence, adapter cleanup, and session hardening.

---

## 8. Follow-up Actions

| # | Action | Owner | Due | Jira Issue |
|---|---|---|---|---|
| 1 | Run real Telegram-client E2E for PTB, aiogram, and telebot; record results | Pham Huu Nam | 26/10/2026 | `TBD` |
| 2 | Capture real `initData`, group launch context, privacy behavior, and `getChatMember` rights | Pham Huu Nam | 26/10/2026 | `TBD` |
| 3 | Review the technical report and PR #5 | Cao Quảng Hưng | 27/10/2026 | `TBD` |
| 4 | Update report Sections 6.4, 7.4, 9.6, and 11 with live evidence | Pham Huu Nam | After E2E | `TBD` |
| 5 | After acceptance, keep one adapter and remove the losing adapters | Pham Huu Nam | After review | `TBD` |
| 6 | Replace Quick Tunnel with a named tunnel/stable host | Pham Huu Nam | Sprint 3 | `TBD` |
| 7 | Create/link the Jira ticket and rename branch/PR with its key | Pham Huu Nam | When key assigned | `TBD` |

---

## 9. References

| Ref | Description | URL / Path |
|---|---|---|
| R1 | Task description and Definition of Done | [`src/description.md`](description.md) |
| R2 | Technical report: limits, comparison, tests, recommendation | [`docs/analysis-and-design/telegram-bot-library-evaluation.md`](../docs/analysis-and-design/telegram-bot-library-evaluation.md) |
| R3 | Backend setup and run guide | [`src/backend/README.md`](backend/README.md) |
| R4 | Implementation plan | [`plan.md`](../plan.md) |
| R5 | Pull request #5 | <https://github.com/AmnO-O/TroMateProject/pull/5> |
| R6 | Telegram `setWebhook` | <https://core.telegram.org/bots/api#setwebhook> |
| R7 | Telegram `getWebhookInfo` | <https://core.telegram.org/bots/api#getwebhookinfo> |
| R8 | Telegram webhook guide | <https://core.telegram.org/bots/webhooks> |
| R9 | Telegram privacy mode | <https://core.telegram.org/bots/features#privacy-mode> |
| R10 | Telegram bot FAQ: messages received and rate limits | <https://core.telegram.org/bots/faq> |
| R11 | Telegram `getChatMember` | <https://core.telegram.org/bots/api#getchatmember> |
| R12 | Telegram `ChatMemberAdministrator` | <https://core.telegram.org/bots/api#chatmemberadministrator> |
| R13 | PTB webhook example | <https://docs.python-telegram-bot.org/en/stable/examples.customwebhookbot.html> |
| R14 | aiogram webhook guide | <https://docs.aiogram.dev/en/latest/dispatcher/webhook.html> |
| R15 | pyTelegramBotAPI documentation | <https://pytba.readthedocs.io/> |
