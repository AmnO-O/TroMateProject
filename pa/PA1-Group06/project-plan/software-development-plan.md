# TroMate — Software Development Plan (Small Project)

**Version 1.0**

> ⚠️ **Template note — remove this box before submission.**
> The PA1 brief references a *Software Development Plan (Small Project)* `.docx` template on Moodle that was not available in the repository. This file reconstructs the standard **RUP "Software Development Plan (Small Project)"** outline (Sections 1, 2, 3, 4.2, 4.3) as required by PA1. Before submitting, reconcile the heading numbers/names with the official Moodle template, then export to `.docx` in **Times New Roman, size 10**, removing the `[blue italic]` guidance text.
> Items marked **[CONFIRM]** are assumptions that the team must verify.

Group: 06 &nbsp;·&nbsp; Date: 13/10 &nbsp;·&nbsp; Document identifier: TroMate-SDP-v1.0

---

## Revision History

| Date | Version | Description | Author |
|---|---|---|---|
| 13/10 | 1.0 | Initial version: overview of the project plan for the Inception phase (PA1) | TroMate team |

---

## 1. Introduction

The introduction of the Software Development Plan provides an overview of the entire document. It includes the purpose, scope, definitions, acronyms, references, and overview of this plan.

### 1.1 Purpose

The purpose of the Software Development Plan (SDP) is to gather all information necessary to control the **TroMate** project. It describes the approach to the development of the software and is the top-level plan used by the team to direct the development effort. The following people use the SDP:

- The **project manager** uses it to plan the project schedule and resource needs, and to track progress against the schedule.
- **Project team members** use it to understand what they need to do, when they need to do it, and what other activities they depend upon.
- The **Teaching Assistant (TA)** uses it to review and supervise the team's execution and tracking.

### 1.2 Scope

This SDP describes the plan to be used by the **TroMate** project, including deployment of the product. The details of individual iterations are described in the iterations/sprints in Section 4.2. The plans outlined in this document are based on the product requirements defined in the **Vision Document**. TroMate is a chatbot integrated into group chats on Telegram (with a future Zalo integration) plus an embedded Mini App, acting as an automatic "chief accountant" for shared housing.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| **SDP** | Software Development Plan |
| **RUP** | Rational Unified Process — the process framework followed in this course |
| **MVP** | Minimum Viable Product |
| **NLP** | Natural Language Processing — used to parse chat messages into ledger entries |
| **OCR** | Optical Character Recognition — used to read rent bills and meter photos |
| **Mini App** | A web application embedded inside Telegram/Zalo, requiring no separate installation |
| **VietQR / NAPAS** | Vietnam's national QR payment standard used to generate exact-amount transfer codes |
| **TA** | Teaching Assistant |
| **CI/CD** | Continuous Integration / Continuous Delivery |
| **PII** | Personally Identifiable Information |
| **UI/UX** | User Interface / User Experience |

### 1.4 References

| Ref | Document | Location |
|---|---|---|
| R1 | TroMate Project Proposal (PA0) | `pa/PA0/project-proposal.md` |
| R2 | TroMate Vision Document | `pa/PA1-Group06/vision/` |
| R3 | This course's project plan template (RUP *Software Development Plan (Small Project)*) | Moodle |
| R4 | Course lecture notes on project assignments and schedule | Moodle |
| R5 | Source code & documentation repository | https://github.com/AmnO-O/TroMateProject |
| R6 | Task & sprint board (Jira) | https://apcs24-cs300.atlassian.net/jira |
| R7 | PA0 tools & access index | `pa/PA0/tools.md` |

### 1.5 Overview

This SDP contains the following information:

- **Project Overview** — a description of the project's purpose, scope, and objectives, and the deliverables the project is expected to produce.
- **Project Organization** — the organizational structure of the team and each member's roles and responsibilities.
- **Management Process** — project estimates, the project plan (phases, iterations, builds, and schedule), and project monitoring and control.

---

## 2. Project Overview

### 2.1 Project Purpose, Scope, and Objectives

**Purpose.**
TroMate addresses the fragmented micro-debts and painful end-of-month rent reconciliation experienced by roommates in shared housing. The team is building it because tracking small shared expenses is too high-friction (no one wants to open an app or spreadsheet to log a few tens of thousands of đồng), rent invoices must be manually computed and offset against each member's advances, and "awkward debt" psychology makes settlement unpleasant.

**Scope.**
The scope of this project includes the development and deployment of the TroMate platform, which encompasses:

- A **Telegram chatbot** that collects data from group chats.
- A **web application / Mini App** providing the main UI, accessible through desktop and mobile browsers and inside Telegram.
- **Natural-language expense logging** (parsing everyday chat messages into ledger entries).
- **Rent bill and meter OCR** to extract itemized charges from photos.
- A **debt-simplification engine** (minimum cash-flow algorithm).
- **VietQR dynamic settlement** with a "Received" confirmation.
- Monthly expense reporting and supporting features.

