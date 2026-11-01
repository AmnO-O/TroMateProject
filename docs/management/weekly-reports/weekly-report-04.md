# Weekly Report

**26/10/2026 – 01/11/2026**

**Group ID:** 06
**Project Name:** TroMate — Roommate Expense & Rent Reconciliation Bot
**Prepared by:** Phạm Hữu Nam (PHNam)

**Team members:**

- 24125008 – Nguyễn Gia Hào (NGHao) — Technical Lead
- 24125010 – Cao Quảng Hưng (CQHung) — QA / Tester
- 24125013 – Trịnh Võ Nam Kiệt (TVNKiet) — Scrum Master / Project Lead
- 24125015 – Phạm Hữu Nam (PHNam) — UI/UX Designer
- 24125020 – Huỳnh Chí Tôn (HCTon) — Product Owner / Business Analyst

---

## Achievements since last week

| STT | Description | Due Date | Responsibility | %Complete |
|---|---|---|---|---|
| 1 | Revise Vision Document (SCRUM-95) | 25/10 | HCTon | 100% |
| 2 | Revise Project Plan (SCRUM-94) | 25/10 | NGHao | 100% |
| 3 | Create Use Case Diagrams (SCRUM-103) | 27/10 | HCTon | 100% |
| 4 | Initialize Mini App (SCRUM-102) | 28/10 | PHNam | 100% |
| 5 | Evaluate OCR (SCRUM-99) | 28/10 | NGHao | 100% |
| 6 | Integrate e-wallet (SCRUM-101) | 28/10 | CQHung | 100% |
| 7 | Research QR Debt Payments (SCRUM-110) | 28/10 | TVNKiet | 100% |
| 8 | Create Use Case Specifications (SCRUM-104) | 28/10 | CQHung | 100% |
| 9 | Update UI Prototyping (SCRUM-97) | 30/10 | TVNKiet, PHNam | 100% |
| 10 | Fill in the Weekly Report (Week 3 & Week 4) (SCRUM-106) | 01/11 | PHNam | 100% |
| 11 | Package and Submit PA2 Deliverables (SCRUM-105) | 01/11 | PHNam, all | 100% |

## Issues and impacts

- Writing comprehensive Use Case Specifications (SCRUM-104) covering complex multi-party expense splits, mid-month roommate departure, and partial debt settlements required extensive edge-case analysis. **Impact:** BA and QA conducted cross-review sessions to define clear preconditions, postconditions, and alternative flows, ensuring ambiguity is resolved before Sprint 3 implementation. (Responsible: CQHung, HCTon, Action date: 28/10)
- Direct e-wallet API integration (MoMo/ZaloPay) imposes merchant licensing constraints and transaction fees that are unsuitable for casual student room settlements. **Impact:** The team resolved to adopt dynamic VietQR payloads as the primary settlement rail with deep-linking to banking apps, ensuring zero fees and instant confirmation. (Responsible: CQHung, TVNKiet, Action date: 28/10)
- Tight deadline leading up to PA2 submission on 01/11 with 11 parallel Jira deliverables across documentation, UI prototyping, and technical spikes. **Impact:** Work was distributed according to Scrum roles with continuous tracking on the Jira board; all deliverables passed review and were packaged on schedule. (Responsible: TVNKiet, Action date: 01/11)

## Next week's goals

| STT | Description | Due Date | Responsibility |
|---|---|---|---|
| 1 | Sprint 3 Planning & decision on automatic payment notification research (T05/T07) | 02/11 | TVNKiet, all |
| 2 | Bot skeleton and Telegram webhook implementation (T07.1) | 08/11 | NGHao |
| 3 | CI pipeline setup: GitHub Actions for linting and unit tests (T07.2) | 05/11 | CQHung |
| 4 | PostgreSQL and Redis setup, initial database schema & migrations (T07.3) | 06/11 | TVNKiet |
| 5 | Natural-language expense parsing: extract amount, payer, and payees (T08.1) | 08/11 | NGHao |
| 6 | Currency normalization engine for Vietnamese slang (k, tr, củ ...) (T08.2) | 08/11 | TVNKiet |
| 7 | Curate test corpus of real chat expense messages for validation (T08.3) | 07/11 | CQHung |
| 8 | Draft Software Architecture Document (SAD) and system overview (T12.1) | 08/11 | NGHao |
| 9 | Design UML models: class, sequence, and state diagrams (T12.2) | 08/11 | HCTon |
| 10 | Draft Test Plan and baseline test cases for text logging flow (T12.3) | 08/11 | CQHung |
| 11 | Prepare UI assets & component specs for confirmation cards and opt-out settings (T09.2, T10.2) | 08/11 | PHNam |
| 12 | Weekly report 5 prepared | 08/11 | PHNam |
