# TroMate Alternative and Exception Flows Catalogue

This catalogue proposes the missing alternative flows for all **11 use cases currently drawn** in the [use-case model](../analysis-and-design/use_case_diagram.md). It contains 101 use-case-specific candidates and seven shared flows. UC06 is excluded from the current specification while auto-accept remains under research; the other UC IDs are preserved. This catalogue is a required drafting input for the [specification plan](usecase-specification-plan.md): the [assignment requirements](requirement.md) make Alternative Flows compulsory in every use-case specification. Review these proposals, clarify applicable business rules, and place the accepted flows into the corresponding sections of the [Moodle template](UseCase-Specification-Template.md).

The scope authority is the [PA1 Vision Small Project document](../../pa/PA1-Group06/vision/rup_vision_sp.docx), supported by the [decision record it references](../management/MVP_plan.md). The old `docs/requirements/vision.md` is excluded. The baseline requires explicit approval of pending expenses, manual creditor confirmation of settlement, a shared Free room quota of 10 OCR scans/month, Free history of 30 days, and unlimited OCR/history for Pro. Monthly analytics remain Post-MVP/Pro scope. The proposed behavior below is not a claim about existing implementation or an already approved detailed policy.

## 1. How to use the catalogue

- **A** means another valid route to the use-case goal. **E** means an exception, cancellation, or recovery route. Both belong in the template's Alternative Flows field.
- Each flow has a stable ID such as `UC05-AF03`. Retain that ID in the specification or a traceability table so coverage can be reviewed after renumbering steps.
- Each use case has **proposed basic-flow anchors B1, B2, …**. These identify meaningful points in the corrected flow; they are not the current draft's step numbers. Replace them with the final numbered basic-flow steps when writing the specification.
- Every row specifies a deviation, response, and return/end state. Expanding a row into numbered steps is expected when the response involves several actor actions.
- A reference such as **D01** marks an unresolved business rule in Section 3. Resolve it before describing that branch as approved behavior. A decision may reject a proposed capability; in that case, document the unsupported-operation outcome rather than inventing support.
- Shared flows and failures in included use cases must be connected to the parent use case. A technical failure ending UC03a must also explain what the member sees and what happens to UC02 or UC04.
- A cancellation after a financial action has already committed cannot silently undo that action. Show the saved outcome and route any correction through a separately authorized, auditable action.

## 2. Shared flows to apply where relevant

These are reusable rules, not additional diagrammed use cases. Reference or restate each applicable shared flow in the final use-case section.

| ID | Deviation or trigger | Proposed response | Return or end state |
|---|---|---|---|
| SH01 | Room is not configured, or the chat is not bound to the expected workspace. | Explain that setup/binding is required. Offer the existing setup route if available; do not infer a room from another chat. | End without a financial change; restart after setup. |
| SH02 | Actor is unauthenticated, no longer a member, or lacks permission for the action. | Request valid authentication where applicable; otherwise deny the action without exposing another room's data. Check permission again when saving. | Resume the requested step after successful authentication, or end without change. |
| SH03 | The same delivery, request, or button action is retried. | Return its recorded outcome or resume the unfinished operation. Do not create a second expense, settlement, approval, or quota charge. A merely similar receipt/message is handled as a possible duplicate, not automatically discarded. | One durable result for the same operation. |
| SH04 | Data needed for the action changes during the flow. | Re-read the affected expense, room membership, balance, bank details, or entitlement. Show the change and require renewed review where the financial meaning changed. | Resume validation/review of the current version; do not approve stale terms. |
| SH05 | A save, external call, or delivery fails, or its result is uncertain. | Show failure or processing status accurately. Before retrying a financial write, determine whether it committed; preserve a saved result even if its notification failed. Retry limits and timing require D13. | Retry the failed step safely or end with the actual persisted state. |
| SH06 | User cancels or leaves before committing the action. | Stop the current interaction. If a pending proposal already exists, state that it remains pending unless the user explicitly cancels it with permission. | No new commitment; existing saved state is preserved. |
| SH07 | Membership changes while outstanding obligations exist. | Deny new actions by unauthorized former members. Preserve recorded obligations; do not silently redistribute or delete them. Apply the agreed departure/reconciliation rule in D12. | Current authorized members see the preserved, current financial state. |

## 3. Decisions needed before finalizing dependent flows

