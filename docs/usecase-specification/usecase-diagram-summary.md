# TroMate Use Case Diagram Review

## Source of truth for this review

The project consensus is [TroMate Vision (Small Project), version 1.0, dated 17 October 2026](../../pa/PA1-Group06/vision/rup_vision_sp.docx). Its **Product Features** table defines Features 1–10, the MVP and later scope, and the Free/TroMate Pro distinctions. The Vision cites the [project decision record](../management/MVP_plan.md) for detailed behavior; that record is used below only where the Vision is less specific. The [use-case diagram document](../analysis-and-design/use_case_diagram.md) is the artifact being reviewed. The older `docs/requirements/vision.md` is excluded from this assessment.

**Current scope decision:** UC06 is removed from the current model and specification while auto-accept remains under research. The remaining 11 use cases keep their existing IDs. The deliverable will be edited in Markdown; the user will convert it to DOCX after editing is complete.

## What this file is trying to do

Despite its filename, [use_case_diagram.md](../analysis-and-design/use_case_diagram.md) is trying to be more than a use-case diagram. It combines several artifacts:

1. **A use-case model**

   It identifies the main roles:

   - Room Member
   - Room Financial Lead
   - A background “System” actor

2. **A catalogue of system functionality**

   It defines **11 entries** (UC01, UC02, UC03a, UC03b, UC04, UC05, and UC07–UC11), covering:

   - Natural-language expense logging
   - Receipt and invoice OCR
   - NLP-based split calculation
   - Utility meter scanning
   - Expense approval
   - Debt simplification
   - VietQR settlement
   - Debt reminders
   - Ledger and dashboard viewing

3. **An initial use-case specification**

   For some use cases, it provides:

   - Primary actor
   - Goal
   - Preconditions
   - Basic flow
   - Example parsing scenarios

4. **A visual use-case diagram**

   It embeds a remotely generated PlantUML image and links the versioned [editable PlantUML source](../analysis-and-design/use_case_diagram.puml). Both now exclude UC06.

5. **A traceability summary**

   The final matrix assigns an MVP priority and a feature reference to each use case. The numbered feature definitions are in the PA1 Vision's Product Features table.

Its intended purpose is to identify TroMate's actors and capabilities, then provide a starting point for detailed user–system interaction flows.

## Is it enough as the basis for a use-case specification?

**Yes as a starting outline, but no as the sole or authoritative basis.**

It contains enough information to identify many of the important use cases and begin drafting them. However, it is not yet complete or consistent enough to convert directly into the current [Use-Case Specification Template](UseCase-Specification-Template.md). The [assignment requirements](requirement.md) call for a specification for every diagrammed use case, with preconditions, basic flow, alternative flows, and postconditions.

### Completeness compared with the template

| Required information | Current state |
|---|---|
| Use-case name | Present |
| Brief description/goal | Present for all cases |
| Actors | Present, but several are modeled incorrectly |
| Basic flow | Detailed for UC01/UC02/UC03a/UC03b; very short for UC04/UC05/UC07/UC08; absent for UC09–UC11 |
| Alternative flows | Mostly missing |
| Preconditions | Only properly stated for UC01 and UC02 |
| Postconditions | Missing from every use case |
| Exception/error flows | Missing |
| Use-case diagram | Remote rendered image with versioned editable source; local final image remains a plan task |
| Consistency with PA1 Vision and its referenced decision record | Settlement clearance, feature references, and Free/Pro scope need correction; auto-accept is deferred |
| Testable outcomes | Mostly insufficient |

UC09–UC11 are especially incomplete: they contain little more than a goal.

## Important problems to correct

### 1. Settlement clearance goes beyond the agreed behavior

UC08 says an uploaded payment screenshot is verified by OCR and then the debt is resolved:

> “Upload payment proof image → OCR verifies proof → Debt resolved.”

That appears in UC08 of the diagram document.

The PA1 Vision's **Feature 5** promises VietQR generation with the exact amount, recipient details, and transfer memo. It does not say that OCR can prove a bank transfer succeeded. Its referenced [decision record](../management/MVP_plan.md) specifies `[Confirm Paid]` by the debtor and `[Confirm Received]` by the creditor before clearing the obligation. The [e-wallet feasibility research](../ewallet.md) also recommends payment evidence followed by manual recipient confirmation.

UC08 should distinguish generating a QR, making or claiming a transfer, and the creditor confirming receipt. A screenshot can be supporting evidence; OCR reading it does not establish that the recipient received the funds. UC09's title mentions settlement confirmation, but its goal describes only QR generation; the confirmation actor and flow still need to be modeled. Whether a room lead may confirm for another creditor remains open.

### 2. Auto accept is deferred for research

UC06 and its auto-accept relationship have been removed from the current model by the user's scope decision. Research may inform a future adoption decision; it does not block the current specification.

The current baseline uses Feature 6's explicit pending confirmations. An expense with no response stays `PENDING`, as documented in UC05-AF04 of the [alternative-flows catalogue](alternative-flows-catalogue.md). The Vision's 300-second concurrency-lock TTL is an infrastructure constraint, not an expense-approval timeout.

### 3. The feature matrix still has an invalid reference

