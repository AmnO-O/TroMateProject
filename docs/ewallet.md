# Electronic Wallet Integration Feasibility Assessment

**Project:** TroMate

**Prepared by:** Cao Quang Hung — 24125010

**Date:** 29 October 2026

## Executive Summary

The recommended MVP approach is to support external bank transfers, allow the payer to upload payment evidence, and require the recipient to confirm receipt before TroMate marks an obligation as settled.

The research identifies MoMo merchant payment capabilities, including payment notifications, linked-wallet payments, and payment links. However, these capabilities do not establish that TroMate can monitor transfers between personal wallets or use merchant payment services for roommate debt settlement. Provider approval and business eligibility remain unresolved.

This report summarizes the research findings recorded for the project. Statements about unavailable or unconfirmed capabilities describe what the reviewed material established; they do not assert that such capabilities are technically impossible.

## 1. Problem Definition and Research Objectives

### 1.1 Settlement Context

Member B owes member A an amount of `x` VND and wishes to repay that obligation through TroMate.

The desired experience has two objectives:

1. Minimize the steps required to initiate and authorize payment.
2. Notify the recipient and update the corresponding obligation in TroMate after payment has been confirmed.

### 1.2 Research Questions

| Area | Research question |
| --- | --- |
| Transaction notifications | Can an electronic wallet send a verified payment-success notification to TroMate for a transfer between two members? |
| Linked-wallet payments | Can a member link a wallet to TroMate and authorize subsequent payments with minimal interaction? |
| Payment handoff | Can TroMate open a supported wallet or banking interface with the recipient, amount, and payment reference already populated? |

### 1.3 Target Experience Under Investigation

The following flow describes the intended automated experience, subject to integration feasibility:

1. Member B selects the obligation payable to member A.
2. TroMate initiates a supported linked-wallet payment or opens a payment interface with the required details populated.
3. Member B authorizes the payment.
4. The payment provider sends a verified transaction result to TroMate.
5. TroMate updates the identified obligation and displays the result to both members.

The research below evaluates whether the available integration mechanisms support this flow for personal debt settlement.

## 2. Transaction Notifications and Webhooks

### 2.1 MoMo Instant Payment Notification

The reviewed MoMo Instant Payment Notification (IPN) mechanism applies to merchant payment transactions. It is not established as a public mechanism for monitoring arbitrary transfers between two personal MoMo wallets.

| Scenario | Finding from the reviewed material |
| --- | --- |
| A customer pays a merchant order through MoMo. | Merchant payment notifications are supported. |
| A merchant backend receives confirmation of a successful payment. | Supported through the merchant notification mechanism. |
| A customer completes payment and closes the browser. | The merchant can still receive the asynchronous notification. |
| Member B transfers directly to member A's personal wallet. | No public IPN capability for this scenario was confirmed. |
| TroMate receives a webhook whenever member A receives a personal transfer from member B. | Not established by the reviewed merchant IPN documentation. |
| A merchant queries its payment transaction using an `orderId`. | Supported within the merchant transaction context. |

Support for merchant notifications must therefore be distinguished from support for personal transfer notifications. A successful merchant integration would not, by itself, allow TroMate to observe every transfer between members.

### 2.2 Access and Operational Requirements

The research records the following requirements for the merchant integration route:

| Area | Recorded requirement or limitation |
| --- | --- |
| Account registration | Registration with MoMo for Business (M4B). |
| Business eligibility | Business information, supporting documents, and contractual arrangements as required by the provider. |
| Test environment | Access to the applicable test environment and credentials through the provider's onboarding process. |
| Integration assessment | System integration testing (SIT), user acceptance testing (UAT), and any required provider assessment. |
| Production access | Completion of business verification and authorization for production use. |
| Fees | Subject to the applicable provider policy and agreement; a separate publicly stated IPN fee was not confirmed. |
| Transaction security | Protection of credentials, verification of notification integrity, and appropriate handling of transaction data. |

### 2.3 Implication for TroMate

The research has not established a notification mechanism that TroMate can use to confirm personal transfers under the project's current constraints. Automatic settlement based on a wallet webhook should therefore not be assumed available for the MVP.

This is an integration and eligibility limitation, rather than evidence that asynchronous payment confirmation is impossible in an approved merchant arrangement.

## 3. Linked Wallets and Tokenized Payments

Account binding and tokenized payment mechanisms allow eligible applications to associate a customer's wallet with subsequent payment requests. The reviewed MoMo capabilities indicate that such merchant integrations can reduce repeated payment steps.

