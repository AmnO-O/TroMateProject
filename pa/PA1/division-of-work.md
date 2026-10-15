# PA1 — Division of Work (Together vs Separate)

*Elements of Software Engineering — 24A01 · Group 06 · PA1*

This answers one question: for **this assignment** (PA1), what must the team do **together**, and what can be done **separately**?

## Principle

> **Decide together → write separately → review together.**

Any fact that appears in **more than one deliverable** (the problem, users, scope, features) must be agreed by the whole team first. If each member invents their own version, the Project Plan and Vision document will contradict each other — which is directly penalized. Unique, self-contained sections can be split and written in parallel.

---

## Step 1 — Do TOGETHER (one kickoff meeting)

Lock a single **shared-facts sheet** that both the plan and the vision will draw from:

- [ ] Problem statement (the pain)
- [ ] Target users & personas
- [ ] Project scope — what's in, what's out
- [ ] Goals / objectives
- [ ] Key features (the same list in both docs)
- [ ] Non-functional requirements (privacy, performance, usability)
- [ ] Roles & responsibilities (who owns what)
- [ ] Phase / sprint timeline (3 phases, 5 sprints) — consistent everywhere
- [ ] UI: the flow and the chosen 3–6 screens

**Output:** one page everyone agrees on (can reuse/expand the PA0 proposal).

---

## Step 2 — Do SEPARATELY (parallel, from the shared facts)

| PA1 item | Together or separate | Suggested owner |
|---|---|---|
| **a. Project plan** — §1 Introduction | Separate (write) | Hào |
| **a.** §2 Overview (purpose/scope/objectives) | *content together*, write-up separate | Hào |
| **a.** §3 Organization (roles) | *roles together*, write-up separate | Hào |
| **a.** §4.2 Plan (phases, builds, schedule) | *schedule together*, write-up separate | Hào |
| **a.** §4.3 Monitoring (4.3.1, 4.3.3) | Separate | Hào + Tôn |
| **b. Vision** — problem / users / features | *content together*, write-up separate | Nam |
| **b. Vision** — NFRs & diagrams | Separate (discuss NFRs) | Nam |
| **c. UI** — flow + screen selection | Together | All |
| **c. UI** — the 3–6 sketches | Separate | Nam Kiệt, Nam |
| **d. Weekly reports** (2 reports) | Each member reports **own** work; one compiles | Tôn (compiler) |
| **e. Execution & tracking** — Jira/GitHub setup | Separate | Hào |
| **e. Execution & tracking** — actually using the board | Everyone updates **own** tasks | All |

---

## Step 3 — Do TOGETHER (final pass)

- [ ] **Consistency review:** plan ↔ vision ↔ UI all tell the same story
- [ ] **Formatting:** Times New Roman, size 10; remove all `[blue italic]` guidance text
- [ ] **Completeness:** check every item in `checklist.md`
- [ ] **Assembly:** copy all files into `PA1-Group06/` and zip it

---

## Why this split

- **Together** = decisions with cross-document impact (scope, users, features, schedule, roles). Cheap to do in one meeting, expensive to fix later.
- **Separate** = writing and drawing, which parallelizes well once the facts are fixed.
- **Together again** = review, because grading is on the *set* of documents, not individuals.

> Note: PA1 is a **team** grade (50 pts). No single member "owns" the score, so the shared decisions are where the marks are won or lost.