| Decision | Question to resolve | Affected use cases |
|---|---|---|
| D01 | Who must approve an expense: all beneficiaries, payer plus beneficiaries, or another explicit rule? What does one rejection do? No response stays pending under the baseline. | UC01, UC02, UC04, UC05 |
| D02 | Who can edit/cancel a proposal, which fields can change, and which changes invalidate prior approvals? How are corrections to confirmed entries authorized and recorded? | UC01, UC02, UC04, UC05 |
| D03 | Which split forms are supported? How are unspecified payer/beneficiaries, unknown aliases, ambiguous currency, unassigned receipt items, and payer participation resolved? | UC01, UC02, UC03b, UC04 |
| D04 | How are indivisible VND remainders allocated so shares always equal the total? Are negative amounts/refunds supported as a separate operation? | UC03b, UC04, UC07, UC08 |
| D05 | When does the room's monthly OCR quota reset? Do failed scans count? How are concurrent requests and retries counted? | UC02, UC03a, UC04 |
| D06 | Which utility tariffs, billing periods, meter replacement/reset cases, and member proration rules are supported? | UC04 |
| D07 | Can the debtor withdraw a payment claim? Are partial/overpayments supported? Can a creditor record an off-flow transfer without an uploaded screenshot? | UC08 |
| D08 | Can the room lead confirm for another creditor? Who manages recipient bank details, and what happens if they change after a QR is issued? | UC08, UC09 |
| D09 | What starts the 24h/48h reminder clock? Are reminders suppressed while receipt confirmation is pending? How are missed deliveries retried? | UC10 |
| D10 | Does history retention affect visibility, storage, or both? What happens to old records and unsettled obligations after a Pro downgrade? Do not silently delete outstanding debt. | UC11 |
| D11 | Deferred research: UC06 is removed from the current model/specification. Auto-accept remains under research with no final adoption decision; that research does not block this deliverable. No response currently stays pending under UC05-AF04. | UC05; former UC06 excluded |
| D12 | What happens when a member leaves or the debt graph changes while a settlement is underway? How are the original obligation and subsequent reconciliation preserved? | UC05, UC07, UC08, UC09 |
| D13 | What are supported media limits, service timeouts, retry limits, and the user-facing recovery routes? A retry must not duplicate a financial action. | All active use cases where applicable |

## 4. UC01 Log Expense via Natural Language Text

Proposed anchors: **B1** receive a message in the bound room; **B2** interpret and validate through UC03b; **B3** show the proposed amount, payer, beneficiaries and allocation; **B4** save/broadcast one `PENDING` proposal; **B5** hand over to UC05. Official balances change only after confirmation.

Shared flows: SH01–SH07 as applicable.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC01-AF01 A | B2: Explicit one-to-one debt instead of a group purchase. | Show the named creditor, debtor, amount and description. Do not charge uninvolved members. | B3 with a one-to-one proposal. |
| UC01-AF02 A | B2: Named subset or unequal fixed shares. | Apply the supported allocation through UC03b; display every participant and share, including the payer's share where applicable (D03). | B3 with the explicit allocation. |
| UC01-AF03 E | B2: Message is ordinary conversation or not a supported expense intent. | Create no proposal. Ignore clear non-expense chat; request clarification when the user appears to be attempting an expense. | End, or B2 after clarification. |
| UC01-AF04 E | B2: Missing/ambiguous amount, payer, beneficiary, nickname or split. | Surface UC03b's specific question; let the member supply or correct the fields without silently choosing a person. | B2; no official debt created. |
| UC01-AF05 E | B2/B3: Invalid amount, unsupported currency, or shares do not reconcile. | Explain which field is invalid and request a valid supported value/allocation. | B2 or B3 after correction. |
| UC01-AF06 A | B3: Member corrects the proposed interpretation. | Update the preview and rerun affected validations. A change to payer/participants must be visible. | B3; proceed to B4 only when valid. |
| UC01-AF07 E | B4: A similar expense is already present. | Show the possible match and ask whether this is the same expense or a separate purchase. Same-delivery retries use SH03 instead. | Show existing proposal, or B4 for a separately confirmed new purchase. |
| UC01-AF08 E | After B4: Original message is edited or withdrawn. | If a supported edit/withdrawal event is received, apply D02: revise/cancel the pending proposal and refresh approvals. If already confirmed, require the authorized correction route. Do not assume every deletion can be observed by the platform. | Updated/cancelled pending proposal, or unchanged confirmed entry awaiting correction. |
| UC01-AF09 E | B2/B4: Parser, save, or group broadcast fails. | Apply SH05. If parsing cannot recover, offer supported field correction; if the proposal saved but the card failed, preserve it and retry delivery. | Resume the failed step; never show a failed delivery as a second expense. |

