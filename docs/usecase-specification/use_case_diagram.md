# TroMate — Use-Case Specification Document

**Date:** October 26, 2026  
**Authors:** TroMate Team (Group 06)  

---

## 1. Introduction

This document provides a detailed specification of the Use-Case Model for **TroMate** — an Intelligent Shared Expense Management and Room Debt Settlement System. It defines system actors, primary use cases, parsing scenarios, and a PlantUML diagram. The agreed scope baseline is the [PA1 Vision Small Project document, version 1.0](../../pa/PA1-Group06/vision/rup_vision_sp.docx); remaining alignment issues are recorded in the [diagram review](../usecase-specification/usecase-diagram-summary.md).

**Current scope decision:** UC06 (Auto-Accept Expense) is excluded from the current model and specification while the behavior remains under research. No final adoption decision has been made. Existing UC IDs are preserved; unapproved expenses remain `PENDING` under the current baseline.

---

## 2. Actors & System Boundaries

### 2.1 Primary Actors (Users)

* **Active Shared-Cost Contributor (Room Member):** A room member sharing living expenses in an apartment (2–5 members). They interact with the system via Telegram group chats or Telegram Mini App to log purchases, confirm/reject pending debt splits, settle net balance debts, and view personal ledgers.
* **Room Financial Lead / Representative:** A specialized Room Member responsible for roommate onboarding, handling physical utility meter photos, landlord invoices, and inspecting consolidated room debt graphs. *(Inherits all capabilities from Room Member via Generalization)*.

### 2.2 Secondary / External Actors (System & Engines)

* **System (Background Engine & Telegram Bot):** An automated background actor executing real-time processing tasks. This includes executing NLP/OCR parsing pipelines, solving the Minimum Cash Flow Problem on directed debt graphs, and firing scheduled 24h/48h debt reminders.

---

## 3. Detailed Use-Case Specifications

### UC01: Log Expense via Natural Language Text
* **Primary Actor:** Active Shared-Cost Contributor (Room Member)
* **Goal:** Log daily shared expenses directly inside the Telegram group chat using unstructured natural Vietnamese messages without manual form entry.
* **Preconditions:** The user is a verified member of the Telegram group chat bound to an active TroMate room workspace.
* **Basic Flow:**
  1. User posts a natural language text message in the Telegram group chat specifying a purchase or debt.
  2. System triggers **UC03b: Parse Intent & Split Logic (LLM/NLP Engine)** to extract items, total amounts, payer, payees, and splitting logic.
  3. System creates a `PENDING` transaction state and broadcasts an interactive inline poll `[Agree] [Reject] [Edit]` to the group.
  4. System dynamically updates the room debt graph.
* **Detailed Parsing Scenarios (Sub-flows):**
  * **Scenario A (Direct 1-to-1 Debt Mention):** 
    * *Input Example:* `"Lan nợ tôi 20k ăn sáng nha, bánh mì đó"`
    * *System Behavior:* Identifies the sender as the creditor (Payer), "Lan" as the sole debtor (Payee), amount = 20,000 VND, description = "bánh mì", and logs an explicit 1-to-1 debt of 20k from Lan to the sender.
  * **Scenario B (Equal Group Split - All Members):** 
    * *Input Example:* `"Tiền lẩu hồi trưa 200k nha ae"`
    * *System Behavior:* Identifies sender as Payer (200,000 VND), detects target group `"ae"` as all `num_members` in the room. Calculates individual split = `200,000 / num_members`. Logs corresponding debts for each roommate to the sender.
  * **Scenario C (Custom Named Split / Partial Group):** 
    * *Input Example:* `"Hùng ăn 30k, Nam 20k tiền nước ngọt"`
    * *System Behavior:* Parses multi-person specific amounts, assigning explicit debt balances to Hùng (30k) and Nam (20k) payable to the message sender.

---

### UC02: Log Expense via Receipt Photo & Text Context
* **Primary Actor:** Active Shared-Cost Contributor (Room Member)
* **Goal:** Extract itemized purchases, total costs, and complex item assignments from a photo of a physical receipt or supermarket invoice combined with optional natural text instructions.
* **Preconditions:** The uploaded photo must be a readable receipt/invoice.
* **Basic Flow:**
  1. User uploads a receipt image into the Telegram group chat, optionally accompanied by a text caption describing item allocation.
  2. System triggers **UC03a: Vision OCR Data Extraction** to extract raw text and line items from the image.
  3. **UC03a** forwards the extracted text stream along with the user text caption to **UC03b: Parse Intent & Split Logic (LLM/NLP Engine)** to process item assignments and split amounts.
  4. System creates a `PENDING` transaction state and broadcasts an interactive poll `[Agree] [Reject] [Edit]` to the group.
  5. System dynamically updates the room debt graph.
