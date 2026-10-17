# PROJECT DECISION RECORD & DETAILED FEATURE SPECIFICATION

---

## PART I: MVP SCOPE & TARGET USERS

### 1. Target Users & Key Pain Points

#### Primary Target Users
* **University Students & Young Professionals (Ages 18–26):** Sharing rented apartments or rooms (2–5 members per room) in urban areas (e.g., Ho Chi Minh City, Hanoi).
* **Room Leads / Financial Representatives:** The member designated to collect money, manage communal expenses, and make bulk payments to the landlord.

#### Key Pain Points
1. **High Friction in Daily Shared Logging (Core Pain Point):** Logging small or frequent shared purchases (groceries, fan, wifi, water) currently requires manual data entry into Excel/Splitwise after paying. This friction causes hesitation, annoyance, and forgotten expenses. **TroMate completely eliminates this final manual step.**
2. **Social Discomfort in Requesting Money (Core Pain Point):** Asking roommates directly to settle debts causes awkwardness and embarrassment. **TroMate automates polite debt reminders, acting as a neutral third party.**
3. **Complex Rent & Utility Settlement:** Converting landlord invoices (rent, electricity, water) and deducting prior individual prepayments into clear individual balances takes time and causes calculation errors.
4. **Multi-party Debt Friction:** Circular debts ($A \to B \to C \to A$) cause unnecessary transactions and confusion.

---

### 2. Feature Prioritization & Scope Classification

| Feature Name | Scope Classification | Priority | Value / Effort Rationale |
| :--- | :--- | :--- | :--- |
| **Natural Language Expense Parsing (Text)** | **MVP** | High | Core value proposition; enables instant text-based expense logging in group chat. |
| **Receipt & Rent Bill OCR Parser (Photo)** | **MVP** | High | **Critical for zero-friction experience.** User snaps a photo of any receipt/bill (fan, groceries, rent) $\rightarrow$ Bot auto-extracts amount & items $\rightarrow$ Eliminates manual Excel logging. |
| **Electricity & Water Meter Scanner** | **MVP** | Medium | Allows users to snap hallway meter photos to auto-extract index numbers directly into the chat. |
| **Dynamic VietQR Settlement Generation** | **MVP** | High | Generates EMVCo VietQR with pre-filled exact amount and transfer memo for 1-tap settlement. |
| **Debt Simplification Engine (Minimal Cash Flow)** | **MVP** | High | Essential to reduce multi-member payment friction to minimum necessary transactions. |
| **Confirmation Protocol & State Machine** | **MVP** | High | High user value; prevents unauthorized debt logging and handles pending/conflict states reliably. |
| **Simple Settlement Flow & Manual Confirmation** | **MVP** | High | Crucial for completing the transaction lifecycle via interactive buttons. |
| **Group Expense Summary & Individual Balances** | **MVP** | High | Primary visibility deliverable; provides real-time net balances for all members. |
| **Polite Automated Debt Reminder** | **MVP** *(Promoted)* | High | **Critical for removing social awkwardness.** Automated, scheduled polite messages tag unsettled debtors so members don't have to ask manually. |
| **Telegram Mini App / Web UI (Read-Only/Admin)** | **MVP** | Medium | Provides a structured dashboard for members who prefer a visual interface over chat commands. |
| **Usage Anomaly Detector (Utility Spikes)** | **Later Release** | Low | Requires historical consumption data across multiple months; deferred to post-MVP. |
| **Monthly Expense Breakdown (Analytics/Infographics)** | **Later Release** | Low | Periodic analytics report for spending habits; deferred to post-MVP iterations. |
| **Meme-based / Custom Image Reminder Generator** | **Later Release** | Low | Image rendering/meme generator for reminders; deferred to post-MVP for visual polish. |
| **Shared Room Fund Ledger** | **Out of Scope** | N/A | **Redundant.** Pre-collected room funds are mathematically represented as standard directional debts within the Minimal Cash Flow engine. |
| **Chore & Trash Scheduler** | **Out of Scope** | N/A | Deviates from the core financial/expense management scope. |
| **Move-in Asset & Deposit Checklist** | **Out of Scope** | N/A | Low frequency of use; adds non-financial scope creep to PA1 deliverables. |

---

### 3. Scope Rationale, Technical & Platform Assumptions