## 5. UC02 Log Expense via Receipt Photo and Text Context

Proposed anchors: **B1** receive image/caption and check room/tier eligibility; **B2** extract through UC03a; **B3** interpret/reconcile through UC03b; **B4** display editable receipt allocation; **B5** create/broadcast one `PENDING` proposal; **B6** hand over to UC05. Treat readability as an input validation check so unreadable images have a documented failure path.

Shared flows: SH01–SH07 as applicable. The quota applies to a scan request once, not again for each included service.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC02-AF01 E | B1: Free room has no scans left. | Explain the quota and reset/Pro option allowed by the targeted release. Offer text logging through UC01. Do not start another chargeable scan (D05). | End scan; text logging is a separate route. |
| UC02-AF02 A | B1: Room has Pro entitlement. | Allow scanning without the Free quota restriction after checking current room entitlement. | B2. |
| UC02-AF03 E | B2: Unsupported, unreadable, incomplete, or non-receipt image. | Propagate UC03a's explanation; request a clearer/supported photo or offer text logging. | B1 for replacement, or end without a proposal. |
| UC02-AF04 A | B3: No caption or allocation instructions. | Show the supported default split and its explicit beneficiary list; request missing information where no default is approved (D03). | B4 after a complete allocation. |
| UC02-AF05 E | B3: Caption conflicts with detected items, totals, or participants. | Show the conflicting fields and request correction. Do not assume the caption or OCR amount is correct. | B3 after correction. |
| UC02-AF06 A | B3: Some items are personal and others shared. | Allocate named items, identify unassigned items, and ask or apply the approved visible shared-item rule (D03). | B4 with all items allocated. |
| UC02-AF07 E | B3/B4: Item totals differ from receipt total, including tax, discount, service fee or rounding. | Show the difference and request a reconciled allocation. Do not silently spread unexplained amounts. | B3/B4; no confirmed ledger effect. |
| UC02-AF08 A | B4: Member corrects OCR fields or split. | Recalculate totals and validate people/amounts again. Keep the original image available for review. | B4 with corrected preview. |
| UC02-AF09 E | B5: Receipt resembles an already logged bill. | Show the possible duplicate and ask whether to use the existing proposal or log a distinct expense. A repeated delivery returns its existing result. | Existing proposal, or B5 after explicit new-expense choice. |
| UC02-AF10 E | B1–B5: Another member consumes the last scan, entitlement changes, or user cancels. | Recheck eligibility at the scan boundary (D05); explain the current result. Apply SH06 for cancellation and preserve any already saved proposal. | Resume if eligible, or end with actual quota/proposal state. |
| UC02-AF11 E | B2/B5: Extraction, persistence, or broadcast fails. | Propagate the included-service result and apply SH05. Quota handling for failed attempts follows D05. | Retry safely or end with no new official balance change. |

## 6. UC03a Vision OCR Data Extraction

Proposed anchors: **B1** receive an authorized scan request and media; **B2** validate type/readability; **B3** extract text and numeric fields; **B4** return extracted data and uncertainty to the caller. This service never approves an expense or proves receipt of payment.

Shared flows: SH03–SH05; authorization/quota failures must be returned to the caller. User prompts belong to UC02/UC04 or the relevant parent flow.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC03a-AF01 E | B1: Media cannot be fetched or has expired. | Return a media-unavailable result; caller asks for a fresh upload. | End extraction; caller resumes image submission. |
| UC03a-AF02 E | B2: File type, size, or image count is unsupported. | Return the supported limits (D13); caller requests one acceptable input. | B1 with replacement media. |
| UC03a-AF03 E | B2/B3: Photo is blurred, cropped, glared, rotated beyond recognition, or contains no usable text. | Return unreadable/incomplete fields rather than fabricated amounts; caller requests a better photo or supported manual correction. | No complete extraction until corrected. |
| UC03a-AF04 A | B3: Some fields are legible but others are uncertain. | Return the readable fields with the uncertain/missing fields identified for human review. | B4 with partial result; caller cannot approve an incomplete allocation. |
| UC03a-AF05 E | B3: Multiple receipts/meters or conflicting totals are detected. | Identify ambiguity and ask the caller to obtain a crop, a single image, or an explicit selection. | B1/B2 after clarification. |
| UC03a-AF06 E | B3: OCR provider times out, is unavailable, or returns unusable data. | Return a recoverable failure using D13; do not substitute a zero amount. | Safe retry or caller fallback. |
| UC03a-AF07 E | B4: Extracted fields fail validation or cannot be handed to the next service. | Preserve the extraction result if available and return validation/processing status; retry without another quota charge for the same operation (D05). | Resume validation/handoff or return failure to caller. |

