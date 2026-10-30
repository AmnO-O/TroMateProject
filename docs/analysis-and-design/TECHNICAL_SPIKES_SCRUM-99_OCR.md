# Technical Spike — OCR for receipts, bills and meters

**Spike ID:** SCRUM-99
**Version:** 1.9
**Status:** `Completed`

**Project:** TroMate
**Sprint / Iteration:** Sprint 2 — Elaboration
**Prepared by:** Hào Nguyễn Gia (HNG)
**Reviewed by:** [Reviewer Name] ([Initials])
**Date created:** 27/10/2026
**Date completed:** 30/10/2026

---

## Revision History

| Date | Version | Description | Author |
|---|---|---|---|
| 27/10 | 1.0 | Initial spike document: Tesseract and PaddleOCR measured on 36 synthetic and 2 real photos; Gemini harness ready | Hào Nguyễn Gia |
| 27/10 | 1.1 | Added 12 more real photos (9 shop receipts, 3 water meters): real set now 14 photos; updated findings and recommendation | Hào Nguyễn Gia |
| 27/10 | 1.2 | Added Gemini Flash-Lite results on the 36 synthetic photos: meets AC1/AC2 there but p95 latency is 27.8 s; updated findings, risks and recommendation | Hào Nguyễn Gia |
| 27/10 | 1.3 | Added Gemini results on the 14 real photos: 9/9 receipts, 3/5 meters; updated acceptance criteria, findings and recommendation | Hào Nguyễn Gia |
| 28/10 | 1.4 | Added 17 more real photos (3 receipts, 14 meters, including 3 meters photographed monthly from January to April 2026): real set now 31 photos. Re-ran every engine on a different laptop | Hào Nguyễn Gia |
| 28/10 | 1.5 | Tested a tuned prompt for Gemini Flash-Lite (`gemini_v2`) aimed at the meter misses; added it to the acceptance criteria and results tables | Hào Nguyễn Gia |
| 28/10 | 1.6 | Added 4 real handwritten bills (personal details blurred): real set now 35 photos. Re-ran both Gemini prompts only. Found that Gemini's answers change between runs; the tuned prompt's gains in v1.5 did not repeat, so it was dropped. Rewrote findings and recommendation | Hào Nguyễn Gia |
| 29/10 | 1.7 | Added a partial test of Gemini Flash (`gemini-3.5-flash`) on meters: 15 of 17 real meters in one run before the free-tier quota ran out; added it to the acceptance criteria, findings, risks and recommendation | Hào Nguyễn Gia |
| 29/10 | 1.8 | Measured Gemini token usage per photo and checked paid-tier prices: Flash-Lite costs about $0.52 per 1,000 scans. Paid-tier latency not measured (needs billing). Re-evaluated risks and recommendation: production needs the paid tier, which conflicts with the zero-cost constraint (SDP 2.2) | Hào Nguyễn Gia |
| 30/10 | 1.9 | Finished the first Gemini Flash run on real meters after the quota reset: meter_real_18 and _19 both read correctly, so Flash read 17 of 19 (89%). Measured Flash thinking tokens on those 2 photos (366–496) and updated the cost estimate | Hào Nguyễn Gia |

---

## 1. Context & Motivation

TroMate lets members log expenses by sending a photo of a receipt, a handwritten bill or an electricity/water meter (Vision v2.0 features F2 and F3). OCR misreads are the project's highest risk (SDP risk R01, exposure 5.6), and the Sprint 4 OCR work (T13, 13 SP) can't be planned until we know which engine reads Vietnamese photos well enough, how fast, and at what cost. This spike measures that before we commit.

---

## 2. Goal

**We need to learn / decide:**

1. Can a free, self-hosted OCR engine read the **final total** of a Vietnamese receipt or handwritten bill, and the **reading** of a meter, accurately enough for TroMate?
2. Does it fit the budget: under 3.5 s per photo (Vision NFR 5.1), zero cost (SDP 2.2), and a confidence signal we can use to trigger manual edit (Vision 5.3)?
3. Which architecture should Sprint 4 build: classic OCR plus our own parser, or a multimodal LLM that returns the fields directly?

**Out of scope:**
- Production-ready implementation, OCR quota/billing logic, the PENDING confirmation UI (T09).
- Line-item extraction quality (we score item lines only indirectly, through the total).
- Spikes produce knowledge, not shippable code.

---

## 3. Timebox

| Field | Value |
|---|---|
| **Max effort** | 3 SP (about 1 person-day) |
| **Deadline** | 28/10/2026 |
| **Assigned to** | Hào Nguyễn Gia (HNG) |

> [!IMPORTANT]
> All real photos were collected by hand. The real photos were sent to the Gemini free tier without blurring (see 6.3). PaddleOCR latencies were measured on two different machines (see 6.2), so the v1.3 and v1.4 numbers are not directly comparable.

---

## 4. Approach / Plan

1. [x] Read documentation and pricing for Tesseract, PaddleOCR PP-OCRv5, Gemini Flash-Lite and Azure Document Intelligence
2. [x] Build two labelled test sets:
   - **Synthetic:** 36 phone-style photos (16 receipts, 10 handwritten bills, 10 meters; easy / medium / hard)
   - **Real:** 35 photos. 12 receipts (VinMart/WinMart, Long Châu, Bách Hóa Xanh, Highlands Coffee, Thanhdo Mart, a restaurant), 4 handwritten bills (2 restaurants, 1 building-supplies shop) and 19 meters (8 electricity including one LCD, 11 water). Nine of the meter photos are 3 meters in our buildings, photographed on several dates between January and April 2026
