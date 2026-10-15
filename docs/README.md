# TroMate — Documentation Library

*Elements of Software Engineering (24A01) · Group 06*
*Advanced Program in Computer Science (APCS), University of Science, VNU-HCM*

---

## 1. Overview

`docs/` is the TroMate project's **documentation library**. It maintains the current version of every project document, classified by RUP discipline, and provides a single reference point for the project's requirements, design, management and verification artefacts.

The library is maintained separately from the assignment submission packages. Each practical assignment is submitted as a self-contained package under `pa/`, which holds a frozen snapshot of the documents exactly as they were handed in.

## 2. Documentation Model

| Location | Role | Nature |
|---|---|---|
| `pa/PA<n>-GroupNN/` | Assignment submission package | **Frozen** — snapshot of the submitted files |
| `docs/<discipline>/` | Project documentation library | **Living** — current, maintained version |

**Maintenance convention**

1. Documents are authored and updated in `docs/`.
2. When an assignment is due, the relevant documents are copied into its `pa/PA<n>-GroupNN/` package.
3. A submitted copy is treated as read-only; any further revision is applied only in `docs/`.

## 3. Directory Structure

`docs/` mirrors the four RUP documentation disciplines.

| Directory | Discipline | Scope |
|---|---|---|
| `requirements/` | Requirements Definition | *What* the system must do — Vision, SRS, use-case model, user stories |
| `analysis-and-design/` | Analysis & Design | *How* the system is built — architecture, data model, UI design |
| `management/` | Project Management | Planning and tracking — plan, task assignment, risks, reports |
| `test/` | Test | Verification and validation — test plan, test cases, test results |

## 4. Document Register

| Document | Discipline | Living copy | Owner | Reviewer | Phase |
|---|---|---|---|---|---|
| Vision Document | Requirements | [`requirements/vision.md`](requirements/vision.md) | Phạm Hữu Nam | Huỳnh Chí Tôn | Inception |
| Software Development Plan | Management | [`management/software-development-plan.md`](management/software-development-plan.md) | Nguyễn Gia Hào | Huỳnh Chí Tôn | Inception |
| Task Assignment | Management | [`management/task-assignment.md`](management/task-assignment.md) | Nguyễn Gia Hào | All | Inception |
| UI Flows & Screen Inventory | Analysis & Design | [`analysis-and-design/ui-flows.md`](analysis-and-design/ui-flows.md) | Trịnh Võ Nam Kiệt | Phạm Hữu Nam | Inception |
| UI Prompts & Wireframes | Analysis & Design | [`analysis-and-design/ui-prompts.md`](analysis-and-design/ui-prompts.md) | Phạm Hữu Nam | Trịnh Võ Nam Kiệt | Inception |
| Software Requirements Specification | Requirements | *planned* | Phạm Hữu Nam | Nguyễn Gia Hào | Elaboration |
| Use-Case Model & User Stories | Requirements | *planned* | Phạm Hữu Nam | Nguyễn Gia Hào | Elaboration |
| Software Architecture Document | Analysis & Design | *planned* | Cao Quảng Hưng | Nguyễn Gia Hào | Elaboration |
| Data Model / ERD | Analysis & Design | *planned* | Nguyễn Gia Hào | Cao Quảng Hưng | Elaboration |
| Risk Register | Management | *planned* | Nguyễn Gia Hào | Huỳnh Chí Tôn | Elaboration |
| Test Plan | Test | *planned* | Huỳnh Chí Tôn | Nguyễn Gia Hào | Elaboration |
| Test Cases | Test | *planned* | Huỳnh Chí Tôn | Nguyễn Gia Hào | Elaboration |
| Test Results | Test | *planned* | Huỳnh Chí Tôn | Nguyễn Gia Hào | Construction |

### Assignment Records

| Record | Description | File |
|---|---|---|
| PA1 Checklist | Grading checklist mapped to the assignment brief | [`management/pa1-checklist.md`](management/pa1-checklist.md) |
| PA1 Division of Work | Together-vs-separate split of the PA1 work | [`management/pa1-division-of-work.md`](management/pa1-division-of-work.md) |

## 5. Conventions

- **Authoring format** — Markdown (`.md`); documents are written here and exported for submission.
- **Submission format** — Microsoft Word (`.docx`), Times New Roman, size 10, with all template guidance text removed.
- **File naming** — lower-case, kebab-case (e.g. `software-development-plan.md`).
- **Review** — every document has an **owner** and a **reviewer**; a document is considered final only after review.
- **Traceability** — requirements and use cases are traced to their Jira items and, in later phases, to test cases.