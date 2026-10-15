# TroMate — Task Assignment Plan

*Elements of Software Engineering — 24A01 · Group 06 · PA1 · supports SDP §3.2 and §4.2.3*

> ⚠️ **Proposal — confirm with the team.** Roles below are a starting point based on team size. Swap owners if a member has a stronger skill in another area (e.g. who is stronger in backend vs UI). Every task lists an **Owner** and a **Reviewer**.

## How we divide work

1. **Vertical slices, not layers.** Each feature has one owner who carries it end-to-end (data → logic → UI → test), with a reviewer.
2. **One owner + one reviewer per task.** Nothing is "done" without a second pair of eyes.
3. **Pair on risk.** NLP and OCR are the least predictable, so two members co-own them.
4. **Shared testing.** A QA lead owns the test plan; acceptance testing is everyone's job.
5. **Jira is the source of truth.** Every task is a ticket with an assignee, sprint, and status (see board setup below).

## Members & roles

| Member (Name, ID) | Primary role | Also |
|---|---|---|
| Nguyễn Gia Hào (24125008) | Project Manager · Backend | Ledger service, debt algorithm, coordination |
| Cao Quảng Hưng (24125010) | Backend · **AI (NLP & OCR)** | Telegram bot integration |
| Trịnh Võ Nam Kiệt (24125013) | Frontend — Mini App | Core screens, settlement UI |
| Phạm Hữu Nam (24125015) | Frontend · **UI/UX** | Design system, report/review screens |
| Huỳnh Chí Tôn (24125020) | **QA / Testing** · Documentation | Test plan, weekly reports, PA docs |

## Workstreams

| WS | Workstream | Lead | Support |
|---|---|---|---|
| W1 | Bot & messaging (Telegram) | Hưng | Hào |
| W2 | NLP quick split | Hưng | Hào |
| W3 | OCR (rent bill & meters) | Hưng | Hào |
| W4 | Ledger service & data model | Hào | Hưng |
| W5 | Debt simplification & settlement (VietQR) | Hào | Nam Kiệt |
| W6 | Mini App UI (screens) | Nam Kiệt | Nam |
| W7 | UX / design system | Nam | Nam Kiệt |
| W8 | Quality (test plan, test cases, acceptance) | Tôn | All |
| W9 | Documentation (SDP, vision, reports, PA) | Tôn / Hào | All |

---

## Sprint-by-sprint allocation

### Sprint 1 — Inception

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T1 | Problem validation & user research summary | Hào | All | W9 |
| T2 | Project plan (SDP) | Hào | All | W9 |
| T3 | Vision document | Nam | Tôn | W9 |
| T4 | UI sketches (3–6 screens) | Nam Kiệt | Nam | W6/W7 |
| T5 | Weekly reports 1 & 2 | Tôn | Hào | W9 |
| T6 | Tools setup (Jira, GitHub) & access | Hào | All | W9 |

### Sprint 2 — Elaboration

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T7 | Use-case model & specifications | Nam | Hào | W9 |
| T8 | Software architecture document (draft) | Hưng | Hào | W4 |
| T9 | NLP quick-split spike (msg → entry) | Hưng | Hào | W2 |
| T10 | OCR rent-bill spike (extract fields) | Hưng | Hào | W3 |
| T11 | Vision document — detailed update | Nam | Tôn | W9 |
| T12 | Weekly reports | Tôn | Hào | W9 |

### Sprint 3 — Elaboration

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T13 | Finalize architecture (SAD v1) | Hưng | Hào | W4 |
| T14 | UI prototype (clickable) | Nam Kiệt | Nam | W6/W7 |
| T15 | Debt-simplification algorithm spike | Hào | Hưng | W5 |
| T16 | Test plan & test cases | Tôn | Hào | W8 |
| T17 | Revised SDP + weekly reports | Hào | Tôn | W9 |

### Sprint 4 — Construction

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T18 | Telegram bot integration | Hưng | Hào | W1 |
| T19 | NLP quick-split implementation | Hưng | Hào | W2 |
| T20 | Ledger service + data model | Hào | Hưng | W4 |
| T21 | OCR bill/meter parsing implementation | Hưng | Hào | W3 |
| T22 | Add Expense screen (S3) | Nam Kiệt | Nam | W6 |
| T23 | Dashboard screen (S2) | Nam Kiệt | Nam | W6 |
| T24 | Rent Bill Review screen (S4) | Nam | Nam Kiệt | W6 |
| T25 | Ledger/History screen (S7) | Nam | Nam Kiệt | W6 |
| T26 | Debt simplification implementation | Hào | Hưng | W5 |
| T27 | Integration testing → **Build 2** | Tôn | All | W8 |

### Sprint 5 — Construction

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T28 | Settlement / VietQR implementation | Hào | Nam Kiệt | W5 |
| T29 | Settlement screen, 3 states (S5) | Nam Kiệt | Nam | W6 |
| T30 | Monthly Report screen + charts (S6) | Nam | Nam Kiệt | W6 |
| T31 | Report data jobs / analytics | Hào | Hưng | W5 |
| T32 | Acceptance testing + bug fixing | Tôn | All | W8 |
| T33 | User guide & final docs | Tôn | Hào | W9 |
| T34 | Final release → **Build 3** + presentation | All | — | — |

---

## Jira board setup

- **Type:** Scrum board, 5 sprints × 2 weeks.
- **Columns:** `Backlog → To Do → In Progress → In Review → Done`.
- **Ticket fields:** Assignee, Sprint, Story points (1/2/3/5/8), Workstream label (`W1…W9`).
- **Ticket naming:** `TM-<n> — <screen/feature>: <task>` (e.g. `TM-22 — Add Expense: editable preview before save`).
- **Definition of Done:** code reviewed · tests pass · UI matches the flow in `flow.md` · reviewer approved.

## Weekly rhythm

- **Mon:** pull tasks for the week from the board; confirm owners.
- **Daily/as-needed:** quick chat check-in (Facebook Messenger).
- **Weekly:** 1 status report (Tôn) + board grooming (Hào).