3. [x] Build one harness that runs every engine on the same images, a VND field parser for classic OCR, and a scorer
4. [x] Run Tesseract and PaddleOCR, each raw and with document pre-processing (page flattening + light correction)
5. [x] Run Gemini Flash-Lite on both sets
6. [x] Try a tuned Gemini prompt (`gemini_v2`) for the meter misses, and re-run both prompts to check the results repeat
7. [~] Test the larger Gemini Flash model on meters: one run on all 19 real meters (17 before the free-tier quota ran out, the last 2 after it reset); second run and synthetic meters still to do
8. [x] Measure Gemini token usage per photo and look up paid-tier prices; paid-tier latency not measured (needs billing)
9. [x] Record findings and update this document

**Proof-of-concept location:** `ocr-spike/` (to go on branch `spike/SCRUM-99-ocr-evaluation`)

How the harness works: each classic engine returns text boxes → `layout.py` rebuilds lines, correcting for photo tilt → `vnd_parser.py` finds the total (`Tổng cộng`, `Thành tiền`, `Cần thanh toán`…, skipping `Tiền khách đưa` / `Tiền thối lại`), the date and the meter reading → `run_spike.py` scores against `labels.csv`. Gemini returns the same fields as JSON and skips the parser.

**About the test sets.** The synthetic images are rendered receipts, bills and meter faces, degraded to look like phone photos (perspective, tilt up to 10°, blur, shadows, low light, crumpling, cut-off edges, JPEG). They include the traps real documents have: four VND formats (`123.000`, `123,000`, `123.000đ`, `123.000 VND`), `k` shorthand, discounts, a cash-given amount larger than the total, red decimal drums, 7-segment LCD digits with ghost segments, and serial/spec numbers next to the reading. Handwriting is rendered with handwriting fonts, which are neater than real writing, so synthetic bill scores are an **upper bound**. The real photos were labelled by eye, zooming into each total and dial. Where a document has two defensible totals (before rounding or a voucher, or with earlier debts added), both are accepted.

---

## 5. Acceptance Criteria

The Gemini Flash-Lite columns use the final run on all 35 real photos. Gemini Flash was tested on meters only, in one run on the 19 real meters, so its column is provisional.

| # | Criterion | Target | Met? (best classic engine: PaddleOCR) | Met? (Gemini Flash-Lite) | Met? (Gemini Flash-Lite + tuned prompt) | Met? (Gemini Flash, meters only, one run) |
|---|---|---|---|---|---|---|
| AC1 | Total amount exact match, receipts + bills | ≥ 90% | ☐ Synthetic 81% (21/26, with prep); real receipts 75% (9/12) | ☑ Synthetic 100% (26/26); real 94% (15/16): receipts 11/12, handwritten bills 4/4 | ☑ Synthetic 100% (26/26); real 94% (15/16): receipts 12/12, handwritten bills 3/4 | n/a: not tested on receipts or bills |
| AC2 | Meter reading exact match | ≥ 90% | ☐ Synthetic 40% (4/10); real 11% (2/19, with prep) | ☐ Synthetic 90% (9/10); real 53% (10/19) | ☐ Synthetic 90% (9/10); real 53% (10/19) | ☐ Real 89% (17/19), one run; synthetic not run yet. Just under the target, needs a second run |
| AC3 | p95 latency per photo, including pre-processing | < 3.5 s | ☑ With photos downscaled to 1280 px: synthetic 1.9 s, real 2.8 s (worst 3.3 s). At full size, real p95 2.9 s but the worst photo took 4.2–5.0 s | ☐ Synthetic 27.8 s; real 9.9–28.6 s depending on the day (free tier) | ☐ Synthetic 28.6 s; real 23.8–24.7 s (free tier) | ☐ Real p50 7.8 s, p95 15.7 s (free tier, one request at a time) |
| AC4 | Cost at 1,000 scans/month | Free | ☑ Self-hosted, free | ☐ Not free in production (see 6.3): paid tier measured at about $0.52 per 1,000 scans | ☐ Slightly more than the original prompt (longer prompt) | ☐ About $2.5–3 per 1,000 scans on the 2 photos where thinking was measured (366–496 tokens), more on photos that think longer; `gemini-3.5-flash` has no published price |
| AC5 | Licence compatible with the project | Apache / MIT | ☑ Tesseract Apache 2.0, PaddleOCR Apache 2.0, RustO binding MIT | n/a: cloud API under Google's terms | n/a: cloud API under Google's terms | n/a: cloud API under Google's terms |
| AC6 | Confidence score separates right from wrong reads | Clear gap | ☐ PaddleOCR 0.96 vs 0.95 synthetic, 0.94 vs 0.84 real; Tesseract 0.87 vs 0.78 synthetic, 0.60 vs 0.51 real | ☐ Synthetic 0.99 vs 0.99; real 0.94 vs 0.96 (higher when wrong) | ☐ Synthetic 1.00 vs 0.99; real 0.94 vs 0.95 (higher when wrong) | ☐ Real 0.94 vs 0.88 (only 2 wrong reads, too few to set a threshold) |
| AC7 | Proof of concept runs end to end | Pass | ☑ `python run_spike.py` | ☑ `python run_spike.py --engines gemini` | ☑ `python run_spike.py --engines gemini_v2` | ☑ `GEMINI_MODEL=gemini-3.5-flash GEMINI_MAX_TOKENS=8192` |

---

## 6. Findings

### 6.1 Summary

