# FEATURE SPECIFICATION: TROMATE ENGINE

## 1. Natural Language & Multi-modal Expense Parsing
**Description:** Parses natural language chat messages, bill images, or a combination of both to extract transaction entities and log group debts.

* **In-Scope Features:**
  * **Text Processing:** Extracts amount, payer (`payer`), payees (`payees`), and item descriptions from free-form chat messages (e.g., *"mua bình nước 50k chia 3"*, *"ứng tiền wifi 220k"*). Defaults to equal split among all room members if not specified.
  * **Multi-modal Context Parsing (Text + Image):** Combines image context with text adjustments (e.g., sending a receipt image of 500k with text *"chỉ có A và B ăn bill này"* $\rightarrow$ total amount extracted via OCR, but split strictly between A and B).
* **Technical Enhancements & Edge Cases:**
  * **Entity Extraction Fallback:** When a message is ambiguous (e.g., *"mua đồ 100k"* missing payer or payee info), the bot prompts for clarification using interactive UI buttons (`Inline Keyboard`) instead of making assumptions.
  * **Currency & Unit Normalization:** Automatically normalizes Vietnamese informal currency tokens (`k`, `kđ`, `tr`, `xị`, `củ`, `ngàn`) into standard integer values (`VND`).

---

## 2. Smart Rent Bill OCR, Meter Scanner & Anomaly Detector
**Description:** Extracts information from rent bills, audits physical electricity/water meters, and flags abnormal consumption spikes.

* **In-Scope Features:**
  * **Rent Bill OCR & Parser:** Extracts fixed rent, electricity usage (new index - old index $\times$ unit price), water usage, and extra fees (trash, wifi, parking) to calculate split ratios.
  * **Electricity & Water Meter Scanner:** Reads indices from photos of hallway meters (analog or digital) to cross-check against landlord-provided invoices.
  * **Usage Anomaly Detector:** Calculates baseline consumption metrics ($X$ liters of water/person/month, $Y$ kWh electricity/person/month based on 3-month historical averages). Sends an alert if current usage spikes beyond threshold limits (e.g., $>\!1.5 \times \text{average}$), flagging issues like water leaks or electrical faults.

---

## 3. Debt Simplification Engine
**Description:** Minimizes circular and cross-debts across all room members.

* **In-Scope Features:**
  * Solves the **Minimum Cash Flow Problem** on a directed graph $G = (V, E)$, where $V$ represents room members and $E$ represents directional debts.
  * Eliminates closed debt cycles (e.g., $A \to B \to C \to A$) to minimize the total number of bank transactions required.

---

## 4. One-Tap VietQR Dynamic Settlement
**Description:** Generates dynamic VietQR codes for instant debt settlement and automatic ledger updates.

* **In-Scope Features:**
  * Generates EMVCo-compliant VietQR codes (NAPAS standard) for each settlement transaction.
  * Pre-fills Bank BIN, Account Number, Exact Settlement Amount, and standardized transfer memo (e.g., `TROMATE P302 A TRA B T10`).
  * Provides a `[✅ Confirm Received]` button for the payee to clear the debt in the group chat upon receiving payment.

---

## 5. Polite Nudge & Meme Reminder
**Description:** Automated debt reminders featuring humorous memes.

* **In-Scope Features:**
  * Automatically mentions unsettled members with random meme images after 24 hours of bill settlement.
  * Relieves social tension around requesting money through humorous and polite automated workflows.

---

## 6. Monthly Expense Breakdown
**Description:** Generates periodic room financial reports.

* **In-Scope Features:**
  * Automatically generates visual reports (Infographics / Cards) at the end of each month detailing electricity/water consumption, total communal meal costs, and average cost per person.
  * Analyzes spending trends compared to preceding months.

---

## 7. Interaction Protocol, State Machine & Concurrency Control
*Deep-dive technical handling for group chat interactions, state transitions, and concurrency.*

### 7.1. Confirmation Protocol
To prevent incorrect or unagreed debt logging:
1. **Pending State:** Upon parsing an expense message, the transaction is created in a `PENDING` state rather than written directly to the primary database ledger.
2. **Broadcast Poll:** The bot posts a confirmation message with interactive buttons:
   * `[✅ Agree]` / `[❌ Reject]` / `[✏️ Edit Amount]`
3. **Timeout & Auto-Commit:**
   * Configurable confirmation window (Default: **60 seconds**).
   * If no involved member clicks `[❌ Reject]` within 60 seconds, the transaction automatically commits to the database ledger.
   * If an involved member clicks `[❌ Reject]`, the state transitions to `CONFLICTED`, freezing the transaction.

### 7.2. Conflict & Rollback Handling
* **Scenario: Member A proposes 1000k split, Member D rejects:**
  * When D clicks `[❌ Reject]`, the bot updates the message UI to red: *"Transaction rejected by D"*.
  * Member A is presented with resolution options:
    * `Edit Request`: Adjust the amount (e.g., lower to 750k) $\rightarrow$ Triggers a new confirmation flow.
    * `Cancel Request`: Deletes the `PENDING` transaction and posts *"Debt request cancelled"*.
    * `Edit/Delete Original Message`: If A deletes or edits the original message in Telegram, the bot listens to `edited_message` / `deleted_message` webhooks and automatically cancels the matching `PENDING` transaction.

### 7.3. Concurrency & Memory Management
* **Race Conditions (Simultaneous Requests):**
  * *Example:* Member A submits a 1000k request (pending confirmation) while Member B simultaneously submits a separate 200k request.
* **Architectural Solution:**
  1. **Isolation via Redis Transaction Queue:** Each chat group maintains a `Group_State_Lock` stored in Redis memory.
  2. **Async Task Processing:** While A's request is `PENDING_CONFIRMATION`, B's request is accepted and queued.
  3. **Message Context Tracking:** Each `PENDING` transaction is bound to a Telegram `message_id`. The bot responds within the reply thread of each request, keeping confirmation contexts isolated.
  4. **In-Memory Session Expiration:** Unsettled transaction data lives in Redis with $TTL = 300\text{s}$. Unresolved conflicts automatically expire (`EXPIRED`).

---

## 8. Web App Interface (Telegram Mini App / External Web UI)
**Description:** A graphical interface supplementing chat interactions.

* **In-Scope Features:**
  * Embedded directly as a **Telegram Mini App** (In-app Webview) or accessible as a standalone Web App.
  * **Core Functionalities:**
    * View balance sheets and cash flow charts over time.
    * Browse transaction logs with date/payer filtering.
    * Edit/Delete past erroneous entries (Admin privilege).
    * Configure group settings: member list, default split ratios, and destination bank accounts.
Beta
0 / 0
used queries
1