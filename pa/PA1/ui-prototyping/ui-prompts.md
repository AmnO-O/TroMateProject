# TroMate — UI Prompts (3–6 main screens)

*Elements of Software Engineering — 24A01 · Group 06 · PA1 UI Prototyping (deliverable c)*

Paste-ready prompts for an AI UI tool (v0, Figma AI, etc.). Each prompt is self-contained but assumes the **shared design system** below is prepended.

**Assumptions (adjust if needed):** six MVP screens · S5 drawn as three separate state frames · **bilingual** copy (Vietnamese primary, English subtitle).

---

## 0. Shared design system (prepend to every prompt)

```text
Design a modern, clean, MOBILE-FIRST web app UI for "TroMate" — a shared-housing expense and rent splitter used by Vietnamese roommates. It runs as a Telegram Mini App, so wrap the content in a Telegram-style shell.

CANVAS: 390 × 844 px (iPhone), also show a responsive desktop variant where useful.

STYLE: friendly, trustworthy fintech. Generous white space; rounded 16px cards; soft shadows; system sans-serif (Inter / SF). Clear visual hierarchy; thumb-reachable primary actions at the bottom.

COLORS: primary teal #0D9488; primary-dark #0F766E; background #F8FAFC; surface #FFFFFF; text #0F172A; muted #64748B; success #16A34A; warning #D97706; danger #DC2626; border #E2E8F0.

TYPE: section titles ~18px semibold; labels ~13px muted; body ~15px; big numbers ~28–32px bold.

CURRENCY: Vietnamese đồng, dot thousands separator, e.g. "1.850.000 ₫".

LANGUAGE: Vietnamese primary labels with a small English subtitle underneath (e.g. "Sổ chi tiêu / Ledger").

SHELL: Telegram top bar with a back chevron and the screen title; a bottom tab bar with icons: Trang chủ (Home), Sổ chi (Ledger), Thanh toán (Settle), Báo cáo (Report). Use placeholder avatars for members: An, Bình, Cường, Dung (phòng trọ 4 người).
```

---

## S2 — Dashboard (Trang chủ)

```text
Using the TroMate design system, design the HOME / DASHBOARD screen.

PURPOSE: at-a-glance room finances and quick entry points.

LAYOUT (top → bottom):
1. Telegram top bar: app name "TroMate" + group selector chip "Phòng 302 · 4 người".
2. HERO SUMMARY CARD (teal gradient): "Tổng chi tháng này / This month" with a large amount "3.240.000 ₫"; below it two sub-stats side by side: "Bạn cần trả / You owe" (danger color, 420.000 ₫) and "Bạn được nhận / You receive" (success color, 0 ₫).
3. QUICK ACTIONS row: three tappable buttons — "Thêm chi tiêu" (Add expense), "Chụp hoá đơn" (Scan bill), "Thanh toán" (Settle). Use icons + labels.
4. "Ai nợ ai / Who owes whom" section: a list of 3 rows, each with avatar, name, a short direction ("Bình → An"), amount, and a status chip: "Chờ thanh toán" (amber) or "Đã tất toán" (green).
5. "Hoạt động gần đây / Recent activity": 3 compact rows — icon, description ("Mua nước 50.000 ₫"), payer, and relative date.
6. Bottom tab bar with "Trang chủ" active.

STYLE NOTES: hero card is the focal point; amounts right-aligned; use color only for status (danger/success/amber), keep the rest neutral.
```

---

## S3 — Add Expense / Quick Split (Thêm chi tiêu)

