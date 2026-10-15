# TroMate — Roommate expense & rent reconciliation bot

Practical assignments for **Elements of Software Engineering** (24A01),
University of Science, VNU-HCM (Advanced Program in Computer Science). Group 06.

TroMate lives in the roommate group chat and does the shared-money bookkeeping
nobody wants to do by hand. An ordinary message becomes an expense; a photo of
the rent bill becomes itemized charges; the circular debts cancel out; and each
person gets one exact-amount VietQR to pay.

---

## 1. Team

| Student ID | Name | GitHub | Responsibility |
|---|---|---|---|
| `24125008` | Nguyễn Gia Hào | _TBD_ | Project manager, backend — ledger and debt simplification |
| `24125010` | Cao Quảng Hưng | _TBD_ | Bot and AI — natural-language parsing, bill OCR |
| `24125013` | Trịnh Võ Nam Kiệt | _TBD_ | Frontend — Mini App screens |
| `24125015` | Phạm Hữu Nam | AmnO-O | Frontend and UI/UX — flow, screens, reports |
| `24125020` | Huỳnh Chí Tôn | _TBD_ | QA and documentation — test plan, weekly reports |

## 2. What the app does

- **Quick split from chat** — "mua nước 50k chia 3" becomes an expense you can
  edit before it is saved: amount, payer, split method and who shares it.
- **Rent bill reading** — the treasurer photographs the bill; OCR pulls out base
  rent, electricity and water readings, unit prices and surcharges for review.
- **Fewest transfers** — circular and chain debts are simplified so members
  settle with the smallest number of payments.
- **One-tap settlement** — a VietQR for the exact amount. Scanning is not
  payment; the treasurer confirms receipt before anyone is marked as paid.
- **Monthly report** — where the money went, split by category and by person.

## 3. How it works

```
Member/Treasurer ─► Bot (NLP + OCR) ─► Group Ledger ─► Debt Simplification ─► VietQR ─► Bank
                                                          ▲                                │
                                                          └──── treasurer confirms ◄────────┘
```

Two journeys matter most:

- **Daily expense:** chat → parsed → editable preview → confirm → ledger.
- **Rent bill:** photo → OCR fields → human review/approval → offset advances →
  minimize debts → per-member VietQR → treasurer confirms receipt.

The full flows and the screen inventory are in
[`pa/PA1-Group06/ui-prototyping/flow.md`](pa/PA1-Group06/ui-prototyping/flow.md).

## 4. Platform and services

Mobile-first web app, delivered through the **Telegram Bot API** and a
**Mini App** (nothing to install). Payments use **VietQR / NAPAS**. **Zalo** is
a later option, subject to its API policy.

| Service | Key needed | Used for |
|---|---|---|
| Telegram Bot API + Mini App | no | the chat interface and the app shell |
| VietQR / NAPAS | no | exact-amount payment codes |
| Hosting + database | _TBD_ | backend service, ledger storage |
| Zalo | _TBD_ | future channel, not in the MVP |

Only free tiers are used — the project has no budget. The exact stack is settled
during Elaboration.

## 5. Project layout

```
docs/            analysis and design, management, requirements and test notes
pa/              graded practical assignments, one subfolder per assignment
  PA0/           project proposal, tools and access index
  PA1-Group06/   project plan, vision, UI prototyping and weekly reports
src/             application source code, populated during Construction
```

## 6. Deliverables

| Document | Location |
|---|---|
| Project proposal (PA0) | [`pa/PA0/project-proposal.md`](pa/PA0/project-proposal.md) |
| Tools and access (PA0) | [`pa/PA0/tools.md`](pa/PA0/tools.md) |
| Software Development Plan (PA1) | [`pa/PA1-Group06/project-plan/software-development-plan.md`](pa/PA1-Group06/project-plan/software-development-plan.md) |
| Task assignment (PA1) | [`pa/PA1-Group06/project-plan/task-assignment.md`](pa/PA1-Group06/project-plan/task-assignment.md) |
| User flows and screens (PA1) | [`pa/PA1-Group06/ui-prototyping/flow.md`](pa/PA1-Group06/ui-prototyping/flow.md) |

## 7. Status

**Inception (Sprint 1).** The proposal and project plan are done and the UI is
being prototyped. There is no runnable build yet; source code lands in `src/`
during the Construction phase. The plan runs three phases over five two-week
sprints.

## 8. Known limitations and assumptions

- **No budget.** Everything runs on free tiers; some services sleep when idle,
  so a first request after a pause can be slow.
- **OCR can be wrong.** Handwritten or faint bills misread, so extracted values
  are always shown for review before they reach the ledger.
- **Privacy is the top concern.** 67% of survey respondents named data leakage
  as their main worry; the design minimizes stored personal data and asks for
  consent explicitly.
- **Anyone can read the group chat.** Expense messages are posted where the
  whole room can see them, which is fine for this use but not for private notes.
- **Zalo is not supported yet.** It depends on API access we cannot assume.

---

*Elements of Software Engineering — 24A01 · Group 06 · University of Science,
VNU-HCM (FITUS)*