#### Rationale
The MVP scope completely covers **zero-friction logging, 1-tap settlement, and automated polite debt reminders**. By promoting the text-based Polite Reminder to MVP, TroMate removes both operational friction (data entry) and social friction (awkward debt requests). Non-essential analytics charts and dynamic meme rendering remain deferred to post-MVP.

#### Technical & Platform Assumptions
1. **Primary Platform:** **Telegram Bot API + Telegram Mini App (Webview)**. Selected for robust bot API, free webhook infrastructure, and instant Mini App deployment.
2. **OCR Engine:** Integration with Vision OCR APIs (e.g., Google Cloud Vision / Tesseract / Viettel OCR) to parse receipt totals, line items, and meter readings.
3. **Task Scheduler:** Background worker (e.g., Celery / Redis Queue / APScheduler) to handle timed trigger jobs for debt reminders (e.g., 24h / 48h post-settlement calculation).
4. **Backend & State Management:** **FastAPI / Node.js** backed by **Redis** for transient state locks (`PENDING`, `CONFLICTED`, `EXPIRED`) and **PostgreSQL** for immutable ledger persistence.
5. **Settlement Standard:** VietQR dynamic payload generation adhering to EMVCo / Napas standards.

---

## PART II: DETAILED FUNCTIONAL SPECIFICATIONS

### 1. Natural Language & Multi-modal Expense Parsing (MVP)
* **Description:** Parses free-form chat messages and accompanying receipt photos to extract transaction details and calculate splits with zero manual entry.
* **Functional Requirements:**
  * **Text Processing:** Extracts amount, payer (`payer`), payees (`payees`), and item descriptions from natural language chat inputs (e.g., *"mua bình nước 50k chia 3"*). Defaults to equal split among all room members if not specified.
  * **Receipt & Bill OCR Parsing (Zero-Manual-Entry Flow):** User uploads a photo of a receipt (buying a fan, supermarket bill, rent invoice) $\rightarrow$ OCR extracts total amount, date, and line items $\rightarrow$ Bot automatically drafts a debt split request.
  * **Multi-modal Combination (Text + Image):** Accepts image + text adjustments in one action (e.g., photo of a 500k restaurant bill + text *"chỉ có A và B ăn bill này"* $\rightarrow$ OCR extracts 500k, split strictly between A and B).
  * **Currency Normalization:** Normalizes informal Vietnamese currency tokens (`k`, `kđ`, `tr`, `xị`, `củ`, `ngàn`) into standard integer values (`VND`).

---

### 2. Meter Scanner & Smart Rent Parser (MVP)
* **Description:** Reads electricity/water meters from photos and parses landlord rent invoices.
* **Functional Requirements:**
  * **Meter Image OCR:** Reads digit sequences from photos of physical electricity/water meters to log current index numbers.
  * **Rent Invoice Breakdown:** Extracts fixed rent, electricity (new index - old index $\times$ unit price), water, and extra fees (trash, wifi) to compute individual shares automatically.

---

### 3. Debt Simplification Engine (MVP)
* **Description:** Minimizes circular and cross-debts across all room members to reduce settlement transactions.
* **Functional Requirements:**
  * Solves the **Minimum Cash Flow Problem** on a directed graph $G = (V, E)$, where $V$ represents room members and $E$ represents directional debts.
  * Eliminates closed debt cycles (e.g., $A \to B \to C \to A$) to minimize the total number of bank transactions required.
  * Computes net balances per member and outputs the minimal set of peer-to-peer transfers.

---

### 4. Dynamic VietQR Settlement & Settlement Flow (MVP)
* **Description:** Generates 1-tap payment QR codes and handles debt clearance confirmation.
* **Functional Requirements:**
  * **Dynamic VietQR Generation:** Generates EMVCo-compliant VietQR codes with pre-filled Bank BIN, Account Number, Exact Settlement Amount, and standardized transfer memo (e.g., `TROMATE P302 A TRA B T10`).
  * **Settlement Confirmation:** Provides a `[Confirm Paid]` button for debtors and a `[Confirm Received]` button for creditors to clear obligations and update net balances to zero.

---

### 5. Polite Automated Debt Reminder (MVP)
* **Description:** Automated, scheduled debt reminders sent directly to group chats to remove personal awkwardness.
* **Functional Requirements:**
  * **Scheduled Trigger:** Automatically scans active balances 24 hours (and/or 48 hours) after a bill settlement calculation.
  * **Polite Messaging Template:** Constructs friendly, neutral reminder messages in the chat, tagging unsettled debtors (e.g., *"Cảnh báo nhẹ: @nam và @hung còn khoản 150k chưa tất toán với @an nhé. Bấm [Thanh toán VietQR] để xóa nợ 1-chạm nha!"*).
  * **Actionable Prompt:** Includes an inline button `[Thanh toán VietQR]` directly inside the reminder message for immediate 1-tap payment.

