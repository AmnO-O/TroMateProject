# TroMate Use Case Specification Plan

This plan turns the [assignment requirements](requirement.md) into a complete use-case model and specification. The deliverable must contain a reviewed diagram and a specification for **every use case in that final diagram**. Each specification must have a name, brief description, actors, preconditions, basic flow, alternative flows (or an explicit statement that none apply), and postconditions. **Alternative Flows is a compulsory template field and a completion gate.** The [alternative and exception flows catalogue](alternative-flows-catalogue.md) is the required starting point for drafting and reviewing that field. The finished document must follow the [Moodle template](UseCase-Specification-Template.md) and be ready for team review.

**Agreed scope and format:** UC06 (Auto-Accept Expense) is excluded from the current diagram and specification while auto-accept remains under research; this is not a final adoption decision. Preserve the existing IDs of the other use cases. Author and deliver the specification in Markdown. The user will convert it to DOCX after editing is complete.

## 1. Baseline and source rules

1. Use [TroMate Vision (Small Project), version 1.0](../../pa/PA1-Group06/vision/rup_vision_sp.docx) as the scope and feature-numbering authority. Its Product Features table defines **Features 1–10**. Its commercial strategy defines the Free and TroMate Pro limits.
2. Use the [project decision record](../management/MVP_plan.md), which the PA1 Vision cites, to clarify behavior that the Vision leaves open. In particular, it specifies explicit approval of pending expenses and manual confirmation of received payments. Record any future disagreement with the PA1 Vision as a decision to resolve, rather than silently changing the specification.
3. Use the existing [use-case diagram document](../analysis-and-design/use_case_diagram.md) as the starting inventory and relationship model. Treat its use-case descriptions as drafts; reconcile them with the PA1 Vision before reuse. The [review summary](usecase-diagram-summary.md) lists known defects.
4. Use [UI flows](../analysis-and-design/ui-flows.md) and [e-wallet research](../ewallet.md) as supporting detail where they agree with the baseline. Do not use the older `docs/requirements/vision.md`.
5. Resolve the `[[use_case_diagram]]` reference in `requirement.md` to the actual diagram file or its reviewed replacement; there is currently no `docs/usecase-specification/use_case_diagram.md` in the repository.
6. Review the [alternative-flows catalogue](alternative-flows-catalogue.md) for every final use case. Its flow IDs and B-step anchors are drafting aids; its proposed policies do not override the Vision or a recorded team decision. Carry accepted flow IDs into the specification or its coverage table.

## 2. Freeze the use-case inventory and diagram

The current diagram contains **11 named use cases**: UC01, UC02, UC03a, UC03b, UC04, UC05, and UC07–UC11. UC06 has been removed from the drawn model and detailed inventory by the user's scope decision; its no-response scenario is covered by UC05-AF04, which keeps an unapproved proposal pending. Auto-accept research does not block completing the current specification. For any further removal or merge, update the diagram and record the old-to-new mapping.

| Current ID | Current use case | PA1 Vision feature | Planned disposition and specification focus |
|---|---|---|---|
| UC01 | Log Expense via Natural Text | 1, 6 | Keep. Specify parsing, editable preview, payer/payees, split rules, and creation of a pending proposal. |
| UC02 | Log Expense via Receipt Photo | 2, 6 | Keep. Specify OCR plus optional caption, item allocation, review/edit, and the Free tier scan quota. |
| UC03a | Vision OCR Data Extraction | 2, 3 | Keep as a named included use case if it remains in the diagram; specify its inputs, outputs, failure and low-confidence paths. It is internal behavior, not an external actor. |
| UC03b | Parse Intent & Split Logic | 1, 2 | Keep as a named included use case if it remains in the diagram; specify normalization, person matching, split calculation, and ambiguity handling. |
| UC04 | Scan Utility Meter & Landlord Invoice | 2, 3 | Keep. Separate meter-reading and invoice-review branches; specify corrections, calculation, and quota handling. Consider splitting it only if the diagram is revised accordingly. |
| UC05 | Confirm / Reject / Edit Pending Expense | 6 | Keep. Define who must agree, rejection/edit behavior, concurrency, and when an expense becomes an official ledger entry. |
| UC07 | Simplify Group Debts | 4 | Keep as a named included use case if diagrammed; define trigger, net-balance inputs, exact amounts, and output obligations. |
| UC08 | Settle Net Debt | 5 | Keep. Define QR request, transfer claim, pending receipt, creditor confirmation, mismatch/rejection, and settlement of only the relevant obligation. |
| UC09 | Generate Dynamic VietQR & Confirmation | 5 | Keep QR generation as included behavior. Align the title with its actual scope; model receipt confirmation under UC08 or as a separate user-goal use case with a creditor/room-lead actor. |
| UC10 | Send Scheduled Debt Reminders | 7 | Keep. Define 24h/48h trigger, recipient, link, suppression after settlement, and failed delivery. |
| UC11 | View Personal Ledger & Dashboard | 8; 10 only for Pro/later analytics | Keep basic balances and ledger. Apply Free 30-day history and Pro unlimited history. Move category charts/monthly analytics out of unconditional MVP behavior. |