* **Detailed Parsing Scenarios (Sub-flows):**
  * **Scenario A (Full Receipt Equal Split):** 
    * *Input Example:* [Image of Supermarket Receipt: 150,000 VND] + Text: `"Tiền lẩu hôm qua nha ae"`
    * *System Behavior:* Vision OCR (UC03a) extracts total amount (150,000 VND). Text context `"ae"` processed by LLM/NLP (UC03b) directs the system to divide 150,000 VND equally among all room members (`150,000 / num_members`).
  * **Scenario B (Itemized Individual & Shared Allocation):** 
    * *Input Example:* [Image of Food Receipt containing: Spicy Beef Noodle x2 110k (55k/bowl), Seafood Noodle 60k, French Fries 30k, Tokbokki 40k] + Text: `"tôi với Hùng ăn mì cay bò mỹ, Minh ăn hải sản nha"`
    * *System Behavior:* 
      1. Vision OCR (UC03a) extracts itemized list and prices.
      2. LLM/NLP Engine (UC03b) parses caption and deterministically assigns specific named items to individuals: Sender ("tôi") = 55k (1x Spicy Beef Noodle), Hùng = 55k (1x Spicy Beef Noodle), Minh = 60k (Seafood Noodle).
      3. System identifies unassigned/shared side items (French Fries 30k + Tokbokki 40k = 70k) and splits them equally among all participants in the meal (Sender, Hùng, Minh).
      4. Calculates final individual totals (Personal Item Cost + Shared Split Portion) and logs debt records accordingly for each participant.

---

### UC03a: Vision OCR Data Extraction (Backend Service)
* **Primary Actor:** System (Background Engine)
* **Goal:** Extract raw text lines, itemized bill tables, and numeric digits from images of receipts, invoices, or utility meters.
* **Trigger:** Invoked automatically (`<<include>>`) by UC02 and UC04.
* **Basic Flow:**
  1. Receives image binary payload from Telegram Webhook (UC02 or UC04).
  2. Executes Optical Character Recognition (OCR) to detect text boxes, numeric index values, and itemized lines.
  3. Formats extracted visual text and forwards payload to **UC03b** for contextual semantic parsing.

---

### UC03b: Parse Intent & Split Logic via LLM/NLP Engine (Backend Service)
* **Primary Actor:** System (Background Engine)
* **Goal:** Serve as the core intent and financial parsing engine, normalizing Vietnamese currency units and mapping human pronouns to database user IDs.
* **Trigger:** Invoked directly by UC01 (`<<include>>`) or forwarded from UC03a (`<<include>>`).
* **Basic Flow:**
  1. Receive raw text payload (from UC01) or OCR-extracted text stream (from UC03a).
  2. **Text Normalization Engine:** Normalizes currency slang (`k`, `tr`, `củ`) into standard VND values.
  3. **Entity & Intent Mapping:** Maps member nicknames and self-referential pronouns (`"tôi"`, `"mình"`) to Telegram User IDs.
  4. Returns structured JSON payload containing: `payer_id`, `payee_list`, `itemized_breakdown`, `total_amount`, and `individual_debts`.

---

### UC04: Scan Utility Meter & Landlord Invoice
* **Primary Actor:** Room Financial Lead / Representative
* **Goal:** Scan hallway electricity/water index digits or handwritten landlord utility bills to automate monthly utility distribution.
* **Basic Flow:** Lead uploads photo of meter/invoice -> System invokes **UC03a (Vision OCR)** -> Text stream passed to **UC03b (LLM/NLP)** -> System calculates delta consumption -> Computes individual utility debts.

---

### UC05: Confirm / Reject / Edit Pending Expense
* **Primary Actor:** Active Shared-Cost Contributor (Room Member)
* **Goal:** Review and vote on a `PENDING` expense logged by a roommate to maintain 100% mathematical auditability.
* **Basic Flow:** Roommate clicks `[Agree]`, `[Reject]`, or `[Edit]` on Telegram inline poll -> Redis distributed lock updates transaction state -> Triggers net balance update.

---

### UC07: Simplify Group Debts (Real-Time Minimal Cash Flow)
* **Primary Actor:** System (Background Engine)
* **Goal:** Recalculate group Net Balances and solve the Minimum Cash Flow Problem on directed debt graph $G=(V,E)$ in real-time (< 0.5s latency).
* **Basic Flow:** Invoked upon transaction confirmation -> Computes net balance vector -> Reduces circular debts ($A \rightarrow B \rightarrow C \rightarrow A$) down to maximum $N-1$ directed transactions.

---

### UC08: Settle Net Debt
* **Primary Actor:** Active Shared-Cost Contributor (Room Member)
* **Goal:** Initiate payment to settle personal net balance debt.
* **Basic Flow:** User requests payment -> System triggers **UC09: Generate Dynamic VietQR** -> User completes transfer via banking app -> Uploads payment proof image -> OCR verifies proof (UC03a) -> Debt resolved.