## 7. UC03b Parse Intent and Split Logic

Proposed anchors: **B1** accept text/OCR and room-member context; **B2** identify intent and normalize amounts; **B3** resolve payer/beneficiaries; **B4** allocate items/shares and reconcile totals; **B5** return a validated proposal or precise clarification request. This service does not save confirmed debt.

Shared flows: SH03–SH05. UC01/UC02/UC04 owns the conversation and must resume the correct review step after clarification.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC03b-AF01 A | B2: Supported slang units or explicit one-to-one/custom allocations appear. | Normalize the units and use the matching supported intent/split rule; retain a readable description of the interpretation. | B3/B4. |
| UC03b-AF02 E | B2: Amount separators, currency unit, intent or multiple candidate totals are ambiguous. | Return the ambiguous values and request a supported amount/intent. | B2 after clarification. |
| UC03b-AF03 E | B2: Zero/negative amount, invalid number, or unsupported refund/currency is supplied. | Reject the invalid value or direct the caller to an approved separate refund flow if one exists (D04). | No valid proposal until corrected. |
| UC03b-AF04 E | B3: Nickname matches several people, no room member, or an unavailable former member. | Return the ambiguity and request explicit selection of a current eligible member. | B3 with resolved identities. |
| UC03b-AF05 E | B3: Payer or beneficiaries are missing; “chia 3” does not identify which three people. | Apply only an approved visible default; otherwise request the actual participants (D03). | B3, then caller preview. |
| UC03b-AF06 E | B3: Sender names a different payer or repeats a person under two aliases. | Show the intended payer explicitly and apply the authorization rule (D02/D03); merge aliases only when they resolve to the same verified member. | B3/B4 with explicit identities, or reject. |
| UC03b-AF07 E | B4: An item has no assignee, is assigned twice, or named item cannot be matched to OCR. | Return the unresolved item/quantity and ask for allocation correction; do not guess shared participation (D03). | B4 after correction. |
| UC03b-AF08 E | B4: Shares, quantities, percentages if supported, or receipt totals do not reconcile. | Return the precise difference and request correction. Unsupported split forms receive an explanation and supported alternatives (D03). | B4; no valid proposal yet. |
| UC03b-AF09 A | B4: Equal division produces a VND remainder. | Apply the approved deterministic integer-VND rule and display which shares receive the remainder (D04). | B5 only when shares equal the total. |
| UC03b-AF10 E | B1–B5: Room context changes, parser fails, or output is structurally/financially invalid. | Refresh affected context or return a clarification/failure to the caller; validate generated output before use. | Reparse/review current data or safe end; no fabricated debt. |

## 8. UC04 Scan Utility Meter and Landlord Invoice

Proposed anchors: **B1** lead selects room, billing period and meter/invoice input; **B2** check quota and extract through UC03a/UC03b; **B3** review readings, tariffs, rent and fees; **B4** calculate and review allocations; **B5** save/broadcast a `PENDING` proposal; **B6** hand over to UC05.

Shared flows: SH01–SH07; OCR quota and failure paths from UC02/UC03a apply here too.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC04-AF01 A | B1: Lead uploads only a meter photo. | Extract the reading and obtain the required period, previous reading and tariff from reviewed stored data or explicit input. | B3; a reading alone does not imply a payable bill. |
| UC04-AF02 A | B1: Lead uploads a landlord invoice, with or without meter photos. | Extract invoice components; compare accompanying meter readings when available. | B3 with the available evidence. |
| UC04-AF03 E | B2: Quota exhausted or extraction is unreadable/incomplete. | Explain the scan problem and request replacement or supported manual input; apply D05 to quota accounting. | B1/B3, or end with no new debt. |
| UC04-AF04 E | B3: Previous reading, tariff, billing period or required fee is missing. | Request the missing value rather than treating it as zero. Explain any first-billing-cycle setup. | B3 after validation. |
| UC04-AF05 E | B3: Current reading is less than previous, or meter reset/replacement is claimed. | Flag the invalid delta and require correction or an explicitly supported meter-change procedure (D06). | B3; no automatic negative utility debt. |
| UC04-AF06 E | B3: Invoice readings/charges differ from meter evidence or calculated total. | Show both values and the difference. Require correction or an authorized, recorded explanation under D06. | B3/B4 after reconciliation. |
| UC04-AF07 A | B3: Lead corrects an OCR digit, tariff, base rent or surcharge. | Recompute affected charges and show the revised total; valid zero consumption/zero fees must not be confused with missing fields. | B3/B4. |
| UC04-AF08 E | B4: Membership changed during the billing period or a custom utility split is requested. | Request an explicit supported allocation. Automatic proration or special tariffs require D06; do not silently charge current members for all past occupancy. | B4 with reviewed allocation, or reject unsupported rule. |
| UC04-AF09 E | B5: Same room/billing-period invoice already exists. | Show the existing bill and distinguish a pending correction from a genuinely additional bill (D02). Do not silently charge it again. | Existing proposal/correction route, or B5 for a justified separate bill. |
| UC04-AF10 E | B5/B6: Save fails, lead cancels, or members reject the proposal. | Apply SH05/SH06 or UC05 rejection handling. Preserve reviewable data where supported. | No unapproved amount affects official balances. |