Check the PA1 Vision for user-facing behavior that has no clear place in this inventory: room setup/member onboarding, bank-detail management, Free-to-Pro upgrade, and Pro-only analytics. If the final specification covers **MVP only**, explicitly defer Pro purchase and analytics. If it covers the full PA1 Vision, add any necessary user-goal use cases to the diagram and inventory before drafting their specifications.

For the diagram itself:

- Maintain the editable [PlantUML source](../analysis-and-design/use_case_diagram.puml) and the diagram embedded in the model document together. Render the final local image at `docs/usecase-specification/assets/use-case-diagram.png` for use in the consolidated Markdown document.
- Draw TroMate as the system boundary. Keep Room Member and Room Financial Lead as actors, with the lead specializing the member. Model external Telegram/banking services only where their interaction matters. Do not place TroMate's own background engine as an actor outside its boundary.
- Recheck every association, `<<include>>`, and `<<extend>>` after deciding whether internal services remain named use cases. Ensure the relationship direction and label reflect the written behavior.
- Replace the invalid Feature 12 reference in UC11. Map UC04 to both Features 2 and 3. Distinguish basic Feature 8 from later/Pro Feature 10 in UC11. The Feature 11 reference was removed with UC06.
- Produce a stable local diagram image for the template and inspect that all labels and relationships remain legible.

**Gate A:** A reviewer can count every use case in the final diagram, identify its actor and Vision feature, and see a recorded disposition for each original ID. Remap the catalogue's flow IDs when a case is removed, renamed, merged, or split. Add a catalogue section for each new use case.

## 3. Decide shared business rules before writing flows

Record these decisions in the specification's assumptions or a short decision table so the use cases cannot contradict each other:

Use the catalogue's D references to identify detailed questions behind these rules and record the agreed answers or explicit assumptions inline in the Markdown. D11 records deferred auto-accept research and does not require resolution for this deliverable.

1. **Expense approval:** Which involved members must approve? Does a single rejection freeze the proposal? What can the creator edit, and does editing reset approvals? The baseline says no response remains `PENDING`; no silent auto-commit.
2. **Ledger boundary:** A proposed expense may show a preview, but it does not change official balances until confirmed. Define the exact confirmation event and audit record.
3. **OCR quota and tiers:** A Free room has a shared 10-scan/month quota; Pro has unlimited scans. Define the billing-cycle boundary, whether failed scans count, and what a user sees when the quota is exhausted. Do not invent these details in a basic flow without a team decision.
4. **Settlement states:** Define `Awaiting payment → Awaiting receipt confirmation → Settled`, including who may claim payment and who may confirm receipt. A QR scan or OCR screenshot alone cannot clear a debt. Specify how a missing/incorrect transfer is handled.
5. **Amounts and allocation:** Decide integer-VND rounding, total reconciliation, shared-item defaults, ambiguous names, and whether the payer is included among beneficiaries.
6. **Room authority and data:** Define room creation/binding, member identity, lead privileges, bank-detail ownership, and access to room ledger data.
7. **Retention and analytics:** Free history is 30 days; Pro history is unlimited. Monthly charts are later/Pro scope. Decide what UC11 shows for each tier in the targeted release.