Two separate questions determine their suitability for TroMate:

| Consideration | Assessment |
| --- | --- |
| Technical capability | The research identifies APIs for wallet binding and tokenized merchant payments. The authorization experience depends on the approved payment flow. |
| Business and use-case eligibility | These capabilities are intended for eligible partners or merchants. Permission to use them for debt settlement between individuals has not been established for TroMate. |

The existence of linked-wallet APIs does not establish that TroMate can debit a member's wallet and transfer funds to another member's personal wallet. The intended use case, onboarding requirements, and permitted movement of funds would need explicit confirmation from the provider.

Accordingly, linked-wallet payment execution should remain outside the MVP unless a suitable integration arrangement is approved.

## 4. Payment Links and Application Handoff

### 4.1 MoMo One-Time Payment Flow

The merchant payment flow described in the research is:

1. TroMate prepares an eligible merchant payment request containing fields such as `amount`, `orderId`, and `orderInfo`.
2. The backend submits the request to `POST /v2/gateway/api/create`.
3. The payment gateway returns a payment URL (`payUrl`) and/or an application deep link, depending on the permitted integration.
4. The user opens the returned payment interface.
5. The user reviews the details and authorizes payment.

This flow creates a merchant payment request. It should not be treated as a confirmed method for opening an arbitrary personal wallet transfer from member B to member A.

### 4.2 Eligibility and Production Access

The recorded integration requirements include M4B registration and credentials such as `partnerCode`, `accessKey`, and `secretKey`. Production use requires the applicable business verification and integration approval. The research also records that production deep-link access may require specific authorization from MoMo.

The reviewed material did not establish an officially supported public URL scheme that TroMate could independently construct with `amount` and `orderInfo` to open a personal transfer confirmation screen.

These findings concern the MoMo merchant gateway and application handoff route. They should not be generalized to bank-generated payment QR codes or to every banking application's supported behavior.

### 4.3 Implication for TroMate

A prefilled MoMo merchant payment interface remains subject to merchant eligibility. TroMate should not promise direct personal-wallet handoff based solely on the availability of the gateway API.

For the MVP, payment instructions can instead be presented within TroMate, using stored recipient bank details and a payment QR code where supported. The member completes the transfer in their own banking application.

## 5. Recommended MVP Settlement Approach

### 5.1 Settlement Flow

1. Member B opens the outstanding obligation payable to member A.
2. TroMate displays the recipient's bank details, exact amount, and transfer reference, with a payment QR code where available.
3. Member B reviews the details and completes the transfer in their banking application.
4. Member B returns to TroMate, reports that payment was made, and uploads the transfer confirmation image.
5. TroMate marks the obligation as **Awaiting receipt confirmation**.
6. Member A independently checks that the funds reached their account and selects **Confirm Received**.
7. TroMate marks the identified obligation as **Settled** and refreshes the affected balances.

A payment screenshot is supporting evidence. Neither generating or scanning a QR code nor reading a screenshot through OCR establishes that the recipient received the funds.

### 5.2 User Experience Considerations

For the payer, TroMate should reduce repetitive work by displaying the recipient's saved bank details, providing copy actions, and populating the amount and transfer reference in a supported QR code.

Payment evidence should be submitted through an explicit upload action, allowing the payer to select the screenshot after returning to TroMate. Automatic retrieval of screenshots from the device gallery is an implementation idea requiring separate platform assessment; it should not be assumed available.

For the recipient, manual confirmation provides an explicit opportunity to verify the account credit. Although this adds an interaction, it avoids clearing a debt solely on an unverified payment claim.

### 5.3 Settlement Safeguards

- An uploaded image or payer declaration must not automatically clear an obligation.
- Receipt confirmation must apply to the identified obligation, rather than resetting the member's entire room balance.
- Missing funds or amount discrepancies must remain unresolved until reviewed.
- If the bank transfer may have succeeded but TroMate has not updated, the user should check the transfer and receipt status before attempting another payment.

## 6. Conclusion

The reviewed MoMo APIs provide merchant payment capabilities, but their applicability to personal debt settlement in TroMate has not been established. Merchant onboarding, business eligibility, and permission for the intended use case remain prerequisites for adopting those integration routes.

The findings primarily concern MoMo. ZaloPay, ShopeePay, and other providers would require separate assessment; equivalent capabilities or eligibility requirements should not be assumed.

For the academic MVP, external bank transfer with payer-submitted evidence and manual recipient confirmation is the recommended settlement approach. Further wallet integration can be reconsidered once provider eligibility and support for the intended use case have been confirmed.