## 9. UC05 Confirm Reject or Edit Pending Expense

Proposed anchors: **B1** open current pending proposal and details; **B2** check actor/expense version; **B3** record approval; **B4** evaluate the approved confirmation rule; **B5** commit exactly once, update balances through UC07 and notify members.

Shared flows: SH02–SH07.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC05-AF01 E | B3: An involved member rejects the expense. | Record the objection and freeze the proposal for correction according to D01. Tell the creator who objected and the reason if supplied. | Pending/disputed proposal; no official debt from it. |
| UC05-AF02 A | B3: Authorized actor chooses Edit. | Show editable fields, validate changes and publish a new reviewed version. Reset affected approvals according to D02. | B1 for renewed review of revised terms. |
| UC05-AF03 E | B4: Only some required approvals exist. | Show remaining required reviewers. Keep the proposal pending. | Wait for B3; no official balance change. |
| UC05-AF04 E | B3/B4: No one responds to the proposal. | Leave the proposal pending. Explain that silence is not approval; auto-accept is outside the current specification. | Remain pending; no automatic UC07 commit. |
| UC05-AF05 E | B2/B3: Button refers to an old proposal version or an already resolved proposal. | Show the current version/status; do not apply the old vote to changed terms. | B1, or end with the existing confirmed/cancelled state. |
| UC05-AF06 E | B3/B5: Repeated or simultaneous actions include approval, rejection and edit. | Record each valid action once and resolve against the current proposal/version and D01/D02. Do not confirm one version using approvals for another. | Current consistent state; one ledger commitment at most. |
| UC05-AF07 E | B3: Creator requests cancellation or actor is no longer eligible. | Permit cancellation only under D02 and current permissions; record the result. Deny unauthorized action. | Cancelled proposal or unchanged current state. |
| UC05-AF08 E | B5: Save/balance recalculation/notification fails. | Do not report confirmation before the ledger save succeeds. If the ledger did commit, retain that fact and safely finish derived updates/notifications; do not ask for duplicate confirmation. | Accurate saved status, with pending refresh/delivery shown where needed. |
| UC05-AF09 E | B1/B3: User wants to edit or reject an already confirmed expense. | Show that it is committed; use a separately authorized correction/reversal process (D02), preserving the original audit record. | Original entry remains until a valid correction is recorded. |

## 10. Deferred auto accept research

UC06 is removed from the current diagram and specification by the user's scope decision. Auto-accept remains under research, with no final adoption decision. There is no active UC06 basic flow or Alternative Flows section to complete, and no pending-expense timer/reminder capability is introduced by this deferral.

The former candidates are retired from the active count. Their applicable general outcomes are already covered as follows:

- `UC06-AF01` maps to `UC05-AF04`: no response leaves the proposal pending.
- `UC06-AF02` maps to `UC05-AF05` and SH04: actions must respect the current resolved state.
- `UC06-AF03` maps to `UC05-AF02`/`UC05-AF05` and SH04: edits and stale versions require current review.
- `UC06-AF04` maps to SH03/SH05 for duplicate or failed operations in active use cases. No new scheduled operation is required.

These mappings preserve review history without treating the research item as a current specification requirement.

## 11. UC07 Simplify Group Debts

Proposed anchors: **B1** obtain current confirmed ledger and settlement state; **B2** calculate net balances; **B3** calculate simplified obligations; **B4** validate invariants and publish the current result. Pending proposals are excluded.