```text
Using the TroMate design system, design the ADD EXPENSE screen (natural-language logging confirmation).

CONTEXT: the bot parsed a chat message and now shows an EDITABLE PREVIEW before saving. Never silently assume who the expense is split among.

LAYOUT (top → bottom):
1. Telegram top bar: "Thêm chi tiêu / Add expense".
2. SOURCE MESSAGE chip (light gray, italic): a chat bubble reading — mua nước 50k chia 3 — labelled "Từ tin nhắn / From message".
3. AMOUNT: large editable amount field showing "50.000 ₫".
4. DESCRIPTION field: "Mua nước / Water" with a small edit pencil.
5. "Người trả / Payer": a horizontal row of selectable avatar chips (An selected, teal ring).
6. "Cách chia / Split method": segmented control with "Chia đều / Even", "Theo tỷ lệ / Percentage", "Tuỳ chọn / Custom" — "Chia đều" selected.
7. "Người tham gia / Beneficiaries": a multi-select list of ALL members with checkboxes and avatars (An, Bình, Cường, Dung). Show checkmarks on the selected ones and a note: "3 người · 16.667 ₫/người". Make clear the user can toggle anyone — this is the critical part.
8. LIVE PREVIEW CARD: summarizes Amount, Payer, Split method, and per-person amount.
9. STICKY BOTTOM BAR: secondary button "Chỉnh sửa / Edit" and primary teal button "Xác nhận / Confirm".

STYLE NOTES: emphasized that the beneficiary list is visible and editable; no hidden assumptions. Keep the confirm button prominent.
```

---

## S4 — Rent Bill Review / OCR (Duyệt hoá đơn tiền nhà)

```text
Using the TroMate design system, design the RENT BILL REVIEW screen for OCR results.

CONTEXT: OCR can be wrong (handwritten readings, faint receipts, misaligned numbers). The treasurer must REVIEW and APPROVE before anything is written to the ledger.

LAYOUT (top → bottom):
1. Telegram top bar: "Duyệt hoá đơn / Review bill".
2. BILL PREVIEW: a thumbnail of the uploaded rent bill photo with a "Xem ảnh / View" overlay; a small badge "Độ tin cậy OCR 92% / OCR confidence 92%".
3. "Thông tin hoá đơn / Bill details" — a FORM with fields:
   - "Kỳ hoá đơn / Billing period": "01/10 – 31/10"
   - "Tiền phòng / Base rent": 2.500.000 ₫
   - "Chỉ số điện cũ / Previous electricity": 1.204
   - "Chỉ số điện mới / Current electricity": 1.348
   - "Đơn giá điện / Electricity unit price": 3.500 ₫/kWh
   - "Lượng nước / Water usage": 8 m³
   - "Đơn giá nước / Water unit price": 20.000 ₫/m³
   - "Phí khác / Surcharges": "Rác 30.000 ₫ · Gửi xe 100.000 ₫"
   Each field has a small edit affordance.
4. COMPUTED LINE: "Tiền điện = (1.348 − 1.204) × 3.500 = 504.000 ₫" shown as a clearly derived subtotal.
5. INCONSISTENCY FLAGS panel (only when applicable): amber/red list rows, e.g. "⚠ Chỉ số điện mới thấp hơn chỉ số cũ / New reading is lower than previous" and "⚠ Thiếu đơn giá nước / Missing water unit price". Include one flagged example so the pattern is visible.
6. TOTAL CARD: "Tổng cộng / Total" = 3.154.000 ₫, with "Chia cho 4 người · 788.500 ₫/người".
7. STICKY BOTTOM BAR: secondary "Chỉnh sửa / Edit" and primary teal "Phê duyệt & ghi sổ / Approve & post".

STYLE NOTES: emphasize human verification — approval is what writes to the ledger; flags must be visually obvious (amber/red) but not alarming.
```

---

## S5 — Settlement (Thanh toán) — three states

Draw these as THREE separate frames (A, B, C) side by side.