**Gate B:** Every rule has one approved answer or is explicitly marked as an open decision. Drafts may proceed with labeled assumptions, but no final use-case specification should present an unresolved assumption as agreed behavior.

## 4. Review the compulsory alternative flows

1. Review the catalogue section for every final diagram use case, including UC03a/UC03b and other included services if they remain diagrammed. Include applicable shared flows SH01–SH07.
2. Give each candidate flow a recorded disposition: **included**, **covered by another named flow**, **conditional pending decision**, or **out of scope with a reason**. Do not omit a plausible branch just because the original diagram description has only a happy path.
3. Clarify the catalogue's business-rule questions where they affect the targeted release; D11 is deferred research. Unsupported operations still need an explicit user-visible outcome where they can be attempted, such as unsupported split forms or unavailable Pro history.
4. Finalize each use case's numbered basic flow, then replace the catalogue's proposed B1/B2 anchors with the actual step numbers. For every accepted alternative, write its trigger, ordered actor/system actions, return step or termination, and postcondition in the template's Alternative Flows field.
5. Connect included-service failures to the parent flow. For example, an unreadable OCR result must identify both UC03a's returned result and UC02/UC04's request for a replacement or correction. Reference shared behavior without leaving the caller's outcome unexplained.
6. Review no-response, cancellation, duplicate action, concurrent change, failed save, and failed delivery paths wherever applicable. Check Free quota/history and Pro-only paths against the PA1 Vision. UC06 is excluded; preserve UC05-AF04's no-response behavior without adding auto-approval.
7. Use “None” only after reviewing the catalogue and establishing that a use case has no applicable alternatives. A blank field, placeholder, or unreviewed “None” does not meet the requirement.

**Gate C:** Every final use case has reviewed alternative-flow coverage. Each accepted flow is anchored to an actual basic-flow step and has a defined outcome; no applicable candidate is silently omitted, and no required business decision remains unresolved in the final draft.

## 5. Write the specifications using the Moodle structure

Create the consolidated Markdown deliverable at `docs/usecase-specification/usecase-specification.md`. Use the Moodle template's document information, revision history, table of contents, use-case model image, and numbered use-case sections. Reference the local diagram image at `assets/use-case-diagram.png`. The user will perform DOCX conversion after all Markdown editing is complete.

For **every use case in the final diagram**, complete these fields:

| Field | Completion rule |
|---|---|
| Use case name and brief description | Match the final diagram's ID/name and state the actor's observable goal. |
| Actors | Name the initiating user or external service; identify supporting actors where needed. Do not name TroMate as its own external actor. |
| Preconditions and trigger | State room membership, permissions, required input, tier/quota, and the event that starts the case where relevant. |
| Basic flow | Number alternating actor/system actions from trigger through visible success; reference included cases by ID without losing the user-level story. |
| Alternative and exception flows | Compulsory. Integrate the reviewed catalogue flows with stable AF IDs or an explicit ID mapping. Anchor each to a numbered basic-flow step; give the trigger, ordered actions, recovery/return step or termination, and postcondition. Use “None” only with a reviewed rationale in the coverage record. |
| Postconditions | State success and failure/minimal guarantees, including `PENDING`, confirmed ledger, or settlement state as appropriate. |
| Traceability | Link to the final diagram ID and PA1 Vision feature number, and reference applicable Vision constraints below. Mark Pro/later-only behavior clearly. |

Use the [full catalogue](alternative-flows-catalogue.md), which covers the 11 current use cases, shared failures, proposed step anchors, and decision-dependent branches. Include its accepted scenarios in the consolidated specification; the catalogue alone does not complete the template's compulsory Alternative Flows fields.

### Apply relevant Vision constraints

Carry the following requirements from the PA1 Vision's **Other Product Requirements** into relevant use-case notes, flows, or postconditions. The V-NFR labels below are local traceability labels, not additional feature numbers. Keep system-wide or implementation constraints in a short shared notes section referenced by affected use cases; preserve the Moodle template's fields and keep infrastructure detail out of user action steps.