Shared flows: SH03–SH05, SH07.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC07-AF01 A | B1/B2: No confirmed expenses or no outstanding balances. | Return an empty settlement list and correct zero balances. | B4; no payment required. |
| UC07-AF02 A | B2: Circular debts cancel to zero net balances. | Publish zero outstanding obligations while retaining the underlying audited ledger. | B4; no artificial transfer created. |
| UC07-AF03 E | B1: Pending/disputed proposals are present. | Exclude them from official calculation; show their separate pending state where appropriate. | B2 using confirmed entries only. |
| UC07-AF04 A | B3: Shares need integer-VND reconciliation. | Use the approved rounding rule at allocation boundaries (D04); preserve each valid member net balance and total. | B4 only when obligations reconcile exactly. |
| UC07-AF05 E | B2/B4: Input totals are inconsistent or output changes net balances. | Stop publication of the invalid result, identify the inconsistency and keep the last valid result marked with its age. | Safe failure/correction; never publish fabricated debt. |
| UC07-AF06 E | B3/B4: New confirmation or settlement changes the input during computation. | Recompute from current data or clearly withhold the stale result. | B1; publish a consistent current result. |
| UC07-AF07 E | B1/B3: A transfer is already awaiting creditor confirmation. | Apply D12 before changing the recipient/amount behind that settlement; preserve its identity and evidence for reconciliation. | Consistent obligations with active settlement preserved. |
| UC07-AF08 E | B3/B4: Computation/storage fails or exceeds the usable response window. | Explain that balances are refreshing/unavailable. Do not show a failed calculation as zero debt. | Safe retry; last valid result labeled if displayed. |

## 12. UC08 Settle Net Debt

Proposed anchors: **B1** select a current obligation; **B2** obtain QR/details through UC09; **B3** member transfers outside TroMate; **B4** member claims payment and supplies required evidence; **B5** creditor reviews receipt; **B6** record settlement once and refresh balances. A bank transfer can occur even if TroMate fails or is closed; TroMate must distinguish its own saved state from external payment reality.

Shared flows: SH02–SH07.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC08-AF01 A | B1: No outstanding obligation, or another action already settled it. | Show current status and balance. | End; no new payment request. |
| UC08-AF02 E | B2: Recipient details or QR generation fail. | Surface UC09's correction/retry route. Do not mark payment claimed or received. | B2 after correction, or end awaiting payment. |
| UC08-AF03 E | B3: Member closes/cancels bank interaction or transfer fails. | Keep the obligation awaiting payment unless the member later reports an actual transfer. TroMate must not infer failure solely from leaving the app. | Awaiting payment, with later claim still possible. |
| UC08-AF04 E | B3/B4: Bank outcome is unknown, or member transferred but did not return/upload evidence. | Ask the member to check their bank history before paying again. Allow the supported payment-claim route when they return. | Obligation remains unresolved in TroMate; avoid a duplicate transfer. |
| UC08-AF05 E | B4: Evidence is unreadable, missing, inconsistent or appears reused. | Request clarification/replacement under the evidence policy (D07). OCR may assist reading but cannot verify funds received. | Awaiting review/clarification; not settled. |
| UC08-AF06 E | B5: Creditor reports funds not received or sent to the wrong recipient. | Record rejection/reason and ask debtor to check the transfer. Do not clear the intended obligation or promise an automatic bank reversal. | Unresolved obligation; return to payment/review as appropriate. |
| UC08-AF07 E | B5: Received amount differs, including partial or excess payment. | Show expected and reported amounts. If D07 supports partial/overpayments, record the approved amount and reconcile explicitly; otherwise keep a discrepancy for manual resolution. | Never mark the whole obligation settled from an unexplained mismatch. |
| UC08-AF08 A | B4/B5: Creditor confirms a known transfer made without this QR or screenshot. | Accept only if D07 permits this route and the creditor is authorized; identify the exact obligation and amount. | B6 after valid receipt confirmation. |
| UC08-AF09 E | B4/B5: Debtor withdraws an erroneous payment claim. | Allow withdrawal only under D07 before final confirmation; notify the creditor. A completed settlement needs the separate correction process. | Awaiting payment, or unchanged settled state pending correction. |
| UC08-AF10 E | B5: Someone other than creditor attempts receipt confirmation. | Deny unless an explicit lead-delegation rule in D08 permits that actor. | Awaiting authorized receipt confirmation. |
| UC08-AF11 E | B4–B6: Obligation amount/recipient changes, or actions are repeated/concurrent. | Preserve transfer/claim identity, compare against the current obligation, and reconcile under D12. Accept a valid final confirmation once. | One settlement; changed amount does not silently consume evidence for another debt. |
| UC08-AF12 E | B6: Save or confirmation response fails after funds were transferred. | Determine whether settlement saved and show/retry that state update safely. Tell the member to await/check receipt confirmation rather than transfer again. | Accurate recorded settlement or unresolved review state; no duplicate clearance. |