**Classic OCR is not good enough.** PaddleOCR PP-OCRv5 with our VND parser read 9 of 12 real receipts (75%) and 81% of synthetic receipts and bills. Its misses on real receipts were parser problems: a total labelled only `TIEN MAT`, a thumb over the total, and a long transaction code taken as the amount. On meters it read only 1–2 of 19 real photos and 40% of synthetic ones, because text OCR can't tell red decimal drums from the reading, often picks up nameplate numbers like "ISO 4064" or "220V", and misses 7-segment LCD digits. Tesseract was worse on everything (4 of 12 real receipts, 0 of 19 meters). Neither engine's confidence score separates right from wrong reads. Both fit the 3.5 s budget once photos are downscaled.

Since both engines were far below the 90% target after 31 real photos, they were not run on the 4 handwritten bills added later: their results could not change the decision, and both did worse on handwriting than on print in the synthetic set.

**Gemini Flash-Lite reads totals very well.** It read 41 of 42 totals across both sets: all 26 synthetic receipts and bills, 11 of 12 real receipts and all 4 real handwritten bills. The bills include two hard cases: one where the written total is 3,000 less than the line items add up to (Gemini returned the written total, which is what the customer was charged), and one where the final total adds two earlier debts to the items on the page. Its one miss was an invented total of 132,700 on a photo that shows only the receipt header.

**Gemini Flash-Lite cannot be trusted with meters.** It read 9 of 10 synthetic meters but only 10 of 19 real ones. In 6 of its 9 real misses it added the red or boxed decimal drum to the end of the reading (83562 for 8356, 599 for 59), which makes the value 10 times too large. It reported 0.95–0.99 confidence on these wrong readings, so a confidence threshold won't catch them. A plausibility check will: for the 3 meters photographed on several dates, every wrong reading after the first one is either lower than, or more than 10 times, the previous month's reading (table in 6.2).

**Gemini is cheap, but not free.** Each photo costs about 1,261 input tokens (the image is billed at a fixed size, so this barely changes from photo to photo) and 48–60 output tokens with Flash-Lite, which does no thinking. At the published paid-tier price that is about $0.52 per 1,000 scans, half the earlier estimate. The free tier is not an option for production, though: Google may use free-tier inputs to improve its products, Flash's free quota ran out after about 20 requests, and one test project was refused the free tier for every model. Paid-tier latency could not be measured without billing.

**Gemini is slow and its speed varies.** On the free tier, p95 latency was 27.8 s on the synthetic set and between 9.9 s and 28.6 s on the real set, depending on the day. That is far over the 3.5 s budget.