| Reference | Vision constraint | Applicable use cases and documentation action |
|---|---|---|
| V-NFR01 | Text command/message parsing response under 1.5 seconds; image parsing under 3.5 seconds. | Reference the appropriate target in UC01–UC04, including UC03a/UC03b. Preserve the stated targets and identify any measurement assumptions when specifying processing/failure feedback. |
| V-NFR02 | Group concurrency control with Redis distributed-lock TTL of 300 seconds. | Reference in shared notes for UC01, UC02, UC04 and UC05; describe consistent outcomes for simultaneous actions in alternatives. The lock TTL is not an expense-approval timeout and does not restore UC06. |
| V-NFR03 | 99.5% availability for webhook processing and scheduled reminders. | Reference as a system-wide target for chat flows and UC10. Document retry/delivery failure outcomes without promising every individual operation succeeds. |
| V-NFR04 | TLS 1.3 for webhook/API communication; financial ledger persisted in PostgreSQL with access restricted to room members. | Reference shared security/storage notes from the affected flows. Ensure permission failures and persisted financial outcomes are explicit; no additional infrastructure actions are required from members. |
| V-NFR05 | Strict room isolation for expenses, bank accounts and transaction history. | Apply to every room-scoped use case, especially UC08–UC11; verify that shared unauthorized/stale-room alternatives expose no other room's financial data. |
| V-NFR06 | Conversational input and clear inline action buttons supporting use without training. | Use concrete user-visible prompts and action choices in UC01, UC02, UC04, UC05, UC08 and UC10, with readable feedback on clarification and failure. |
| V-NFR07 | Immutable, auditable ledger with explicit pending confirmations and recorded rejection/correction behavior. | Reference in UC01, UC02, UC04, UC05, UC07 and UC08. Preserve original confirmed records when recording authorized corrections; distinguish a pending-state rejection from a confirmed-entry correction. |
| V-NFR08 | Webhook retry queuing and graceful manual correction when OCR confidence is low. | Connect shared retry/duplicate behavior to UC01/UC02/UC04/UC05 and extraction failures to UC03a/UC03b. Include caller-visible clarification/correction instead of fabricated amounts. |

**Gate D:** A reader can execute each basic flow and accepted alternative step by step and determine the system state after every success, rejection, cancellation, and failure path.

## 6. Integrate and verify coverage

1. Build a traceability table with one row per **final diagram** ID: actor, Vision feature, applicable V-NFR references, section number, basic flow, accepted alternative-flow IDs, applicable shared-flow IDs, preconditions, and postconditions. Record candidate flow dispositions and any necessary clarification inline; retain the UC06 deferral note and any further old-to-new ID mappings.
2. Count the final diagram use cases and the specification sections. Every diagram use case must have exactly one corresponding section. If internal included use cases remain on the diagram, they also need specifications under `requirement.md`.
3. Compare the diagram, feature table, and text for matching actors, names, `include`/`extend` relations, triggers, state changes, tier limits, and applicable Vision constraints. Confirm that there are 11 diagrammed/specification entries and that UC06 appears only in the research/deferral note.
4. Check monetary examples and the accepted alternatives: totals equal the sum of shares, allocations use integer VND, and pending/rejected proposals never affect confirmed balances. Duplicate actions must not duplicate debt or payment. A settlement clears only its identified obligation after authorized receipt confirmation. Failed operations must report the actual persisted state.
5. Remove template examples, guidance text, placeholders, broken wiki-links, and remote-only image dependencies. Check the local diagram image and all relative links. Review the final Markdown for readability and completeness before the user's later DOCX conversion.
6. Have a teammate review the unresolved decisions and use-case coverage. Record revisions in the document's revision history, then mark the artifact ready for review/submission.

**Gate E (definition of done):** All 11 use cases in the current diagram have a completed template section; every section has a name, actors, preconditions, basic flow, reviewed alternative flows or justified “None,” and postconditions. All current catalogue candidates have a recorded disposition, applicable alternatives appear in the actual specification with valid step references, and necessary business-rule clarifications are resolved or explicitly excluded from the release. UC06 remains deferred for research and does not block completion. The diagram and text agree with the PA1 Vision's Features 1–10, Free/Pro boundaries, and applicable V-NFR01–V-NFR08 constraints; no unresolved behavior is described as consensus; the consolidated Markdown deliverable is saved at `docs/usecase-specification/usecase-specification.md` for the user's later DOCX conversion.
