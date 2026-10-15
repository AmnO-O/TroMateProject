# Project Documentation — `docs/`

This folder is the project's **living documentation library**, organised by RUP discipline.

It is **not** the submission folder. Each assignment is handed in as a self-contained package under [`../pa/`](../pa/) — for example [`../pa/PA1-Group06/`](../pa/PA1-Group06) for PA1.

## Two locations, two purposes

| Location | What it is | Example |
|---|---|---|
| `pa/PA<n>-GroupNN/` | **Submission package** — the frozen set of files handed in for that assignment | `pa/PA1-Group06/vision/vision-document.md` |
| `docs/<discipline>/` | **Living library** — the current version of each document, by discipline | `docs/requirements/vision.md` |

When a document is revised in a later phase, the new version is updated **here first**, then copied into the relevant `pa/` package at submission time. A submitted copy is never edited afterwards — it is a snapshot of what was handed in.

## What goes where

| Folder | Discipline | Documents | Produced in |
|---|---|---|---|
| `requirements/` | **Requirements Definition** — *what the system must do* | Vision document · Software Requirements Specification (SRS) · use-case model & user stories | Inception → Elaboration |
| `analysis and design/` | *How it is built* | Software Architecture Document (SAD) · data model / ERD · UI prototype | Elaboration |
| `management/` | *Plan & track* | Software Development Plan (SDP) · task assignment · risk register · weekly reports | Inception → every sprint |
| `test/` | *Verify* | Test plan · test cases · test results | Elaboration → Construction |

## Current contents

| Document | Living copy (`docs/`) | Submission (`pa/`) |
|---|---|---|
| Vision Document | [`requirements/vision.md`](requirements/vision.md) | [`../pa/PA1-Group06/vision/vision-document.md`](../pa/PA1-Group06/vision/vision-document.md) |

The remaining documents — **SRS**, **use cases**, **SAD**, **test plan & cases** — are Elaboration-phase deliverables and will be added here as they are produced (Sprints 2–3).
