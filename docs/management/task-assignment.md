# TroMate — Task Assignment Plan

*Elements of Software Engineering — 24A01 · Group 06 · PA1 · supports SDP §3.2 and §4.2.3*

> Every task lists an **Owner** and a **Reviewer**. The Jira board is the source of truth for status; this document is the planning baseline and follows the team's agreed Scrum roles.

## How we divide work

1. **Vertical slices, not layers.** Each feature has one owner who carries it end-to-end (data → logic → UI → test), with a reviewer.
2. **One owner + one reviewer per task.** Nothing is "done" without a second pair of eyes.
3. **Pair on risk.** NLP and OCR are the least predictable, so the Technical Lead and the QA/Tester co-own them.
4. **Shared testing.** The QA/Tester owns the test plan; acceptance testing is everyone's job.
5. **Jira is the source of truth.** Every task is a ticket with an assignee, sprint, and status (see board setup below).

## Members & roles

| Member (Name, ID) | Primary role | Focus |
|---|---|---|
| Nguyễn Gia Hào (24125008) | **Technical Lead** | Architecture, ledger service, debt algorithm |
| Cao Quảng Hưng (24125010) | **QA / Tester** | Test plan, test cases, defect reporting |
| Trịnh Võ Nam Kiệt (24125013) | **Scrum Master / Project Lead** | Process, Jira board, plans, coordination |
| Phạm Hữu Nam (24125015) | **UI/UX Designer** | User flows, wireframes, design system, screens |
| Huỳnh Chí Tôn (24125020) | **Product Owner / Business Analyst** | Requirements, user stories, acceptance criteria |

## Workstreams

| WS | Workstream | Lead | Support |
|---|---|---|---|
| W1 | Bot & messaging (Telegram) | Hào | Hưng |
| W2 | NLP quick split | Hào | Hưng |
| W3 | OCR (rent bill & meters) | Hào | Hưng |
| W4 | Ledger service & data model | Hào | Kiệt |
| W5 | Debt simplification & settlement (VietQR) | Hào | Kiệt |
| W6 | Mini App UI (screens) | Nam | Hào |
| W7 | UX / design system | Nam | Tôn |
| W8 | Quality (test plan, test cases, acceptance) | Hưng | All |
| W9 | Documentation (SDP, vision, reports, PA) | Kiệt / Tôn | All |

---

## Sprint-by-sprint allocation

### Sprint 1 — Inception

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T1 | Problem validation & user research summary | Tôn | All | W9 |
| T2 | Project plan (SDP) | Kiệt | All | W9 |
| T3 | Vision document | Tôn | Kiệt | W9 |
| T4 | UI sketches (3–6 screens) | Nam | Kiệt | W6/W7 |
| T5 | Weekly reports 1 & 2 | Kiệt | Tôn | W9 |
| T6 | Tools setup (Jira, GitHub) & access | Kiệt | Hào | W9 |

### Sprint 2 — Elaboration

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T7 | Use-case model & specifications | Tôn | Hào | W9 |
| T8 | Software architecture document (draft) | Hào | Kiệt | W4 |
| T9 | NLP quick-split spike (msg → entry) | Hào | Hưng | W2 |
| T10 | OCR rent-bill spike (extract fields) | Hào | Hưng | W3 |
| T11 | Vision document — detailed update | Tôn | Kiệt | W9 |
| T12 | Weekly reports | Kiệt | Tôn | W9 |

### Sprint 3 — Elaboration

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T13 | Finalize architecture (SAD v1) | Hào | Kiệt | W4 |
| T14 | UI prototype (clickable) | Nam | Kiệt | W6/W7 |
| T15 | Debt-simplification algorithm spike | Hào | Hưng | W5 |
| T16 | Test plan & test cases | Hưng | Hào | W8 |
| T17 | Revised SDP + weekly reports | Kiệt | Tôn | W9 |

### Sprint 4 — Construction

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T18 | Telegram bot integration | Hào | Hưng | W1 |
| T19 | NLP quick-split implementation | Hào | Hưng | W2 |
| T20 | Ledger service + data model | Hào | Kiệt | W4 |
| T21 | OCR bill/meter parsing implementation | Hào | Hưng | W3 |
| T22 | Add Expense screen (S3) | Nam | Hào | W6 |
| T23 | Dashboard screen (S2) | Nam | Hào | W6 |
| T24 | Rent Bill Review screen (S4) | Nam | Hào | W6 |
| T25 | Ledger/History screen (S7) | Nam | Hào | W6 |
| T26 | Debt simplification implementation | Hào | Hưng | W5 |
| T27 | Integration testing → **Build 2** | Hưng | All | W8 |

### Sprint 5 — Construction

| ID | Task | Owner | Reviewer | WS |
|---|---|---|---|---|
| T28 | Settlement / VietQR implementation | Hào | Kiệt | W5 |
| T29 | Settlement screen, 3 states (S5) | Nam | Hào | W6 |
| T30 | Monthly Report screen + charts (S6) | Nam | Hào | W6 |
| T31 | Report data jobs / analytics | Hào | Hưng | W5 |
| T32 | Acceptance testing + bug fixing | Hưng | All | W8 |
| T33 | User guide & final docs | Tôn | Kiệt | W9 |
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
- **Weekly:** 1 status report (Kiệt) + board grooming (Kiệt).
