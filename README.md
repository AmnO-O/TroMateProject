# TroMate

**Roommate expense & rent reconciliation bot** — the dorm's automatic "chief accountant", living right inside your group chat.

| | |
|---|---|
| **Course** | Elements of Software Engineering — 24A01 |
| **Group** | 06 |
| **Status** | Inception phase (Sprint 1) |

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Main Screens](#main-screens)
- [Platform & Technology](#platform--technology)
- [Repository Structure](#repository-structure)
- [Folder Guide](#folder-guide)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Team](#team)
- [Links](#links)

---

## Overview

TroMate is a chatbot that lives in the roommate group chat (Telegram, with a web/Mini App) and removes the friction of tracking shared money:

- **Logs expenses from natural-language chat** — e.g. *"mua nước 50k chia 3"*.
- **Reads rent bills and meter photos via OCR** (handwritten, thermal, or chat-image invoices).
- **Simplifies circular debts**, so members settle with the fewest possible transfers.
- **Settles to the exact đồng with dynamic VietQR** (NAPAS), confirmed by the treasurer.

No installation is required — it lives where roommates already talk.

## Problem Statement

1. **Fragmented micro-debts** — daily shared purchases (water, spices, Wi-Fi) are too small to bother opening an app or spreadsheet for.
2. **Painful end-of-month rent reconciliation** — landlord invoices contain many variables (base rent, electricity readings, water, garbage, parking) that the payer computes and offsets by hand.
3. **"Awkward debt" psychology** — circular debt chains and embarrassment about reminding roommates to pay.

## Key Features

| Priority | Features |
|---|---|
| **MVP core** | Natural-language quick split · Rent bill OCR parser · Debt-simplification engine · One-tap VietQR settlement |
| **Supporting** | Meter scanner · Monthly expense report · Shared room fund · Chore scheduler |
| **Later** | Polite meme reminders · Move-in/deposit checklist · Zalo integration |

## How It Works

```
Member/Treasurer ─► Bot (NLP + OCR) ─► Group Ledger ─► Debt Simplification ─► VietQR ─► Mini App / Bank
                                                          ▲                                │
                                                          └──── treasurer confirms ◄────────┘
```

Two core journeys:

- **Daily expense:** chat → parsed → *editable preview* (amount, payer, split, beneficiaries) → confirm → ledger.
- **Rent bill:** photo → OCR fields → *human review/approval* → offset advances → minimize debts → per-member VietQR → *treasurer confirms receipt* (scan ≠ paid).

## Main Screens

The MVP comprises six main screens:

**Dashboard** · **Add Expense** · **Rent Bill Review** · **Settlement** (3 states) · **Monthly Report** · **Ledger**

See [`pa/PA1-Group06/ui-prototyping/flow.md`](pa/PA1-Group06/ui-prototyping/flow.md) for the user flows and [`pa/PA1-Group06/ui-prototyping/ui-prompts.md`](pa/PA1-Group06/ui-prototyping/ui-prompts.md) for the screen designs.

## Platform & Technology

Mobile-first web app plus the **Telegram Bot API** and **Mini App** (no install). Payments are handled via **VietQR / NAPAS**. **Zalo** is a future option, subject to API policy.

> **Tech stack — to be finalized during Elaboration.** Planned: Telegram Bot API, a backend service (NLP + OCR + ledger), a web/Mini App frontend, and a database. Free-tier services only (zero budget).

## Repository Structure

```
TroMateProject/
├── docs/                      # Project documentation (by discipline)
│   ├── analysis and design/   # UML models, architecture, design artifacts
│   ├── management/            # Schedules, plans, meeting notes, reports
│   ├── requirements/          # Requirements, use cases, specifications
│   └── test/                  # Test plans, test cases, test results
├── pa/                        # Course practical assignments (one subfolder per assignment)
├── src/                       # Application source code
└── README.md
```

## Folder Guide

Each folder has a single, clearly scoped purpose:

| Folder | Purpose |
|---|---|
| **`docs/`** | Long-lived project documentation, organized by discipline. |
| └ `docs/analysis and design/` | Analysis and design artifacts — UML models, software architecture, and design decisions. |
| └ `docs/management/` | Management artifacts — schedules, plans, meeting notes, and status reports. |
| └ `docs/requirements/` | Requirements and specifications — functional/non-functional requirements and use cases. |
| └ `docs/test/` | Quality assurance artifacts — test plan, test cases, and test results. |
| **`pa/`** | Graded practical-assignment deliverables, one subfolder per assignment (e.g. `PA0`, `PA1-Group06`). |
| **`src/`** | Application source code, populated during the Construction phase. |

## Documentation

| Document | Location |
|---|---|
| Project proposal (PA0) | [`pa/PA0/project-proposal.md`](pa/PA0/project-proposal.md) |
| Tools & access (PA0) | [`pa/PA0/tools.md`](pa/PA0/tools.md) |
| Software Development Plan (PA1) | [`pa/PA1-Group06/project-plan/software-development-plan.md`](pa/PA1-Group06/project-plan/software-development-plan.md) |
| Task assignment (PA1) | [`pa/PA1-Group06/project-plan/task-assignment.md`](pa/PA1-Group06/project-plan/task-assignment.md) |
| User flows & screens (PA1) | [`pa/PA1-Group06/ui-prototyping/flow.md`](pa/PA1-Group06/ui-prototyping/flow.md) |

## Roadmap

The project follows three phases across five two-week sprints:

| Phase | Sprints | Focus |
|---|---|---|
| **Inception** | Sprint 1 | Problem validation, project plan, vision, UI sketches |
| **Elaboration** | Sprints 2–3 | Architecture & detailed design, use cases, NLP/OCR spikes, UI prototype |
| **Construction** | Sprints 4–5 | Implementation, integration, testing, and release |

## Team

**Group 06**

| Name | Student ID | Email | Role |
|---|---|---|---|
| Nguyễn Gia Hào | 24125008 | nghao2420@apcs.fitus.edu.vn | Project Manager · Backend |
| Cao Quảng Hưng | 24125010 | cqhung2420@apcs.fitus.edu.vn | Backend · AI (NLP/OCR) |
| Trịnh Võ Nam Kiệt | 24125013 | tvnkiet2406@apcs.fitus.edu.vn | Frontend (Mini App) |
| Phạm Hữu Nam | 24125015 | phnam2409@apcs.fitus.edu.vn | Frontend · UI/UX |
| Huỳnh Chí Tôn | 24125020 | hcton2426@apcs.fitus.edu.vn | QA · Documentation |

## Links

- **Repository:** <https://github.com/AmnO-O/TroMateProject>
- **Jira board:** <https://apcs24-cs300.atlassian.net/jira>
- **User survey:** <https://docs.google.com/forms/d/e/1FAIpQLScM5yP4aliMYLqN7aDY88b7SqNZ4aVUaF5TYSiHEhPrL0CenA/viewform>

---

*Elements of Software Engineering — 24A01 · Group 06 · University of Science (FITUS)*