---

### 6. Interaction Protocol, State Machine & Concurrency Control (MVP)
* **Description:** Manages transaction validation, conflict resolution, and concurrent message handling in group chats.
* **Functional Requirements:**
  * **Confirmation Protocol:**
    1. **Pending State:** Transactions created from text or OCR are initially set to `PENDING`.
    2. **Broadcast Poll:** The bot posts a confirmation card with action buttons: `[✅ Agree]`, `[❌ Reject]`, `[✏️ Edit Amount]`.
    3. **Explicit Approval & Pending Retention:** Transactions remain in the `PENDING` state until explicitly confirmed by involved members. If no action or confirmation is received within a timeframe, the transaction stays in `PENDING` status rather than being auto-committed to the official ledger.
  * **Conflict & Rollback Handling:** If rejected, the requester can select `Edit Request`, `Cancel Request`, or delete/edit the original message (detected via Telegram webhooks) to cancel or modify the pending transaction.
  * **Concurrency Control:** Redis key-value locks per group (`Group_State_Lock`) prevent race conditions from simultaneous messages.

---

### 7. Group Summary & Telegram Mini App (MVP)
* **Description:** Provides quick-view text summaries in chat and a full Webview interface.
* **Functional Requirements:**
  * **Chat Summary:** Displays real-time net balances and minimal settlement actions upon `/balance` command.
  * **Telegram Mini App:** In-app Webview showing interactive balance sheets, transaction history, and room configuration (member list, bank details).

---

### 8. Post-MVP & Deferred Features (Later Release)
* **Usage Anomaly Detector:** Automated alerts for consumption spikes exceeding $1.5\times$ historical 3-month averages.
* **Meme-based / Custom Image Reminder Generator:** Custom meme generation overlay for debt reminders.
* **Monthly Expense Breakdown:** End-of-month visual analytics reports, charts, and spending trend infographics.

---

## PART III: KEY USER FLOWS, RISKS & DELIVERABLES

### Core User Flow (Zero-Friction Logging & Polite Reminder)
1. **Log Expense (Text or Photo):** Member $A$ buys a fan for 1,000k, takes a photo of the receipt, and sends it to the Telegram group with the text `"chia 3"`.
2. **OCR Parsing & Pending State:** Bot extracts `1,000,000 VND` from the receipt photo, sets state to `PENDING`, and posts a confirmation card (`[Agree]`, `[Reject]`, `[Edit]`).
3. **State Commit:** Upon explicit approval by involved members, the transaction commits to PostgreSQL. Unconfirmed transactions remain in PENDING state and do not affect official net balances.
4. **Simplify & Settle:** Members request net balances. Debt Simplification Engine outputs: $B \to A: 333.3\text{k}$, $C \to A: 333.3\text{k}$.
5. **Polite Reminder Trigger (After 24h):** If $B$ hasn't paid after 24 hours, Bot automatically sends a friendly tag: *"@B ơi, nhớ chuyển 333.3k cho @A nha!"* kèm nút `[Thanh toán VietQR]`.
6. **1-Tap VietQR Settlement:** Member $B$ taps `[Thanh toán VietQR]`, scans the pre-filled QR code, and completes payment. $A$ taps `[Confirm Received]`, updating net balance to zero.

### Major Risks & Mitigation
* **OCR Accuracy on Low-Quality Receipts:** Poor lighting or crumpled receipts causing incorrect OCR extraction.
  * *Mitigation:* Always display extracted amount in the `PENDING` confirmation card, allowing members to tap `[✏️ Edit Amount]` to fix typos in 2 seconds.
* **Concurrency / Race Conditions:** Multiple members sending expense logs simultaneously.
  * *Mitigation:* Isolate state locks per Telegram group ID using Redis key-value expiration ($TTL = 300\text{s}$).

---

## PART IV: TEAM DECISION RECORD & LINK

* **Decision Status:** Approved & Agreed by Team
* **Target Release:** PA1 Vision Document, Project Plan, SRS & UI Prototype Baseline
* **Documentation Link:** `[Repository Documentation / docs/management/MVP_plan.md]`