*Out of scope for the MVP:* direct Zalo integration (subject to API/access policy), and any automated transfer execution (settlement is confirmed manually).

**Objectives.**
- Deliver a working MVP that logs shared expenses, reads rent bills, minimizes circular debts, and enables one-tap settlement.
- Ensure the app is low-friction (no install) and approachable for non-technical roommates.
- Address the survey's top adoption blocker — **data privacy** — through explicit data-handling and consent design.

### 2.2 Assumptions and Constraints

**Assumptions.**
- All 5 team members have continuous access to the necessary development tools and free-tier services.
- Members will learn the required technologies (bot frameworks, OCR, web frontend) during the project.
- Target users already use Telegram group chats for roommate communication.
- Third-party APIs (Telegram Bot API, VietQR/NAPAS) remain available and their terms permit the intended use.
- Users are willing to grant message access and upload bill photos within the group chat.

**Constraints.**
- **Timeline:** the project runs for the course duration, structured as **5 two-week sprints** (see Section 4.2).
- **Staff:** exactly **5 members**, with varying expertise and no external support.
- **Budget:** effectively **zero** — the project must rely on free tiers (GitHub, Jira, free-tier hosting/database, free Telegram APIs).
- **Privacy:** the survey found **67%** cite fear of data leakage as the top barrier; the design and this plan must respect data consent and minimization.
- **Platform policy:** Zalo integration depends on Zalo's API access policy and is deferred.

### 2.3 Project Deliverables

Deliverables for each phase are identified below and are delivered towards the end of the iteration, as specified in Section 4.2.

| Phase | Key deliverables |
|---|---|
| **Inception** | PA0 proposal; Project Plan (this SDP); Vision document; 3–6 UI sketches; 2 weekly reports; PA1 submission |
| **Elaboration** | Revised SDP; detailed Vision document; use-case model & specifications; draft Software Architecture Document (SAD); UI prototype; test plan; weekly reports |
| **Construction** | Implemented MVP (3 test builds); test cases & results; user guide; final release; project presentation |

---

## 3. Project Organization

### 3.1 Organizational Structure

TroMate is developed by a small, flat team of **5** members. Rather than a deep hierarchy, the team uses a **lightweight Scrum** approach: a project manager coordinates a single cross-functional team that divides work into the feature areas (chat bot & NLP, OCR/computer vision, frontend/Mini App, and quality/testing). All members contribute to documentation and reporting. Task assignment and progress are tracked on the Jira board (R6).

```
                         TroMate Team (5)
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        Project Manager   Backend/AI      Frontend/UX        Quality & Docs
        (coordination)   (bot, NLP, OCR) (Mini App, UI)     (testing, reports)
```

### 3.2 Roles and Responsibilities

> **[CONFIRM]** The role allocation below is a *proposal* based on team size; confirm with members before submission.

| Member (Name, ID) | Role | Responsibilities |
|---|---|---|
| Nguyễn Gia Hào (24125008) | Project Manager, Backend Developer | Plans and tracks the schedule; assigns tasks; supports development; reviews deliverables |
| Cao Quảng Hưng (24125010) | Backend Developer, AI (NLP & OCR) | Builds the bot backend, natural-language parsing, and OCR bill/meter extraction |
| Trịnh Võ Nam Kiệt (24125013) | Frontend Developer (Mini App) | Develops the Mini App / web UI and VietQR settlement flow |
| Phạm Hữu Nam (24125015) | Frontend Developer, UI/UX Designer | Designs UX and screens; implements UI components |
| Huỳnh Chí Tôn (24125020) | Tester, Documentation | Writes and runs test cases; maintains weekly reports and assignment documents |

*Note (per PA1 guidance): responsibilities that do not apply to this project have been removed.*

---

## 4. Management Process

### 4.1 Project Estimates

- **Effort:** ≈ **5 members × 10 weeks ≈ 50 person-weeks** across the 5 two-week sprints.
- **Cost:** ≈ **0 VND**. The project relies on free tiers:
  - Hosting/database: free-tier cloud (e.g., free student credit / free database tier).
  - Repository & CI: GitHub (free).
  - Task tracking: Jira (free tier).
  - APIs: Telegram Bot API (free); VietQR generation via a public library/service.
- **Equipment:** each member's personal laptop; personal mobile phones for Mini App testing.

### 4.2 Project Plan

#### 4.2.1 Phase and Iteration Plan

TroMate follows **3 phases** and **5 iterations/sprints**, each sprint lasting **2 weeks**.

| Phase | Sprints | Focus |
|---|---|---|
| **Inception** | Sprint 1 | Problem validation, requirements, project plan, vision, UI sketches |
| **Elaboration** | Sprint 2–3 | Architecture and detailed design, use cases, technical spikes (NLP/OCR), UI prototype |
| **Construction** | Sprint 4–5 | Implementation, integration, testing, release |