```text
Using the TroMate design system, design the SETTLEMENT screen in THREE states. A VietQR scan is NOT proof of payment — only the treasurer confirming receipt (or a verified integration) marks a debt as paid.

FRAME A — "Chờ thanh toán / Awaiting payment"
1. Telegram top bar: "Thanh toán / Settle".
2. Summary: "Cần thu / To collect" 1.850.000 ₫.
3. List of debts, each row: debtor avatar + name, amount, and a teal button "VietQR". 
4. A bottom sheet / modal preview: the VietQR image (placeholder QR), the exact amount "1.850.000 ₫", a prefilled note "TroMate phòng 302 – An", and helper text "Mở app ngân hàng và quét mã / Open your bank app to scan".
5. Status chip per row: "Chờ thanh toán / Awaiting payment" (amber).

FRAME B — "Chờ xác nhận / Awaiting receipt confirmation"
1. Same list, but the debtor row now shows "Đã chuyển tiền? / Marked as transferred" with a timestamp, chip "Chờ xác nhận / Awaiting confirmation" (blue/amber).
2. Treasurer action button on the row: primary "Đã nhận tiền? / Confirm received".
3. A subtle note: "Người chuyển chưa được coi là đã trả cho tới khi xác nhận / Not paid until confirmed."

FRAME C — "Đã tất toán / Settled"
1. The row shows a green check, "Đã tất toán / Settled", the amount, and the confirmation time.
2. A small note under it: "Chỉ tất toán khoản này. Các khoản nợ khác vẫn giữ nguyên / Only this obligation is cleared — other debts remain."
3. Keep other members' still-open debts visible (do not reset the whole balance).

STYLE NOTES: the three states must be visually distinct (amber → blue → green). Make explicit that clearing one debt clears only that obligation.
```

---

## S6 — Monthly Report (Báo cáo tháng)

```text
Using the TroMate design system, design the MONTHLY REPORT screen.

LAYOUT (top → bottom):
1. Telegram top bar: "Báo cáo / Report" + a month selector chip "Tháng 10/2026".
2. HERO: "Tổng chi tháng 10" = 3.240.000 ₫; subtitle "Trung bình/người 810.000 ₫".
3. DONUT CHART: spending by category — Tiền nhà (rent), Điện (electricity), Nước (water), Ăn uống (food), Khác (other) — with a legend showing amounts and percentages.
4. BAR/LINE CHART: "Điện tiêu thụ / Electricity usage" over the last 6 months (kWh), to spot trends.
5. "Chi tiết theo thành viên / Per-member breakdown": list rows (avatar, name, amount paid, amount owed) with a small bar showing each person's share.
6. Footer action: "Xuất / chia sẻ / Export or share" (secondary button).

STYLE NOTES: use the teal palette for charts; keep numbers legible; the report should look shareable in a group chat.
```

---

## S7 — Ledger / History (Sổ chi tiêu)

```text
Using the TroMate design system, design the LEDGER (history) screen.

LAYOUT (top → bottom):
1. Telegram top bar: "Sổ chi tiêu / Ledger".
2. SEARCH + FILTER: a search field and filter chips — "Tất cả / All", "Tiền nhà / Rent", "Điện nước / Utilities", "Ăn uống / Food".
3. HANDOFF ENTRY: a prominent card row "＋ Thêm nhanh / Quick add" and "Chụp hoá đơn / Scan bill".
4. ENTRY LIST grouped by date ("Hôm nay", "12/10"): each row shows a category icon, description ("Mua nước"), payer ("An trả"), amount ("50.000 ₫"), and split info ("chia 3"). One row should be expandable to reveal per-person shares.
5. Bottom tab bar with "Sổ chi" active; a floating action button "＋" if space allows.

STYLE NOTES: dense but readable; amounts right-aligned; category icons color-coded lightly.
```

---

## Notes for generating the sketches

- Prepend the **shared design system** (Section 0) to each screen prompt.
- Generate at **390×844**; a Telegram shell makes it obvious the app lives in the chat.
- After generating, drop the images into `pa/PA1/ui-prototyping/` and reference them in the PA1 UI section.
- Keep the **six** screens for PA1 (S2–S7); S1/S9/S10/S11 are for later.