## 13. UC09 Generate Dynamic VietQR and Confirmation

For these flows, UC09 owns **QR generation**; UC08 owns creditor confirmation. If the team retains “Confirmation” in UC09's final scope, move or reference the corresponding UC08 flows explicitly. Proposed anchors: **B1** validate current obligation and actor; **B2** obtain approved recipient bank details; **B3** generate code with amount/reference; **B4** show QR and human-readable details to the member.

Shared flows: SH02–SH05.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC09-AF01 E | B1: Obligation is zero, settled, unavailable or belongs to another room. | Show appropriate current status or deny access; generate no actionable QR. | End without financial change. |
| UC09-AF02 E | B2: Recipient bank details are missing or invalid. | Ask an authorized account owner/lead to provide/correct them under D08. Do not infer an account or use another room's details. | B2 after correction. |
| UC09-AF03 E | B3: Amount/reference exceeds supported format or contains invalid data. | Explain the invalid field; obtain a compliant amount/reference while preserving the obligation identity. | B3 after validation; no altered debt amount. |
| UC09-AF04 E | B3: QR provider/generator fails. | Offer safe retry. If approved bank details are already available, display them for a supported manual-transfer route; do not claim successful transfer. | B3 or caller UC08-B3. |
| UC09-AF05 A | B4: Bank deep link is unavailable or unsupported. | Keep the valid QR and readable bank details available; explain the supported scan/copy route. Do not promise an unverified app link. | Caller UC08-B3. |
| UC09-AF06 E | B4: QR cannot be displayed/read. | Offer regeneration or the supported readable-detail route without creating another obligation. | B3/B4 or caller's manual-transfer path. |
| UC09-AF07 E | B2–B4: Bank details, amount or obligation status change after generation. | Warn that the displayed QR is stale and replace it after review (D08/D12). If money may already have been sent, route to UC08 reconciliation. | Reviewed current QR, or unresolved transfer review. |

## 14. UC10 Send Scheduled Debt Reminders

Proposed anchors: **B1** find obligations due under the 24h/48h schedule; **B2** recheck status and current amount; **B3** prepare recipient/message/current payment link; **B4** deliver reminder and record result. Precise clock rules require D09.

Shared flows: SH03–SH05, SH07.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC10-AF01 A | B1/B2: Obligation is not due, zero or already settled. | Skip the reminder. | End for that obligation; no misleading tag. |
| UC10-AF02 E | B2: Payment is awaiting creditor confirmation. | Apply D09's suppression/review rule. Do not state that the debtor has not transferred as an established fact. | Suppressed reminder or an approved accurate review prompt. |
| UC10-AF03 E | B2/B3: Amount, recipient or simplified debt has changed. | Rebuild using current obligations and apply D12 to in-flight payments. | B2/B3 with current data, or suppress. |
| UC10-AF04 E | B3: Bank details or payment-link target is unavailable. | Avoid sending a broken actionable link; use an approved factual reminder or postpone delivery under D09. | Valid reminder without misleading payment action, or recorded postponement. |
| UC10-AF05 E | B4: Bot lacks permission, was removed, or Telegram delivery fails. | Record delivery failure and retry according to D09/D13. Do not mark the debtor as notified when delivery is unconfirmed. | Retry or recorded failed delivery; financial state unchanged. |
| UC10-AF06 E | B1/B4: Job is replayed or two workers select the same reminder interval. | Send at most the permitted reminder for that obligation/interval. | Existing delivery result; no duplicate tag. |
| UC10-AF07 E | B1: Service recovers after a missed reminder time. | Recheck current status, then apply the approved catch-up policy. Avoid a burst of obsolete 24h and 48h messages (D09). | One applicable reminder or suppression. |
| UC10-AF08 E | B2–B4: Settlement completes while reminder is being prepared. | Recheck before dispatch where possible; cancel unsent reminder. If already sent, make opening its link show current settled status. | No second payment requested from a settled link. |

## 15. UC11 View Personal Ledger and Dashboard

Proposed anchors: **B1** open authenticated Mini App and select room; **B2** determine tier, accessible history and filters; **B3** load confirmed balances/ledger and separately identified pending items; **B4** display details and permitted navigation. Free history is 30 days; Pro history is unlimited. Retention must not silently erase unresolved obligations (D10).