**Sprint objectives**

| Sprint | Phase | Objectives |
|---|---|---|
| **Sprint 1** | Inception | Project plan (SDP), Vision document, UI sketches, 2 weekly reports, PA0/PA1 |
| **Sprint 2** | Elaboration | Detailed Vision; use-case model & specs; draft SAD; NLP & OCR spike; revised SDP |
| **Sprint 3** | Elaboration | Finalize architecture; UI prototype; test plan; debt-simplification algorithm spike |
| **Sprint 4** | Construction | Implement core MVP (ledger, NLP, OCR, debt engine); Build 2; weekly reports |
| **Sprint 5** | Construction | VietQR settlement, reports, polish; final build, testing, presentation |

#### 4.2.2 Builds

The team will produce **3 integrated builds for testing** (one per key integration point), plus the final release:

| Build | When | Contents | Purpose |
|---|---|---|---|
| **Build 1 (alpha)** | End of Elaboration (≈ end of Sprint 3) | Core ledger + natural-language quick split | Internal smoke test of the logging flow |
| **Build 2 (beta)** | Mid-Construction (≈ Sprint 4) | + Rent bill OCR + debt-simplification engine | Integration & functional testing |
| **Build 3 (RC)** | End of Construction (≈ Sprint 5) | + VietQR settlement, monthly report, final polish | Acceptance testing → final release |

#### 4.2.3 Project Schedule

> **[CONFIRM]** Dates below assume Sprint 1 ends at the PA1 due date (18/10) with 2-week sprints. Confirm/adjust to match the course calendar and the Jira board before submission.

| Phase | Iteration | Start | End | Key tasks | Result / Release | Owner(s) |
|---|---|---|---|---|---|---|
| Inception | Sprint 1 | 05/10 | 18/10 | Confirm problem & users; write project plan, vision, UI sketches; weekly reports | PA0, PA1, Vision v0, 3–6 UI sketches | All |
| Elaboration | Sprint 2 | 19/10 | 01/11 | Requirements & use cases; architecture draft; NLP/OCR spikes | Use-case model, draft SAD | Hưng, Nam Kiệt |
| Elaboration | Sprint 3 | 02/11 | 15/11 | Finalize architecture; UI prototype; test plan; debt algorithm | **Build 1 (alpha)**, test plan | Hào, Tôn |
| Construction | Sprint 4 | 16/11 | 29/11 | Implement ledger, NLP, OCR, debt engine; integrate | **Build 2 (beta)** | Hưng, Nam |
| Construction | Sprint 5 | 30/11 | 13/12 | VietQR settlement, reports, testing, polish, presentation | **Build 3 (RC)** → final release | All |

Detailed per-task assignment (owner + reviewer per task) and the Jira board convention are in [`task-assignment.md`](./task-assignment.md).

### 4.3 Project Monitoring and Control

#### 4.3.1 Requirements Management

The requirements for TroMate are captured in the **Vision document** (R2) and elaborated into use cases during Elaboration. Requested changes are recorded as issues on the **Jira** board (R6) and, where they affect scope, reviewed by the project manager against the schedule before approval. All requirements and use cases are traceable to the corresponding Jira items and, later, to test cases. Changes that threaten the MVP scope are deferred to a "future release" backlog.

#### 4.3.2 Reporting and Measurement

*[Left blank for now, per PA1 instructions.]*

#### 4.3.3 Risk Management

Risks are identified during Inception and re-evaluated at least once per iteration; the table below lists the highest-magnitude risks first.

| Ranking | Risk | Impact | Mitigation / Contingency |
|---|---|---|---|
| High | **Privacy / data leakage** (67% of survey respondents' top concern) | Users refuse to adopt the bot | Clear data-handling & consent policy; minimize stored PII; allow deleting entries; document retention explicitly |
| High | **Scope creep** — too many candidate features (10 proposed) | MVP not finished in 5 sprints | Freeze the MVP feature set after Elaboration; move extras to a future backlog |
| High | **Intensive new technologies** (NLP, OCR, bot APIs) learned in parallel | Delays and low quality | Divide learning into small spikes per sprint; pair members; timebox research |
| Medium | **OCR accuracy** on handwritten/low-quality bills | Wrong splits, lost trust | Allow users to review/correct extracted values; keep the original photo for reconciliation |
| Medium | **Member availability** varies (different schedules) | Missed sprint goals | Weekly check-ins; redistribute tasks; buffer within each sprint |
| Medium | **Platform/API policy changes** (Telegram, Zalo, VietQR/NAPAS) | Blocked integration | Prefer stable, documented APIs; abstract integrations; keep Zalo optional |
| Low | **Team member turnover** | Knowledge loss | Document decisions in the repo; maintain the Jira board as the single source of truth |

---

## 5. Annexes

*(Reserved — no content in this version.)*
