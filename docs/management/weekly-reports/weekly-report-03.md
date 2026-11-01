# Weekly Report

**19/10/2026 – 25/10/2026**

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
| 3 | Create Use Case Diagrams — draft initial diagrams for MVP epics (SCRUM-103) | 25/10 | HCTon | 100% |
| 4 | Initialize Mini App — backend skeleton and Telegram authentication spike (SCRUM-102) | 25/10 | PHNam | 100% |
| 5 | Technical spike: Evaluate OCR engine for receipt and utility bill extraction (SCRUM-99) | 25/10 | NGHao | 100% |
| 6 | Technical spike: Research QR debt payments and VietQR standards (SCRUM-110) | 25/10 | TVNKiet | 100% |
| 7 | Technical spike: Integrate e-wallet — evaluate MoMo and ZaloPay API feasibility (SCRUM-101) | 25/10 | CQHung | 100% |
| 8 | Review clickable UI prototype and refine conversational flows (SCRUM-97) | 25/10 | TVNKiet | 100% |
| 9 | Writing weekly report 3 (SCRUM-106) | 25/10 | PHNam | 100% |

## Issues and impacts

- The Vision Document (SCRUM-95) and Project Plan (SCRUM-94) lacked sufficient detail in feature specifications and milestone criteria following initial review. **Impact:** Both documents were thoroughly revised with concrete requirements and sprint breakdowns; a Revision History table was added at the top of each document, and line-level changes were highlighted in blue text for transparent change tracking. (Responsible: HCTon, NGHao, Action date: 25/10)
- Presenting all use cases abstractly within a single combined table made complex flows and actor interactions difficult to interpret. **Impact:** The team restructured the requirements model by breaking down each use case into an individual, dedicated specification table detailing preconditions, main success scenarios, and alternative exception flows. (Responsible: HCTon, CQHung, Action date: 25/10)
- The UI prototype screens were complex and isolated across disconnected wireframes, obscuring the end-to-end user journey between Telegram bot interactions and Mini App views. **Impact:** The UI team synthesized the fragmented wireframes into cohesive visual user flow diagrams and an integrated Figma prototype, establishing seamless transitions across all key user paths. (Responsible: TVNKiet, PHNam, Action date: 25/10)
- Ensuring smooth payment settlement UX required investigating automated transfer notifications when roommates send funds via bank transfer, but standard retail banking lacks open webhook APIs. **Impact:** The team conducted technical spikes on VietQR standards and e-wallet deep-linking (SCRUM-101, SCRUM-110), establishing fallback payment confirmation protocols and transfer syntax parsing to verify settlements reliably. (Responsible: TVNKiet, CQHung, Action date: 25/10)

## Next week's goals

| STT | Description | Due Date | Responsibility |
|---|---|---|---|
| 1 | Finalize Use Case Diagrams and complete peer review (SCRUM-103) | 27/10 | HCTon |
| 2 | Complete Use Case Specifications for all MVP flows (SCRUM-104) | 28/10 | CQHung |
| 3 | Complete Mini App initialization and verify Telegram integration (SCRUM-102) | 28/10 | PHNam |
| 4 | Complete OCR evaluation spike and document engine recommendations (SCRUM-99) | 28/10 | NGHao |
| 5 | Complete e-wallet integration spike and mock transfer endpoints (SCRUM-101) | 28/10 | CQHung |
| 6 | Complete QR debt payments research and dynamic VietQR generator (SCRUM-110) | 28/10 | TVNKiet |
| 7 | Update UI Prototyping with high-fidelity Figma interactive prototype (SCRUM-97) | 30/10 | TVNKiet, PHNam |
| 8 | Fill in Weekly Reports for Week 3 and Week 4 (SCRUM-106) | 01/11 | PHNam |
| 9 | Package and submit PA2 deliverables (PA2-Group06) (SCRUM-105) | 01/11 | PHNam, all |