The PA1 Vision's Product Features table defines **Features 1–10**. The diagram's mappings for UC01–UC05 and UC07–UC10 broadly match that numbering. UC11 still cannot be traced as written:

- **UC11 → Features 8, 12:** Feature 12 does not exist. Feature 8 covers the group summary and Mini App; the category charts mentioned in UC11 belong to **Feature 10**, which is Post-MVP/TroMate Pro, not an unconditional MVP capability.

UC04 covers both meter scanning (**Feature 3**) and landlord invoice parsing (**Feature 2**), so its matrix entry should cite both. The invalid Feature 11 reference was removed with UC06. Correct the remaining entries during specification drafting.

### 4. Internal components are modeled as actors

The file treats “System (Background Engine & Telegram Bot)” as an actor and makes it the primary actor for OCR, NLP and debt simplification.

In UML use-case modeling, the system normally should not be an actor to itself. Actors should be entities outside the TroMate boundary, such as:

- Room Member
- Treasurer/Room Lead
- Telegram platform
- Bank application
- Possibly a scheduler/time actor
- External OCR or NLP provider, if it is truly external

OCR parsing, NLP parsing, QR generation and debt simplification are generally included system behaviors or subflows—not independent user-goal use cases with TroMate as their actor.

### 5. Important alternative and exception flows are missing

A formal specification needs behavior for cases such as:

- NLP cannot determine the payer, amount or beneficiaries.
- A nickname matches multiple members.
- The entered amount is invalid, zero or negative.
- The split produces a rounding remainder.
- OCR cannot read the image.
- OCR values are inconsistent.
- A duplicate Telegram message is received.
- A member rejects or edits an expense.
- Multiple members act on the same pending expense.
- A user lacks permission to edit or confirm.
- Bank details required for VietQR are missing.
- The creditor reports that payment was not received.
- The transferred amount does not match.
- A reminder is due after the debt has already been settled.

The [UI flow](../analysis-and-design/ui-flows.md) already sketches some missing behavior, such as asking for clarification when parsing is incomplete.

### 6. Some flows update financial data too early

UC01 and UC02 say the system creates a `PENDING` transaction and then immediately updates the debt graph. The PA1 Vision requires explicit `PENDING` confirmations and immutable, auditable ledger entries. Its referenced [decision record](../management/MVP_plan.md) states that unconfirmed transactions do **not** affect official net balances. The diagram document does not say whether its graph update is only a preview or an official balance change, so this needs clarification.

The specification should distinguish:

- Proposed expense
- Confirmed ledger entry
- Derived debt graph/net balances

### 7. Coverage and commercial scope need a clearer inventory

Compared with the PA1 Vision and its referenced decision record, the diagram document omits or under-specifies:

- Correcting OCR or parsing errors in the pending expense card.
- Explicit approval criteria: which involved members must approve, and what happens on rejection or no response.
- Manual confirmation that the creditor received a settlement.
- Room configuration and bank details shown in the Mini App.
- Room setup and member onboarding, mentioned under the room lead's responsibilities but absent as a use case.
- The Free tier's shared **10 OCR scans per month** quota and the Pro tier's unlimited scans.

Receipt OCR is explicitly MVP scope, so UC02 is appropriate. The Vision's Free tier retains transaction history for **30 days**, while Pro has unlimited history: UC11's unconditional **90-day** ledger claim does not match either tier. Category charts and monthly analytics are **Feature 10**, Post-MVP/TroMate Pro; they should not be described as unconditional UC11 MVP behavior. Usage anomaly detection is **Feature 9**, Post-MVP, and need not be added to the MVP diagram. The Vision also describes a room representative buying TroMate Pro; decide whether subscription purchase/upgrade needs a separate use case if the specification is intended to cover the full product rather than only MVP.

## Recommended use of this file

Treat it as a **use-case inventory and brainstorming document**, not as the final specification or single source of truth.

A sensible next step would be to validate the diagram's UC inventory against the PA1 Vision, then organize the user-goal use cases approximately as follows:

1. Set up or join a TroMate room.
2. Log an expense through natural-language text.
3. Review, edit, approve or reject a proposed expense.
4. Upload and review a rent invoice.
5. Scan and cross-check utility meters.
6. View balances and ledger, with history limited by tier.
7. Settle an obligation using VietQR.
8. Confirm receipt of a settlement.
9. Receive scheduled debt reminders.

NLP parsing, OCR extraction, debt simplification and QR generation can then appear as included behaviors or supporting subflows. UC06 remains excluded while research continues. Retain identifiers or document an explicit mapping if the team renumbers use cases, because the assignment requires a specification for every use case shown in the final diagram. The [implementation plan](usecase-specification-plan.md) records the sequence, relevant Vision constraints, Markdown delivery format, and coverage checks.

## Final assessment

The diagram document is a useful starting point for the required specification:

- It is strong enough to establish the main product idea and begin drafting.
- UC01 and UC02 provide useful examples.
- It is not complete enough for implementation, acceptance testing or submission as a formal use-case specification.
- Before expanding it into the template, reconcile approval and settlement behavior with the PA1 Vision and its referenced decision record, correct the feature references and tier limits, and define the missing flows and outcomes.
