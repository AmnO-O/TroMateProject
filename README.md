# TroMate

**Roommate expense & rent reconciliation bot** — the dorm's automatic "chief accountant", living right inside your group chat.

*Elements of Software Engineering — 24A01 · Group 06*

---

## What is TroMate?

TroMate is a chatbot integrated into the roommate group chat (Telegram, with a web/Mini App) that removes the friction of tracking shared money:

- **Logs expenses from natural-language chat** — e.g. *"mua nước 50k chia 3"*.
- **Reads rent bills & meter photos via OCR** (handwritten, thermal, or chat-image invoices).
- **Simplifies circular debts** so members settle with the fewest possible transfers.
- **Settles to the exact đồng with dynamic VietQR** (NAPAS), confirmed by the treasurer.

No installation required — it lives where roommates already talk.

## The problem

1. **Fragmented micro-debts** — daily shared purchases (water, spices, WiFi) are too small to bother opening an app or spreadsheet for.
2. **Painful end-of-month rent reconciliation** — landlord invoices contain many variables (base rent, electricity readings, water, garbage, parking) that the payer computes and offsets by hand.
3. **"Awkward debt" psychology** — circular debt chains and embarrassment about reminding roommates to pay.

## Key features

| Priority | Feature |
|---|---|
| **MVP core** | Natural-language quick split · Rent bill OCR parser · Debt-simplification engine · One-tap VietQR settlement |
| **Supporting** | Meter scanner · Monthly expense report · Shared room fund · Chore scheduler |
| **Later** | Polite meme reminders · Move-in/deposit checklist · Zalo integration |

## How it works

```
Member/Treasurer ─► Bot (NLP + OCR) ─► Group Ledger ─► Debt Simplification ─► VietQR ─► Mini App / Bank
                                                          ▲                                │
                                                          └──── treasurer confirms ◄────────┘
```

Two core journeys:
- **Daily expense:** chat → parsed → *editable preview* (amount, payer, split, beneficiaries) → confirm → ledger.
- **Rent bill:** photo → OCR fields → *human review/approval* → offset advances → minimize debts → per-member VietQR → *treasurer confirms receipt* (scan ≠ paid).

## Main screens (MVP)

Dashboard · Add Expense · Rent Bill Review · Settlement (3 states) · Monthly Report · Ledger.

## Platform

Mobile-first web app + **Telegram Bot API** & **Mini App** (no install). Payments via **VietQR / NAPAS**. **Zalo** is a future option, subject to API policy.

## Tech stack

> _To be finalized during Elaboration._ Planned: Telegram Bot API, a backend service (NLP + OCR + ledger), a web/Mini App frontend, and a database. Free-tier services only (zero budget).

## Repository structure

```
docs/            analysis & design, management, requirements, test
pa/PA0/          project proposal, tools, interview questions
pa/PA1/          project plan (SDP), vision, UI prototyping, weekly reports
src/             application source (to be populated)
```

## Documentation

- **Project proposal (PA0):** [`pa/PA0/project-proposal.md`](pa/PA0/project-proposal.md)
- **Tools & access (PA0):** [`pa/PA0/tools.md`](pa/PA0/tools.md)
- **Software Development Plan (PA1):** [`pa/PA1/project-plan/software-development-plan.md`](pa/PA1/project-plan/software-development-plan.md)
- **User flows & screens (PA1):** [`pa/PA1/ui-prototyping/flow.md`](pa/PA1/ui-prototyping/flow.md)

## Team — Group 06

| Name | Student ID | Email | Role |
|---|---|---|---|
| Nguyễn Gia Hào | 24125008 | nghao2420@apcs.fitus.edu.vn | Project Manager · Backend |
| Cao Quảng Hưng | 24125010 | cqhung2420@apcs.fitus.edu.vn | Backend · AI (NLP/OCR) |
| Trịnh Võ Nam Kiệt | 24125013 | tvnkiet2406@apcs.fitus.edu.vn | Frontend (Mini App) |
| Phạm Hữu Nam | 24125015 | phnam2409@apcs.fitus.edu.vn | Frontend · UI/UX |
| Huỳnh Chí Tôn | 24125020 | hcton2426@apcs.fitus.edu.vn | QA · Documentation |

## Links

- **Repository:** https://github.com/AmnO-O/TroMateProject
- **Jira board:** https://apcs24-cs300.atlassian.net/jira
- **User survey:** https://docs.google.com/forms/d/e/1FAIpQLScM5yP4aliMYLqN7aDY88b7SqNZ4aVUaF5TYSiHEhPrL0CenA/viewform

## Status

**Inception phase (Sprint 1).** Project plan, vision, and UI prototyping in progress.