Shared flows: SH01–SH05, SH07.

| Flow | Branch point and condition | Proposed response | Return or outcome |
|---|---|---|---|
| UC11-AF01 A | B3: Room is new or has no expenses/debts. | Show a clear empty state and zero balances only when the data load succeeded. Offer existing expense-entry actions. | B4 with valid empty data. |
| UC11-AF02 A | B2: Member selects personal, room, date or expense filters. | Apply only supported filters within current room access and tier limits. | B3/B4 with filtered data. |
| UC11-AF03 A | B3: Valid filter produces no entries. | Explain that no entries match and allow filters to be cleared. | B2; do not imply room data was deleted. |
| UC11-AF04 E | B2: Date range/filter is invalid or unsupported. | Identify the invalid value and request a valid range/filter. | B2 after correction. |
| UC11-AF05 E | B2: Free member requests history older than 30 days. | Explain the tier limit. Show available history and an existing upgrade-information route if in scope. Do not promise unavailable data can be recovered (D10). | B2/B4 within allowed range. |
| UC11-AF06 E | B2/B4: Member requests monthly charts or Pro-only analytics outside the targeted release/tier. | Explain that the feature is unavailable under this scope/entitlement. Continue basic balances and ledger. | B4; no silent analytics entitlement. |
| UC11-AF07 E | B2/B3: Tier changes or Pro downgrades during the session. | Refresh access rules and apply approved retention/downgrade behavior (D10). Preserve unresolved obligations and do not destroy history as a side effect of viewing. | B2/B4 with accurate access. |
| UC11-AF08 E | B3: Load/refresh fails or displayed information is stale. | Show unavailable/stale status and retry; do not replace failed data with zero debt. | B3 on retry or a clearly labeled previous result. |
| UC11-AF09 E | B3/B4: Member changes room, data changes during paging, or a selected entry was corrected. | Load only the selected authorized room and refresh affected entry/summary consistently. Show recorded corrections without presenting old details as current. | B3/B4 with current authorized data. |
| UC11-AF10 E | B1/B4: Session expires, membership is revoked, or a direct link targets another room. | Reauthenticate/recheck access and deny unauthorized data. | B1 after valid authentication, or end without disclosure. |

## 16. Coverage for additional use cases if the final model expands

Do not add these capabilities solely because an exception is imaginable. If the final model adds them to implement the PA1 Vision's room setup, bank configuration or Pro purchase behavior, write their own basic flows and Alternative Flows sections and add them to this catalogue.

| Potential use case | Alternative/exception scenarios to specify if included |
|---|---|
| Create/bind room and onboard members | Bot lacks group access; group already bound; conflicting binding request; user not an eligible group member; duplicate join; member leaves; setup cancelled or save fails. |
| Manage recipient bank details | Unsupported/invalid bank details; unauthorized editor; change requested while payment is underway; cancellation; concurrent edits; failure after save. Do not claim account ownership was bank-verified without an integration. |
| Purchase/upgrade TroMate Pro | Purchase abandoned, rejected or pending; repeated payment notification; payment succeeded but entitlement update failed; room/price changed before confirmation. A real purchase needs an approved payment-verification mechanism; this catalogue does not assume merchant integration is available. |
| View monthly analytics or usage alerts | Insufficient retained data; missing categories/readings; zero baseline; invalid reporting period; unavailable Pro entitlement; delayed/failed calculation. These remain later/Pro scope unless the team changes the targeted release. |

## 17. Required integration and review record

For each final use case, record the applicable shared IDs and its own `AF` IDs in the specification coverage table. Give every candidate a disposition: **included**, **covered by another named flow**, **conditional pending a listed decision**, or **out of scope with a reason**. If the diagram removes or renames a use case, record the old-to-new mapping as well.

Before a specification is complete, replace its B anchors with final numbered steps; describe each accepted flow's trigger, ordered actions, return step or termination, and postcondition. Ensure the parent flow explains the result of an included service's exception. Conditional decisions must be resolved or explicitly excluded from the targeted release. “None” is acceptable only when a reviewed use case truly has no applicable alternative; a blank cell or “None” used to avoid the scenarios above does not satisfy the requirement.

Review financial outcomes especially carefully: pending or rejected proposals do not change confirmed balances; duplicate actions do not duplicate debt or settlement; QR generation does not prove payment; only authorized receipt confirmation settles the identified obligation; errors preserve the actual persisted state. Use the accepted flow IDs to derive review scenarios and later acceptance tests when implementation begins.