**A tuned prompt did not help.** A longer prompt (`gemini_v2`) was written that explains which drums are decimals, how to read a drum caught between two digits, which nameplate numbers to ignore and how to read a rotated photo. It also makes the model write the whole-number digits and the decimal digits separately before giving the reading. It still read 10 of 19 real meters, and it read one handwritten bill wrong (3,637,800 for 36,378,000, misreading the writer's `a0` shorthand for `000`). The transcribed digits show why: the model does list the decimal drum separately, but it still miscounts the drums. It often copies the decimal digit into the whole-number part too (`000002` + `2` for a meter at 0), or drops a real digit. A better prompt can't fix that.

**Gemini's answers change between runs.** Both prompts were run twice on the same 31 receipts and meters with temperature 0, and 9 of the 62 answers changed. In the first run the tuned prompt seemed to fix two meters; in the second run both were wrong again and two other meters came out right. Small differences between prompts are therefore just noise, and any comparison needs at least two runs.

**Gemini Flash reads meters much better (one run).** The larger Flash model (`gemini-3.5-flash`), with the original prompt, read 17 of 19 real meters correctly (89%), against 10 of 19 for Flash-Lite. It never added a decimal drum to the reading: it read 794, 8356, 8387, 8404, 59 and 1 where Flash-Lite read 7944, 83562, 833872, 84045, 599 and 10, and it also got the all-zero Gelex meter and the drum caught mid-roll right. Its two misses are the hardest photos in the set, both photographed sideways: 482 for 141 (low light, missed by every engine) and 57 for 578 (fogged glass, a dropped digit). It was not slower than Flash-Lite (p50 7.8 s, p95 15.7 s). The free-tier quota for Flash ran out after about 20 requests, so the first run was finished a day later (meter_real_18 and _19), and the second run and the synthetic meters are still to do (next step 3).

### 6.2 Detailed Results

Synthetic set, 36 photos (results in `results/summary.md`; per-image CSVs and raw text in `results/`):

| Engine | Receipts total | Bills total | Meter reading | Easy | Medium | Hard | Dates | p50 ms | p95 ms | Confidence when right / wrong |
|---|---|---|---|---|---|---|---|---|---|---|
| Gemini Flash-Lite (`gemini-3.5-flash-lite`) | 16/16 (100%) | 10/10 (100%) | 9/10 (90%) | 14/14 (100%) | 14/14 (100%) | 7/8 (88%) | 22/22 (100%) | 12740 | 27776 | 0.99 / 0.99 |
| Gemini Flash-Lite + tuned prompt (`gemini_v2`) | 16/16 (100%) | 10/10 (100%) | 9/10 (90%) | 14/14 (100%) | 14/14 (100%) | 7/8 (88%) | 22/22 (100%) | 20544 | 28624 | 1.00 / 0.99 |
| PaddleOCR PP-OCRv5 | 10/16 (62%) | 10/10 (100%) | 4/10 (40%) | 11/14 (79%) | 10/14 (71%) | 3/8 (38%) | 20/22 (91%) | 1114 | 1611 | 0.96 / 0.96 |
| PaddleOCR + pre-processing | 12/16 (75%) | 9/10 (90%) | 2/10 (20%) | 10/14 (71%) | 10/14 (71%) | 3/8 (38%) | 20/22 (91%) | 842 | 1894 | 0.96 / 0.95 |
| Tesseract 5 (`vie+eng`) | 9/16 (56%) | 8/10 (80%) | 0/10 (0%) | 10/14 (71%) | 6/14 (43%) | 1/8 (12%) | 15/22 (68%) | 574 | 975 | 0.87 / 0.78 |
| Tesseract + pre-processing | 9/16 (56%) | 6/10 (60%) | 0/10 (0%) | 10/14 (71%) | 5/14 (36%) | 0/8 (0%) | 19/22 (86%) | 718 | 1254 | 0.81 / 0.72 |

Real set (results in `results/real/`). Gemini was run on all 35 photos; Tesseract and PaddleOCR on the 31 receipts and meters only (see 6.1):

| Engine | Receipts total | Bills total | Meter reading | Dates | p50 ms | p95 ms | Confidence when right / wrong |
|---|---|---|---|---|---|---|---|
| Gemini Flash-Lite | 11/12 (92%) | 4/4 (100%) | 10/19 (53%) | 11/12 (92%) | 11132 | 24459 | 0.94 / 0.96 |
| Gemini Flash-Lite + tuned prompt | 12/12 (100%) | 3/4 (75%) | 10/19 (53%) | 11/12 (92%) | 10598 | 23819 | 0.94 / 0.95 |
| PaddleOCR PP-OCRv5 | 9/12 (75%) | not run | 1/19 (5%) | 11/12 (92%) | 1418 | 2858 | 0.94 / 0.84 |
| PaddleOCR + pre-processing | 8/12 (67%) | not run | 2/19 (11%) | 10/12 (83%) | 1176 | 3112 | 0.94 / 0.76 |
| Tesseract 5 | 4/12 (33%) | not run | 0/19 (0%) | 2/12 (17%) | 595 | 986 | 0.60 / 0.51 |
| Tesseract + pre-processing | 4/12 (33%) | not run | 0/19 (0%) | 5/12 (42%) | 725 | 1520 | 0.50 / 0.48 |

Both Gemini prompts missed the date on receipt_real_11 (27/05/2025 against a label of 27/06/2025). The month on that photo is too blurry to tell which is right, so this miss is unresolved.

Per photo:

| Photo | Truth | Gemini | Gemini + tuned prompt | PaddleOCR | PaddleOCR + prep | Tesseract |
|---|---|---|---|---|---|---|
| receipt_real_01 VinMart+ | 49,000 | 49,000 ✓ | 49,000 ✓ | 49,000 ✓ | 49,000 ✓ | none ✗ |
| receipt_real_02 WinMart+ | 237,576 | 237,576 ✓ | 237,576 ✓ | 237,576 ✓ | 237,576 ✓ | 34,280 ✗ |
| receipt_real_03 WinMart, 400,000 voucher | 68,097 (or 468,097) | 68,097 ✓ | 68,097 ✓ | 68,097 ✓ | 68,097 ✓ | 488,087 ✗ |
| receipt_real_04 Long Châu, second invoice in frame | 13,500 | 13,500 ✓ | 13,500 ✓ | 13,500 ✓ | 13,500 ✓ | 13,500 ✓ |
| receipt_real_05 Long Châu, thumb over the total | 45,000 | 45,000 ✓ | 45,000 ✓ | 25,000 ✗ | 25,000 ✗ | none ✗ |
| receipt_real_06 Bách Hóa Xanh, total cut off | no total | none ✓ | none ✓ | none ✓ | none ✓ | none ✓ |
| receipt_real_07 Bách Hóa Xanh, header only | no total | 132,700 ✗ | none ✓ | none ✓ | none ✓ | none ✓ |
| receipt_real_08 Bách Hóa Xanh, rounded card payment | 187,500 (or 187,954) | 187,954 ✓ | 187,954 ✓ | 187,954 ✓ | 187,954 ✓ | none ✗ |
| receipt_real_09 Bách Hóa Xanh, rounded payment | 450,000 (or 450,430) | 450,000 ✓ | 450,000 ✓ | 450,430 ✓ | 450,430 ✓ | 459,430 ✗ |
| receipt_real_10 restaurant, total labelled only `TIEN MAT` | 537,000 | 537,000 ✓ | 537,000 ✓ | none ✗ | none ✗ | none ✗ |
| receipt_real_11 Highlands Coffee | 39,000 | 39,000 ✓ | 39,000 ✓ | 39,000 ✓ | 3,900 ✗ | 39,000 ✓ |
| receipt_real_12 Thanhdo Mart, crumpled, cash and change printed | 315,580 | 315,580 ✓ | 315,580 ✓ | 2726021012135817 ✗ (transaction code) | 109,000 ✗ (first item) | none ✗ |
| bill_real_01 Hạ Long boat restaurant, one amount overwritten | 6,530,000 | 6,530,000 ✓ | 6,530,000 ✓ | not run | not run | not run |
| bill_real_02 building supplies, written total ≠ sum of lines | 10,787,000 | 10,787,000 ✓ | 10,787,000 ✓ | not run | not run | not run |
| bill_real_03 building supplies, earlier debts added | 36,378,000 (or 14,400,000) | 36,378,000 ✓ | 3,637,800 ✗ | not run | not run | not run |
| bill_real_04 restaurant, "+ 50" added below the items | 690,000 | 690,000 ✓ | 690,000 ✓ | not run | not run | not run |
| meter_real_01 EMIC electricity | 17924 | 17924 ✓ | 17924 ✓ | 7924 ✗ | 79247 ✗ | none ✗ |
| meter_real_02 EMIC electricity | 17805 | 17805 ✓ | 17805 ✓ | 178055 ✗ | 17805 ✓ | 72846 ✗ (sticker) |
| meter_real_03 Actaris water | 794 | 7944 ✗ | 7944 ✗ | 141715 ✗ | none ✗ | none ✗ |
| meter_real_04 Elster water | 95 | 95 ✓ | 95 ✓ | 205007 ✗ | 1 ✗ | none ✗ |
| meter_real_05 water | 1 | 10 ✗ | 10 ✗ | 110102 ✗ | none ✗ | none ✗ |
| meter_real_06 water, sideways, low light | 141 | 944 ✗ | 1441 ✗ | 18163 ✗ | none ✗ | none ✗ |
| meter_real_07 Gelex EMIC electricity | 0 | 2 ✗ (1/10 drum) | 2 ✗ (1/10 drum) | 220181 ✗ | 22018 ✗ | 2018 ✗ (year) |
| meter_real_08 EMIC electricity | 99985 | 99985 ✓ | 99985 ✓ | 22010 ✗ | 22010 ✗ | 16202 ✗ (stamp) |
| meter_real_09 EMIC electronic LCD | 33 | 33 ✓ | 33 ✓ | 190000 ✗ | 130001 ✗ | none ✗ |
| meter_real_10 Zermat water, last drum mid-roll | 0 | 4 ✗ | 0 ✓ | 0 ✓ | 60008 ✗ | 4064 ✗ (ISO 4064) |
| meter_real_11 water meter A, 29/01, sideways | 59 | 599 ✗ | 599 ✗ | 599 ✗ | 4064 ✗ (ISO 4064) | none ✗ |
| meter_real_12 water meter B, 29/01, sideways, fogged | 578 | 578 ✓ | 578 ✓ | 5178 ✗ | none ✗ | none ✗ |
| meter_real_13 EMIC electricity, 01/03, glare | 8356 | 83562 ✗ | 83562 ✗ | 140220 ✗ | 835531 ✗ | none ✗ |
| meter_real_14 water meter B, 01/03, rust | 579 | 579 ✓ | 579 ✓ | 450406 ✗ | 51798 ✗ | none ✗ |
| meter_real_15 water meter A, 28/03, sideways | 60 | 60 ✓ | 601 ✗ | 4064 ✗ (ISO 4064) | 60 ✓ | none ✗ |
| meter_real_16 EMIC electricity, 28/03 | 8387 | 833872 ✗ | 83387 ✗ | 22001 ✗ | 22001 ✗ | none ✗ |
| meter_real_17 water meter B, 28/03, tiny dial in wide shot | 581 | 581 ✓ | 581 ✓ | none ✗ | none ✗ | none ✗ |
| meter_real_18 EMIC electricity, 30/04, rotated 60°, glare | 8404 | 84045 ✗ | 84045 ✗ | none ✗ | none ✗ | none ✗ |
| meter_real_19 water meter B, 30/04, rust | 582 | 582 ✓ | 582 ✓ | none ✗ | none ✗ | none ✗ |

Real receipts did better than synthetic ones because thermal receipts print the label and amount close together on one line, and most of these photos are only slightly tilted. Two product questions came up that OCR can't answer: whether the expense is the total before a voucher or the amount actually paid (receipt_real_03), and whether to use the rounded payment or the exact total (Bách Hóa Xanh). The validator should show both and let the payer pick.

**Checking a reading against last month.** For the 3 meters photographed on several dates (meter_real_11–19), the first reading is assumed to be confirmed by the member, and any later Gemini reading is flagged if it is lower than the previous one or more than 10 times it:

| Meter | Readings by date (truth → Gemini) | Gemini wrong | Flagged by the check |
|---|---|---|---|
| EMIC electricity | 8356 → 83562; 8387 → 833872; 8404 → 84045 | 3 of 3 | the 2 after the first |
| Water meter A | 59 → 599; 60 → 60 | 1 of 2 (the first) | none (nothing to compare the first with) |
| Water meter B | 578, 579, 581, 582, all read correctly | 0 of 4 | none (no false alarms) |

**Repeatability.** Both Gemini prompts were run twice on the same photos with the same settings (temperature 0). These answers changed:

| Photo | Truth | Prompt | Run 1 | Run 2 |
|---|---|---|---|---|
| receipt_real_07 (header only) | no total | original | none ✓ | 132,700 ✗ |
| meter_real_03 | 794 | original / tuned | 79447 ✗ / 794 ✓ | 7944 ✗ / 7944 ✗ |
| meter_real_13 | 8356 | tuned | 8356 ✓ | 83562 ✗ |
| meter_real_10 | 0 | tuned | 4 ✗ | 0 ✓ |
| meter_real_12 | 578 | tuned | 57 ✗ | 578 ✓ |
| meter_real_06 | 141 | original / tuned | 1421 ✗ / 1449 ✗ | 944 ✗ / 1441 ✗ |
| meter_real_10 | 0 | original | 9 ✗ | 4 ✗ |

The tables above show run 2.

**Gemini Flash on meters.** One run of `gemini-3.5-flash` with the original prompt, on the real meters only (results in `results/flash_real_run1/`). The free-tier quota ran out at meter_real_18, so meter_real_18 and meter_real_19 were read on 30/10, after it reset, with the same settings:

| Photo | Truth | Gemini Flash | Gemini Flash-Lite (run 2) |
|---|---|---|---|
| meter_real_01 EMIC electricity | 17924 | 17924 ✓ | 17924 ✓ |
| meter_real_02 EMIC electricity | 17805 | 17805 ✓ | 17805 ✓ |
| meter_real_03 Actaris water | 794 | 794 ✓ | 7944 ✗ |
| meter_real_04 Elster water | 95 | 95 ✓ | 95 ✓ |
| meter_real_05 water | 1 | 1 ✓ | 10 ✗ |
| meter_real_06 water, sideways, low light | 141 | 482 ✗ | 944 ✗ |
| meter_real_07 Gelex EMIC electricity | 0 | 0 ✓ | 2 ✗ |
| meter_real_08 EMIC electricity | 99985 | 99985 ✓ | 99985 ✓ |
| meter_real_09 EMIC electronic LCD | 33 | 33 ✓ | 33 ✓ |
| meter_real_10 Zermat water, last drum mid-roll | 0 | 0 ✓ | 4 ✗ |
| meter_real_11 water meter A, 29/01, sideways | 59 | 59 ✓ | 599 ✗ |
| meter_real_12 water meter B, 29/01, sideways, fogged | 578 | 57 ✗ | 578 ✓ |
| meter_real_13 EMIC electricity, 01/03, glare | 8356 | 8356 ✓ | 83562 ✗ |
| meter_real_14 water meter B, 01/03, rust | 579 | 579 ✓ | 579 ✓ |
| meter_real_15 water meter A, 28/03, sideways | 60 | 60 ✓ | 60 ✓ |
| meter_real_16 EMIC electricity, 28/03 | 8387 | 8387 ✓ | 833872 ✗ |
| meter_real_17 water meter B, 28/03, tiny dial in wide shot | 581 | 581 ✓ | 581 ✓ |
| meter_real_18 EMIC electricity, 30/04, rotated 60°, glare | 8404 | 8404 ✓ | 84045 ✗ |
| meter_real_19 water meter B, 30/04, rust | 582 | 582 ✓ | 582 ✓ |
| **Total** | | **17/19 (89%)** | **10/19 (53%)** |

Flash is a thinking model, and its reasoning counts against the reply's token cap. The first Flash attempt used the 512-token cap set for Flash-Lite, and 13 of 19 replies were cut off before the answer, so the cap is now configurable (`GEMINI_MAX_TOKENS`) and was set to 8192 for this run. Requests were sent one at a time.

**Cost and token usage.** Input tokens were counted with the `countTokens` endpoint for all 35 real photos (prompt + photo; the JSON schema adds a few more), and output tokens were read from real Flash-Lite replies on 9 photos (3 receipts, 2 bills, 4 meters). Results are in `results/token_usage.json`; the harness now saves token usage with every Gemini reply. Prices are the published Standard paid-tier prices (R1):

| | Gemini Flash-Lite (`gemini-3.5-flash-lite`) | Gemini Flash (`gemini-3.5-flash`) |
|---|---|---|
| Input tokens per photo | 1,241–1,292 (mean 1,261), measured | Same, measured |
| Output tokens per photo | 48–60, measured; no thinking tokens | 28–29 for the answer plus 366–496 thinking tokens, measured on 2 meters (meter_real_18, _19); 13 of 19 meters overflowed a 512-token cap on the first attempt, so some photos think longer |
| Price per 1M tokens | $0.30 input, $2.50 output | Not published for this model; listed Flash models (3.6, 3.8) cost $0.75 input, $3.75 output until 31/12/2026, then $1.50 and $7.50 |
| Cost per scan | about $0.0005 | about $0.0025–0.003 on the 2 measured photos; more on photos that think longer |
| **Cost per 1,000 scans** | **about $0.52** | **about $2.5–3** on the measured photos (double from 2027) |

The earlier estimate of about $1 per 1,000 scans assumed 1,500 input and 150 output tokens; the real counts are lower. Free-tier latency in this measurement was 4.7–16.5 s per photo (p50 about 7 s). Paid-tier latency is still unknown. Flash's thinking tokens were read from the usage data of the meter_real_18 and _19 replies; 2 photos is too few to fix a price, so the Flash figure is a rough estimate.

**How Gemini was run.** One request per photo with the prompt and JSON schema in `engines.py`, temperature 0, 2 requests at a time, on the free tier. The first schema also asked for line items, but on some receipts Gemini kept listing items until it hit the output limit and the JSON was cut off. Items are not scored, so they were removed and replies were capped at 512 tokens. With 5 requests at a time the free tier returned 429 (per-minute quota), so the harness uses 2 and backs off on 429. Latency is measured per request, so it includes Google's queueing.

The tuned prompt (`GEMINI_V2_PROMPT` in `engines.py`) uses the same model and settings. Its schema asks for `meter_type`, `whole_digits` and `decimal_digits` before `meter_reading`, and the harness takes the reading from `whole_digits`. It was written after looking at the real meter misses, so the real set is not an independent test of it; the synthetic set is, and there it scored the same as the original prompt.

**Hardware.** The first PaddleOCR and Tesseract runs were on a 4-core Intel Xeon 2.1 GHz; the 31-photo real run was on an AMD Ryzen 5 5500U laptop (6 cores). Peak memory: PaddleOCR about 330 MB, Tesseract about 60 MB. Models: PaddleOCR detection + Latin recognition 13 MB, Tesseract `vie.traineddata` 0.5 MB.

**What went wrong, by failure type:**

| Failure | Example | Engines | Fixable by us? |
|---|---|---|---|
| Label and amount end up on different rows on tilted photos, or two labels share a row | `THÀNH TIỀN: Tổng tiền hàng: 314.500đ` (receipt_05) | PaddleOCR, Tesseract | Partly: the tilt-aware line rebuild in the harness recovers some; perspective-heavy photos still fail |
| Total confused with cash handed over | `500009` read from the `Tiền khách đưa` row (receipt_12) | Tesseract | Parser rules help, but they depend on rows being right |
| Red or boxed decimal drums read as an extra digit | `389398` for 38939 (meter_07), `178055` on a real meter; Gemini `27493` for 2749 (meter_09), `7944` for 794 (meter_real_03), `83562` for 8356 (meter_real_13) | All engines except Gemini Flash (Gemini Flash-Lite: 1 of 10 synthetic, 6 of 19 real; Gemini Flash: 0 of 19 real) | No for PaddleOCR: text OCR has no colour; it needs a separate digit-window detector. Gemini Flash-Lite does it at 0.95–0.99 confidence and a tuned prompt didn't stop it; Gemini Flash didn't do it in one run; a check against last month's reading catches it |
| Nameplate numbers taken as the reading | `4064` from "ISO 4064", `22010`/`22001` from "220V", "5(20)A", "2001", year `2018`, inspection sticker `72846`/`16202`, `1000 imp/kWh` | PaddleOCR, Tesseract | Partly: add these to the parser's nameplate filter |
| 7-segment LCD digits not detected | meter_02, meter_04: no digits at all | PaddleOCR, Tesseract | Needs a dedicated 7-segment model |
| Total invented when there is none | 132,700 on a receipt header with no total (receipt_real_07) | Gemini | Partly: if the line items don't add up to the total, ask the member |
| Vietnamese tone marks lost | `Nuóc suôi` for `Nước suối` | PaddleOCR | No: the PP-OCRv5 Latin dictionary covers only 47 of 146 Vietnamese letters; fine for amounts, unusable for item names |
| Hard photos (crumpled, dark, cut off) | 0–3 of 8 correct | PaddleOCR, Tesseract | Pre-processing didn't help overall |

### 6.3 Risks & Limitations Discovered

| Risk | Severity (H/M/L) | Mitigation |
|---|---|---|
| Production cannot run on the Gemini free tier: Google may use free-tier inputs to improve its products, Flash's free quota ran out after about 20 requests in a day, and one team member's new project was refused the free tier for every model. The paid tier breaks the zero-cost constraint (SDP 2.2) | H | The measured cost is small: about $0.52 per 1,000 scans with Flash-Lite. The team needs to approve a small OCR budget (next step 2). If it is not approved, the zero-cost option is PaddleOCR for receipts with mandatory review and manual meter entry |
| Gemini Flash-Lite reads only 10 of 19 real meters (53%), mostly by adding the decimal drum, and a tuned prompt didn't help | H | Make F3 photo-assisted: Gemini prefills the reading, the app checks it against last month's, and the member confirms it. Gemini Flash read 17 of 19 real meters in one run; confirm it with a second run before switching meters to Flash (next step 3) |
| Gemini latency breaks the 3.5 s budget (Vision NFR 5.1): p95 9.9–28.6 s on the free tier, varying by day; paid-tier latency not measured | H | Run OCR in the background: save the photo, show the expense as "reading…" and fill the PENDING card when the result arrives. Measure paid-tier latency (next step 1) and agree whether NFR 5.1 applies to the upload or the OCR result (next step 2) |
| Confidence scores don't flag wrong reads (Flash-Lite averages 0.96 on wrong reads and 0.94 on right ones), so "low confidence → manual edit" (Vision 5.3) can't rely on them | H | Keep every OCR result PENDING with [Edit] (already in SDP). Add our own checks: line items must add up to the total, and a meter reading must be at least last month's and less than 10 times it |
| Too few real receipts (12) and handwritten bills (4); synthetic handwriting is neater than real. Some photos (meter_real_07–10, receipt_real_10–11, all 4 bills) look like web images rather than photos from our own phones | H | Collect real bills and more receipts from our rooms and re-run the harness before Sprint 4 |
| Gemini's answers change between runs even at temperature 0 (9 of 62 answers changed between two runs of both prompts) | M | Compare prompts or models over at least two runs before choosing; never auto-accept a result |
| Gemini replies can be cut off: Flash-Lite when it lists too many line items, Flash when its thinking uses up the output cap (13 of 19 replies on the first Flash attempt) | M | Ask only for the fields the app needs, set the output cap per model (`GEMINI_MAX_TOKENS`), and treat an unparsable reply as a failed read that falls back to PaddleOCR or manual entry |
| Gemini prices change: `gemini-3.5-flash` has no published price, and the listed Flash models double in price on 1 January 2027 | M | Budget with 2027 prices; use a model that is on the pricing page; Flash-Lite stays cheap either way |
| Real photos include names, phone numbers and bank details | M | Blur them before committing `data/real/` (done for the two building-supplies bills; still needed for the cashier's name on receipt_real_12) |
| The real photos were sent to the Gemini free tier during the spike | M | Accepted for this spike. Blur any further real photos before sending them; production uses the paid tier, where inputs are not used to improve Google's products |
| Free-tier rate limits and cold starts (SDP R08); Gemini returned 429 at 5 requests at a time during the spike | M | Queue OCR jobs, back off on 429, warm up before demos, keep a local fallback engine |
| Large phone photos push PaddleOCR past the budget (4.8 s on 1346×2400) | M | Downscale to 1280 px on the long side before OCR |
| PaddleOCR needs about 330 MB RAM per process, tight on 512 MB free hosting | M | Run it only as a fallback with one worker, or use Tesseract as the low-memory fallback |
| Tesseract Vietnamese data shipped by Ubuntu is the 2019 "fast" model | L | Try `tessdata_best/vie` if Tesseract stays as a fallback |

### 6.4 Alternatives Considered

| Option | Pros | Cons | Decision |
|---|---|---|---|
| Multimodal LLM (Gemini Flash-Lite) returns JSON fields | Best measured on totals: 41 of 42 across both sets, including 4/4 real handwritten bills; reads layout, colour and handwriting together; no parser to maintain; cheapest Gemini model (about $0.52 per 1,000 scans), which matters because receipts are the most frequent scan | p95 9.9–28.6 s on the free tier; misses the meter target on real photos (10/19), mostly by adding the decimal drum; answers vary between runs; cloud dependency; needs the paid tier in production; output must be validated | ✅ Chosen for receipts and bills, run in the background because of latency. Not used for meters |
| Gemini Flash (`gemini-3.5-flash`) for meters | 17 of 19 real meters in one run, against 10 for Flash-Lite; no decimal-drum errors; no slower than Flash-Lite | Only one run, synthetic meters not run; tiny free-tier quota, so it needs the paid tier; about 5 times Flash-Lite's price, about $2.5–3 per 1,000 scans (estimate from 2 photos); thinking tokens need a larger output cap | ✅ Chosen for meters. A member sends only 1–2 meter photos a month on average, so the higher price adds well under $0.01 per member a month. Readings stay user-confirmed and checked against last month's. |
| Gemini Flash-Lite with a tuned prompt (`gemini_v2`) | Same receipt results | Same meter score as the original prompt (10/19) over two runs; misread one handwritten bill; longer prompt costs more | ❌ Not adopted: no measurable gain |
| PaddleOCR PP-OCRv5 + our parser | Best classic engine; 75% on real receipts; free; self-hosted | 5–11% on real meters; weak confidence signal; loses Vietnamese tone marks; 330 MB RAM | ✅ Fallback for receipts if Gemini is unavailable |
| Tesseract 5 + our parser | Light (60 MB); keeps tone marks on clean print | 4 of 12 real receipts; 0 of 29 meters (synthetic + real) | ❌ Rejected |
| Azure Document Intelligence (receipt model) | Returns receipt fields directly | Receipt locales are English only; amounts typed as USD | ❌ Rejected after desk research |
| VietOCR recogniser | Trained for Vietnamese text | Recogniser only; needs PaddleOCR detection plus PyTorch | ❌ Not now; revisit if item names matter |

---

## 7. Recommendation

- **⚠️ Proceed with conditions.** Build Sprint 4 OCR (T13) as **photo → Gemini Flash-Lite (original prompt, paid tier) → JSON fields → validation → PENDING card with [Edit]**, with PaddleOCR + VND parser as the fallback. Gemini meets the 90% target for totals: 26/26 synthetic and 15/16 real, including all 4 handwritten bills.
- **Use the paid tier, and get the budget approved.** The free tier is fine for testing but not for production (privacy terms, quotas, availability). The paid tier costs about $0.52 per 1,000 scans with Flash-Lite, well under $1 a month at the planned 1,000 scans a month, but it breaks the zero-cost constraint in SDP 2.2, so the team needs to approve it (next step 2). If it is not approved, use the zero-cost option: PaddleOCR for receipts (75% on real receipts) with mandatory review, and manual meter entry with the photo attached as evidence.
- **Make the meter scanner photo-assisted.** Flash-Lite does not meet the target for meters (9/10 synthetic, 10/19 real): Gemini prefills the reading, the app flags a reading that is lower than last month's or more than 10 times it, and the member always confirms it. Gemini Flash read 17 of 19 real meters in one run (89%). If a second run confirms that (next step 3), meters should use Flash. At an estimated $2.5–3 per 1,000 scans and a few meter photos per room per month, that adds only cents a month.
- **Run OCR in the background.** Gemini can't meet the 3.5 s budget as a blocking call (p95 up to 28.6 s on the free tier; paid tier not measured), so the member sends the photo, the expense appears as "reading…", and the PENDING card fills in when the result arrives.

Whichever engine we use, every OCR result stays PENDING and is never auto-accepted (already in SDP 2.2), and the validator checks the total against the line items and the meter reading against last month's.

**Estimated implementation effort** (if proceeding): ~5 person-days (Gemini client + schema + validation 2 days, PaddleOCR fallback service 2 days, test set and regression 1 day), within the 13 SP planned for T13.

---

## 8. References

| Ref | Description | URL / Path |
|---|---|---|
| R1 | Gemini API pricing, checked 29/10/2026 (Flash-Lite $0.30 / $2.50 per 1M tokens; Flash $0.75 / $3.75 until 31/12/2026; free-tier inputs used to improve products) | https://ai.google.dev/gemini-api/docs/pricing |
| R2 | PaddleOCR PP-OCRv5 multilingual models (Latin model lists Vietnamese) | https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html |
| R3 | Azure Document Intelligence prebuilt language support (receipt locales English only) | https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/language-support/prebuilt?view=doc-intel-4.0.0 |
| R4 | Tesseract 5.3.4 with Ubuntu `tesseract-ocr-vie` data | https://github.com/tesseract-ocr/tesseract |
| R5 | PP-OCRv5 models and Node binding used in the PoC (`@rustors/node`, `@rustors/model-ppocrv5-mobile`, `@rustors/model-ppocrv5-latin` 0.3.2) | https://www.npmjs.com/package/@rustors/node |
| R6 | Proof-of-concept code, test set and results | https://github.com/AmnO-O/TroMateProject/tree/main/src/ocr-spike |
| R7 | TroMate Vision v2.0 and SDP v2.0 | project files |