---

### UC09: Generate Dynamic VietQR & Settlement Confirmation
* **Primary Actor:** System (Background Engine)
* **Goal:** Generate EMVCo-compliant VietQR codes and deep-links pre-filled with recipient bank account, exact net amount, and standardized transfer memo.

---

### UC10: Send Scheduled Debt Reminders
* **Primary Actor:** System (Background Engine)
* **Goal:** Periodically tag debtors in group chat after 24h/48h with polite reminders and payment links without personal confrontation.

---

### UC11: View Personal Ledger & Webview Dashboard
* **Primary Actor:** Active Shared-Cost Contributor (Room Member)
* **Goal:** Open Telegram Mini App to view personal net balances, "my related expenses" filtered views, room category charts, and 90-day historical ledgers.

---

## 4. Use-Case Diagram (PlantUML)

Editable source: [use_case_diagram.puml](use_case_diagram.puml).

![TroMate Use-Case Diagram](https://uml.planttext.com/plantuml/png/ZLNRJkCm47tFLupwmC93WHOG9KA8qW92Qjbk2-mB4feaqyHBObUsM-XU_dt7kNHf2MZpKFaovypnyNXwRYngEyzIkDDgY9QUxWqzzP1_-W9ZZPcNqjI2LQ15d5Y8XARG2YKzyopa33a2PXW-OqmJkqm9t3RAEAKt0HXQfOljHAMfUl6yV0aQNUPQ44mIr1GrUyhOHzbJqceHp3cW0MXWI5b0kaACbShWIaYKeS0K1eHH7kK6LSnaQInbZtBxWfN5Mirb19So5f9syjXYt_CAPZZztMmMU6-b7Xgb8MKmN3WMrCi6_F8yuAyyDJGkNsSa3S50nPmYXYqOeJPkLEHq22Y_kQ6GpON6VM-_vJi8LF25GBX5EzTygZjwjRbI5rOBRhy7ZoaaCRCmIfHL5RfTYpxqOHAYX7ihKc6NRB5b7xPWW39AbOxWHYwK2AbYEVHgQGxGXmTXk1hWQsyCVRJ8Ygp6l48gy07MWmC_DueucILfEVranchSkKG8suF1SEzsCDfPqGGvpPyDzxbQfa9dw3B2IFFHGvKwBkikRuXXyiaL7FbGuc6F_Vl1jy-3ouXLZ4X6-HqM3bSgZcf5z2cmC14Pwv-AiD324iZQb39tjiyhuTYlm4kuvdATWICqi3qKKcHS3_mW4xZYXxDouxYMgEENIU6MR4vInNTguqzyk2P9sbdLNqhCsFW7GVRRcEM_TRQYEQcZQUsxjFp69c52qJobA4_DXcP2HgHDYMxjrvetuWWbyxSSnNaPVgTW8UY52yeaWK8TVM1Sg-NgZmF_YwBGq2eri8elN2zihrv2D-yRNMCKDnLtNbFrXcRph7Y4w_FsnlneOzvPdtDMpbPOdOgVHO6uZhEUCryf6GuTekezcsqCkjmTin9L1fKuVcqR2y76ml7wd6-5Czt8C9r7n7UM5hI9c1cOiYlhpSnpPi3kRaaDFfoUYW9xTkOsswjDVBzv-Dachtt4wwpuzvXAhGxJgI0dcuXpBaZ-N_F-0W00)
---

## 5. Summary Matrix & Definition of Done Mapping

| UC ID | Name | Target Actor | Primary Priority | Vision Feature Ref |
| :--- | :--- | :--- | :--- | :--- |
| **UC01** | Log Expense via Text | Room Member | High (MVP) | Feature 1 |
| **UC02** | Log Expense via Receipt Photo | Room Member | High (MVP) | Feature 2 |
|**UC03a**| Vision OCR Data Extraction| System Engine| High (MVP) | Feature 2, 3|
|**UC03b**| Parse Intent & Split Logic (LLM/NLP)| System Engine| High (MVP) | Feature 1, 2|
| **UC04** | Scan Meter & Landlord Invoice | Room Lead | Medium (MVP) | Feature 3 |
| **UC05** | Confirm/Reject Pending Expense | Room Member | High (MVP) | Feature 6 |
  | **UC07** | Simplify Group Debts | System Engine | High (MVP) | Feature 4 |
| **UC08** | Settle Net Debt | Room Member | High (MVP) | Feature 5 |
| **UC09** | Generate Dynamic VietQR | System Engine | High (MVP) | Feature 5 |
| **UC10** | Send Scheduled Debt Reminders | System Engine | High (MVP) | Feature 7 |
| **UC11** | View Personal Ledger & Dashboard | Room Member | High (MVP) | Feature 8, 12 |

---
*End of Use-Case Specification Document.*
