# TroMate — Roommate Expense & Rent Reconciliation Bot

*Elements of Software Engineering — 24A01 — PA0 Project Proposal*

## 1. Introduction

### 1.1 The problem

Shared living is full of small, fragmented money that no one wants to track:

- **Fragmented micro-debts.** Daily shared purchases (spices, drinking water, WiFi, groceries) happen constantly but are scattered. Nobody wants to install a dedicated app or open a Google Sheet on their phone just to log a few tens of thousands of đồng.
- **Painful end-of-month rent reconciliation.** Rent invoices from landlords (handwritten, chat messages, thermal prints) contain many variables (base rent, old/new electricity readings, water volume, garbage fee, motorbike parking). The person who pays must manually compute everything and offset each member's advances — slow and error-prone.
- **Transaction friction and "awkward debt" psychology.** Circular debt chains (A owes B, B owes C) make settlement annoying, and roommates often feel embarrassed to remind each other to transfer rent money.

### 1.2 The solution

TroMate is a **chatbot integrated directly into the group chat on Telegram / Zalo**, paired with an embedded **Mini App** (no installation required). It acts as the dorm's **automatic "chief accountant"**. It lets users:

- Log expenses with **natural-language chat messages**,
- **Read and parse rent bills from photos** (OCR),
- Run an algorithm that **minimizes circular debts**,
- Generate **dynamic VietQR codes** so debts can be settled to the exact đồng in one tap.

### 1.3 Why it is worth doing

- **Zero-friction** — no new app to install; it lives where roommates already talk.
- **Real, recurring need** — every shared household faces this monthly.
- **AI-leveraged** — natural-language parsing and image-based bill extraction remove the biggest barriers to tracking expenses.
- **Scope-fit** — a focused feature set well within the 6–50 screen/function range.

---

## 2. Target Users and Environments

### 2.1 Target users

- **Students and young professionals living in shared rentals** (2–5 people per room/apartment).
- **The group leader / "room treasurer"** — the person who collects money and pays the landlord each month.
- **Landlords / property managers** (indirectly) — their invoices are the input the bot parses.

### 2.2 Environments

- **Primary platform (MVP): Telegram** — free Bot API, group-message access (Group Privacy disabled), and a smooth **Telegram Mini App** (inline webview, no app review).
- **Secondary platform: Zalo** — best reach for mass Vietnamese users via **Zalo Mini App**; stricter review for business accounts (OA) and user-data access.
- **Devices / OS:** mobile-first (**Android & iOS**), with desktop support through the native Telegram/Zalo desktop apps.
- **Web:** the Mini App is a web application embedded in the chat client — no separate install.
- **Payment:** domestic bank apps via the **VietQR / NAPAS** standard.

---

## 3. Key Features

1. **Natural-Language Quick Split** — Parses everyday group-chat messages (e.g., *"bought a water jug 50k split 3"*, *"fronted WiFi 220k"*), extracts the amount, payer, and beneficiaries, and logs the entry to the group ledger.
2. **Rent Bill OCR & Parser** — Users send a photo of the rent invoice to the group; Computer Vision/OCR extracts base rent, electricity readings (new − old × unit price), water volume, and surcharges, then splits them automatically.
3. **Debt Simplification Engine** — Solves the **Minimum Cash Flow** problem on the group's debt graph, eliminating circular debts to minimize the number of transfers between members.
4. **One-tap VietQR Dynamic Settlement** — Generates a **VietQR (NAPAS)** code per person with the exact amount and a standardized transfer note pre-filled; a **"Received"** button auto-clears the debt.
5. **Electricity & Water Meter Scanner** — Photograph mechanical or digital meters in the hallway; the bot recognizes the digits to cross-check against the landlord's invoice readings.
6. **Roommate Chore & Trash Scheduler** — Rotating duty roster for cleaning and trash; auto-tags the person on duty with a check-in button to confirm completion.
7. **Shared Room Fund Ledger** — Manages a fixed monthly room fund and automatically deducts from it when a member buys shared supplies.
8. **Polite Nudge & Meme Reminder** — After the 24-hour settlement cutoff, sends funny images/memes to remind members who have not paid, easing the awkwardness of asking for money.
9. **Monthly Expense Breakdown** — Visual end-of-month summary of electricity usage, shared food costs, and average living cost per person.
10. **Move-in Asset & Deposit Checklist** — Stores photos of the room's initial condition on move-in (AC remote, meter, wall cracks) to support the deposit check on move-out.

---

## 4. Use Cases

### Use Case 1 — Daily groceries and small purchases
- **Behavior:** Member A buys spices and laundry detergent for 120,000đ and messages the group: *"A bought detergent 120k, split for the whole room."*
- **Result:** The bot confirms, adds the entry to the room ledger, and splits 40,000đ per person.

### Use Case 2 — End-of-month rent payment
- **Behavior:** The room leader receives the rent notice from the landlord and sends a photo straight into the group chat.
- **Result:** The bot scans the image, extracts the itemized list (room, electricity, water, garbage), offsets each member's advances during the month, and outputs a summary: *Member B owes A 1,850,000đ* (with a VietQR image), *Member C owes A 1,920,000đ* (with a VietQR image).

### Use Case 3 — One-tap debt settlement
- **Behavior:** Member B opens their banking app, scans the VietQR generated by the bot in the group (amount and note pre-filled), and transfers.
- **Result:** The leader taps **"Received"**, and the bot automatically resets B's outstanding balance to 0.

---

## 5. Interview Evidence

> **Requirement:** Interview **at least 5 potential users/customers** and provide evidence for each: an **audio/video recording**, the **notes taken**, and **information about the interviewee** (background, occupation, interests, and other characteristics).

### 5.1 Interviewee profiles

| # | Name | Age | Occupation | Background / interests | Other characteristics | Date | Interviewer(s) |
|---|---|---|---|---|---|---|---|
| 1 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 2 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 4 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 5 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 5.2 Evidence files

> Files are stored in `pa/PA0/interviews/`. Naming: `interview-<n>-<name>.<ext>`.
> Interview questions: `pa/PA0/interviews/interview-questions.md`.
> **Online survey:** https://docs.google.com/forms/d/e/1FAIpQLScM5yP4aliMYLqN7aDY88b7SqNZ4aVUaF5TYSiHEhPrL0CenA/viewform
> **Recorded answers (Google Sheet):** https://docs.google.com/spreadsheets/d/1X-GWnKz42I-MgZ_UnvzSq1lkeU0NDc5DSjurFPXTJ1M/edit?usp=sharing

| # | Audio/video recording | Notes | Key findings |
|---|---|---|---|
| 1 | `interview-1-TBD.mp3` / `.mp4` | `interview-1-TBD.md` | TBD |
| 2 | `interview-2-TBD.mp3` / `.mp4` | `interview-2-TBD.md` | TBD |
| 3 | `interview-3-TBD.mp3` / `.mp4` | `interview-3-TBD.md` | TBD |
| 4 | `interview-4-TBD.mp3` / `.mp4` | `interview-4-TBD.md` | TBD |
| 5 | `interview-5-TBD.mp3` / `.mp4` | `interview-5-TBD.md` | TBD |

### 5.3 Summary of findings

- **Confirmed problems:** (e.g., fragmented micro-debts, painful rent reconciliation, awkward reminders)
- **New ideas discovered:** (e.g., privacy concern about the bot reading chat, need for extra cost categories like garbage/bike fees)
- **Platform preference:** (e.g., mostly Zalo, some Telegram)
- **Willingness to pay:** (e.g., a few tens of thousands of đồng per room/month)

---

## 6. Platform & Technical Notes

### 6.1 Deployment platform (Telegram vs Zalo)
- **Telegram** — Recommended for the first technical MVP: the Bot API is fully free, supports reading group messages (Group Privacy disabled), and offers a smooth Telegram Mini App (inline webview, no complex review process).
- **Zalo** — Excellent fit for the mass Vietnamese market via the Zalo Mini App model, but has stricter review for business accounts (OA) and user-data access.

### 6.2 Core tech stack
- **Backend & Webhook:** Python (FastAPI) or Node.js (Express) to process bot event webhooks.
- **Core algorithm:** Greedy / Disjoint-Set / Flow Network for the Minimum Cash Flow (debt-minimization) problem.
- **Image processing:** Tesseract OCR, Google Vision API, or Viettel Cloud OCR to extract digits from thermal-printed and handwritten Vietnamese invoices.
- **Payment integration:** A library that generates **EMVCo-compliant VietQR / NAPAS** strings encoding domestic bank info (BIN code, account number, amount, message).
