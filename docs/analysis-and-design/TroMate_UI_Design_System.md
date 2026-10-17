# TroMate Design System — Agent Guide

Use this file to keep every new TroMate screen consistent with the existing designs. It describes the Telegram Mini App and bot UI, based on the Phòng 203 mockups and the SCRUM-69 and SCRUM-77 Figma work.

**Source of truth:** Figma file `TroMate – SCRUM-77 Settlement & VietQR`
- URL: https://www.figma.com/design/7oxDhK6PSNrlVIDGpBlLMK
- File key: `7oxDhK6PSNrlVIDGpBlLMK`
- Pages:
  - `SCRUM-77 · Settlement & VietQR` (id `0:1`). This page also holds the **Components** library frame (`2:37`).
  - `SCRUM-69 · Room Dashboard` (id `16:213`).

If this document and the Figma file ever disagree, the Figma variables and styles win. Update this file to match.

> ## ⛔ Do not edit existing screens
> The existing screens and pages are approved baselines for SCRUM-69 and SCRUM-77. **Do not modify, move, rename, restyle, re-order or delete them**, or any layer inside them. This also covers their labels and the spec boards above them. For example, the protected screens are:
> - `SCRUM-77 · Settlement & VietQR` page: screens 01–06 and the `SCRUM-77 · Spec` board.
> - `SCRUM-69 · Room Dashboard` page: screens 01–04 and the `SCRUM-69 · Spec` board.
>
> Also do **not** change the shared foundations they depend on, because any change carries through to every existing screen. These are:
> - the `TroMate` color variables
> - the text styles
> - the existing components (Button, StatusChip, Badge, Avatar, TabBar, Icon/*)
>
> **What you may do:**
> - Create new screens on a **new page** (or to the right of existing frames, without overlapping them).
> - Place **instances** of the existing components.
> - Add **new** variables, styles or components when something is truly missing. Use new names and leave existing ones untouched.
> - To show a change to an existing screen, **duplicate** it into a new frame with a suffix such as `— v2 (proposal)`, edit only the copy, and leave the original as is.
>
> If a task seems to need an existing screen or foundation edited, stop and ask the human first.

---

## 1. Design principles

1. **Calm and friendly, never awkward.** Money between roommates is sensitive. Use a warm canvas, soft cards and a polite tone. Never write anything that sounds like scolding.
2. **One clear next action per state.** Every screen or state card has exactly one Primary button. Supporting actions use Secondary or Ghost buttons.
3. **Status is never shown by color alone.** Always pair a color with a text label and an icon. Examples: chip "Chưa trả" with an alert icon, "Chờ xác nhận" with a clock, "Đã xác nhận" with a check.
4. **Exact numbers, big and readable.** Amounts are always exact (`250.000đ`). Never round or abbreviate them.
5. **Mobile-first, Vietnamese-first.** Vietnamese is the default UI language. Its text runs longer than English, so layouts must stretch to fit it.

---

## 2. Color tokens

All colors are Figma variables in the collection **`TroMate`** (mode `Light`).

- Always bind to a variable. Never hard-code hex values in Figma.
- In code, use the same names as CSS custom properties, e.g. `--brand-teal`.

### Surfaces and text
| Token | Hex | Use |
|---|---|---|
| `bg/canvas` | `#F8F5F0` | App/screen background (warm off-white) |
| `bg/surface` | `#FFFFFF` | Cards, bottom bars, tab bar |
| `bg/subtle` | `#F4F0E9` | Inset boxes inside cards (copy fields, bank box, spec cells) |
| `bg/chat` | `#EEF3F0` | Telegram chat preview, setup step number circles |
| `border/default` | `#ECE5DA` | 1px card borders, dividers, top border of bars |
| `text/ink` | `#1E2B2A` | Primary text, icons |
| `text/muted` | `#6E716D` | Secondary text, labels, captions |
| `text/onPrimary` | `#FFFFFF` | Text and icons on teal |
| `icon/bg` | `#F1ECE4` | Neutral icon circles (list rows, inactive stats) |
| `state/disabled` | `#ECE8E1` | Disabled button fill |

### Brand
| Token | Hex | Use |
|---|---|---|
| `brand/teal` | `#1F6F68` | Primary buttons, links ("Xem tất cả"), active tab, the "in progress" badge |
| `brand/tealSoft` | `#E2EEEB` | Secondary buttons, copy actions, active room-fund icon circle |

### Status (semantic)
| Meaning | Strong | Soft bg | Border | Used for |
|---|---|---|---|---|
| Owe / unpaid / needs payment | `status/orange` `#BF5520` | `status/orangeSoft` `#FBE7DB` | `status/orangeBorder` `#F4D6C4` | "Bạn cần trả", "Chưa trả", "Cần thanh toán" |
| Waiting / new | `status/amber` `#8A6100` | `status/amberSoft` `#FBF0C9` | — | "Chờ xác nhận", "Phòng mới" |
| Receive / paid / closed | `status/green` `#2E7D4F` | `status/greenSoft` `#E1F0E5` | `status/greenBorder` `#CDE5D4` | "Cần thu về", "Đã trả", "Đã xác nhận", "Đã chốt sổ" |
| Error | `status/red` `#B3261E` | `status/redSoft` `#FBE4E1` | — | QR generation error, destructive actions |

**Money color rule**
- **Orange** means *you owe*.
- **Green** means *you receive / settled*.
- **Ink** means a neutral amount, e.g. viewing someone else's debt.

Never use red for a normal debt. Red is reserved for errors.

### Member avatars
| Token | Hex | Member |
|---|---|---|
| `avatar/L` | `#F2D5C3` | Linh |
| `avatar/M` | `#D3E5E0` | Minh |
| `avatar/A` | `#E3D7F0` | An |
| `avatar/H` | `#F6E7B4` | Hạnh |

For new members, pick another soft pastel of similar lightness. Avatar letters are always `text/ink`.

---

## 3. Typography

- **Font family:** `Be Vietnam Pro` only. It has full Vietnamese diacritic support. Do not use Inter or system fonts.
- **Line height:** never set it below 1.3× the font size. Stacked Vietnamese accents (ặ, ổ, ữ) get clipped otherwise.

| Text style | Size / line height | Weight | Letter spacing | Use |
|---|---|---|---|---|
| `Title/Room` | 26 / 34 | Bold | −0.3 | Room name in dashboard header ("Phòng 203") |
| `Display/Amount` | 40 / 48 | Bold | −0.5 | Hero money amount ("320.000đ") |
| `Title/H1` | 22 / 30 | Bold | 0 | Card headlines ("Cả phòng đang ổn") |
| `Title/H2` | 19 / 26 | Bold | 0 | Screen titles, section headers ("Chi tiêu gần đây") |
| `Stat/Value` | 15 / 22 | Bold | −0.3 | Values in the 3 stat cards |
| `Body/Strong` | 15 / 22 | SemiBold | 0 | Row titles, amounts in lists, key values |
| `Body/Regular` | 15 / 22 | Regular | 0 | Body copy, descriptions |
| `Label/Button` | 16 / 22 | Bold | 0 | Button labels |
| `Body/SmallStrong` | 13 / 18 | SemiBold | 0 | Chips, badges, tab labels (active) |
| `Body/Small` | 13 / 18 | Regular | 0 | Subtitles, captions, timestamps |
| `Label/Overline` | 12 / 16 | SemiBold | +0.4, UPPERCASE | Small section labels inside cards ("NỘI DUNG CHUYỂN KHOẢN") |
| `Code/Transfer` | 15 / 22 | Bold | +0.6 | Bank transfer memo ("TROMATE P203 LINH TRA MINH T10") |

---

## 4. Spacing, radius and elevation

### Layout grid
- **Frame width:** 360px (mobile). Frames hug content height.
- **Screen padding:** 16px left and right. Top padding 20–22px, bottom padding 20–28px.
- **Vertical gap between cards:** 14–16px.
- **Gap between the 3 stat cards:** 6px.

### Cards
- **Corner radius:** 20px on detail and settlement screens, 22px on dashboard hero and list cards.
- **Padding:** 18px (list cards use 16px horizontally and 4px vertically).
- **Border:** 1px `border/default`. Tinted cards use their matching soft border.

### Other radii
| Element | Radius |
|---|---|
| Screen frame | 28 |
| Inset box (copy field, bank box) | 14 |
| Button | 14 |
| Stat card | 18 |
| Chip / badge | 999 (pill) |
| Avatar / icon circle | full circle |

### Icon circle sizes
| Size | Use |
|---|---|
| 28 | Timeline steps |
| 32 | Stat cards |
| 36 | Notices, bank row |
| 40 | Back button |
| 44 | List rows |
| 48–60 | Success marks |

### Elevation
- Effectively flat: depth comes from borders and tinted backgrounds, not shadows.
- The only shadow is on toasts: y 6, blur 18, black at 18%.

### Inner padding
| Element | Padding |
|---|---|
| Button | 14 × 20 |
| Chip | 4 × 10 |
| Badge | 5 × 12 |
| Copy field | 12 × 14 |

---

## 5. Iconography

- **Style:** Lucide-style outline icons, 24px viewBox, stroke width 2, round caps and joins.
  - Note: the original PDF mockups used filled Material-style icons. The Figma file standardized on outline. Keep outline.
- **Sizes:**
  - 20px in buttons and list circles
  - 16–18px in small circles
  - 14px in chips
  - 22px in the tab bar and room switcher
- **Color:** tint the stroke with a color token. Never use fills.

**Available icon components** (`Icon/<name>`):
`chevron-left`, `chevron-right`, `chevron-down`, `copy`, `arrow-right`, `arrow-down`, `arrow-up`, `check`, `clock`, `lock`, `alert`, `external`, `download`, `refresh`, `bell`, `bank`, `zap`, `wifi`, `droplet`, `cart`, `home`, `wallet`, `history`, `receipt`, `info`, `x`, `qr`, `plus`, `user-plus`.

**Meaning conventions:**
| Icon | Meaning |
|---|---|
| `zap` | electricity / utility bills |
| `wifi` | internet |
| `droplet` | water |
| `cart` | groceries / purchases |
| `home` | rent |
| `bank` | room fund / bank account |
| `arrow-down` | money coming to you |
| `arrow-up` | money you pay |

---

## 6. Components

All components live in the **Components** frame on the first page. Instance them; don't redraw.

### Button (`Button`, set `2:153`)
- **Properties:**
  - `Label` (text)
  - `Show icon` (boolean)
  - `Icon` (instance swap, any `Icon/*`)
- **Variants (`Type=`):**
  | Variant | Fill | Text/icon |
  |---|---|---|
  | `Primary` | teal | white |
  | `Secondary` | tealSoft | teal |
  | `Ghost` | none | teal |
  | `Disabled` | `state/disabled` | muted |
  | `Danger` | redSoft | red |
- **Default size:** 50px tall, full width (fill container).
- **Rule:** one Primary per state card or bottom bar. Put a leading icon on most buttons: `plus` to create, `check` to confirm, `chevron-right` to pay, `bank` for the room fund, `receipt` for details.

### StatusChip (`StatusChip`, set `2:175`)
Settlement status, always icon + label.
| Variant | Label | Color | Icon |
|---|---|---|---|
| `Unpaid` | Chưa trả | orange | `alert` |
| `Pending` | Chờ xác nhận | amber | `clock` |
| `Confirmed` | Đã xác nhận | green | `check` |
| `Error` | Lỗi tạo QR | red | `alert` |

### Badge (`Badge`, set `15:268`)
Period state badge or list tag. Pill shape, text only. Has a `Label` text property.
| Variant | Use |
|---|---|
| `Tone=Amber` | "Phòng mới" |
| `Tone=Teal` | "Đang diễn ra" |
| `Tone=Orange` | "Cần thanh toán" / "Chưa trả" |
| `Tone=Green` | "Đã chốt sổ" / "Đã trả" / "An còn nợ bạn" |

### Avatar (`Avatar`, set `2:184`)
- Variants `Person=L/M/A/H`. 36px circle with a 2px white stroke.
- In the header, stack the avatars horizontally with −8px spacing.

### TabBar (`TabBar`, component `16:214`, on the SCRUM-69 page)
- White bar with a top border and 3 equal tabs: **Phòng** (`home`), **Số dư** (`wallet`), **Lịch sử** (`history`).
- Active tab is teal with `Body/SmallStrong`. Inactive tabs are muted with `Body/Small`.

### Composed patterns
These are built from frames, not components. Copy the structure exactly.

- **Room header**
  - Row 1: "Phòng 203" (`Title/Room`) + `chevron-down`, with the avatar stack on the right.
  - Row 2: period "Kỳ 10/2026 · 1–31/10" (`Body/Regular` muted), with a Badge on the right.
- **Stat cards (×3)**
  - Order is always **Quỹ phòng · Cần thu về · Bạn cần trả**.
  - Each card: icon circle (32), label (`Body/Small` muted), then value (`Stat/Value`).
  - When a value is 0đ, the icon circle is neutral `icon/bg` and the value is ink.
  - When a value is non-zero: fund = teal circle with ink value, credit = green circle with green value, debt = orange circle with orange value.
- **State hero card**
  - Title (`Title/H1`), one line of explanation (`Body/Regular` muted), then Primary and Secondary buttons.
  - The card background follows the state: white when active, `orangeSoft` when the user owes, `greenSoft` when the period is closed.
- **Transaction row**
  - Icon circle (44) + title (`Body/Strong`) + subtitle (`Body/Small` muted, format "`<Payer> trả · phần bạn <amount>`").
  - Right-aligned column: amount (`Body/Strong`), with an optional Badge below it.
  - Rows are separated by 1px dividers inside one card.
- **Section header:** title (`Title/H2`) on the left, "Xem tất cả" (`Body/Strong` teal) on the right.
- **Settlement summary card**
  - Status line + StatusChip, then the amount (`Display/Amount`).
  - Then a "Parties" row: avatar, name and role ("Người trả" / "Người nhận"), with an arrow circle between the two people.
  - Then key–value rows: label muted on the left, value `Body/Strong` on the right.
- **Copy field:** `bg/subtle` box with the value on the left and a "Sao chép" pill on the right (tealSoft, `copy` icon). Copying shows a dark toast with a green check.
- **Notice:** horizontal box with a 36px icon circle, a title (`Body/Strong`) and a description (`Body/Small` muted). Use it for pending info and permission messages (`lock` icon).
- **Timeline:** vertical steps with a 28px circle and a 2px connector line.
  | Step state | Circle | Connector |
  |---|---|---|
  | Done | green check | green |
  | Waiting | amber clock, timestamp in amber | border color |
  | Not started | muted | border color |
- **Bottom action bar:** white with a top border, 16px padding. Holds one Primary button (plus an optional Secondary or Ghost) and an optional centered muted caption explaining what happens next.
- **VietQR block:** white bordered box with the QR (≈200px) and a centered brand logo. Below it: a "VietQR · napas 247" caption, then the bank box (bank name, account holder, account number with copy, amount).
- **Error state:** `redSoft` box with a dashed red border, a red alert circle, a title, a reason, and a recovery action (Secondary "Thử tạo lại mã"). Always offer a manual fallback.

---

## 7. States reference

### Dashboard (SCRUM-69)
| State | Badge | Hero card | Primary action |
|---|---|---|---|
| New room | Amber "Phòng mới" | Welcome + Telegram chat example + setup checklist | Ghi chi tiêu đầu tiên |
| Active period | Teal "Đang diễn ra" | "Cả phòng đang ổn" (white) | Ghi chi tiêu |
| Owes money | Orange "Cần thanh toán" | Orange "Bạn cần trả" + amount | Trả <tên> <số tiền> bằng VietQR |
| Period closed | Green "Đã chốt sổ" | Green "Kỳ … đã chốt sổ" | Bắt đầu kỳ <tháng tiếp> |

### Settlement (SCRUM-77)
`Unpaid → (debtor taps "Tôi đã chuyển khoản") → Pending → (creditor or room lead taps "Đã nhận …") → Confirmed`

- **Permissions:** only the creditor or the room lead can confirm receipt. Other members see a Disabled button with a `lock` icon and a permission notice.
- **Pending debts:** a pending debt still counts in balances until it is confirmed. Say so in the UI.

---

## 8. Content and copy rules

- **Language and tone:** Vietnamese, friendly, informal "bạn / mình". Use soft particles at the end of sentences ("nhé", "nha") in bot messages and success messages. Don't use them in labels.
- **Money format:** dot thousands separator plus "đ" with no space, e.g. `250.000đ`, `1.200.000đ`, `0đ`.
  - In chat input, users may type `k / tr / củ / xị`. The UI always displays the normalized full amount.
- **Dates:** `DD/MM/YYYY`. Times are 24h and come first: `21:14 · 16/10/2026`. Billing period: `Kỳ 10/2026 · 1–31/10`.
- **Separator:** use a middle dot ` · ` between metadata items.
- **Transfer memo format:** `TROMATE P<room> <PAYER> TRA <PAYEE> T<month>`, all caps, no diacritics.
- **Button labels:** start with a verb and include the amount or person when it helps, e.g. "Trả Minh 250.000đ bằng VietQR", "Đã nhận 250.000đ".
- **Captions under actions:** explain the consequence, e.g. "Minh sẽ nhận thông báo để xác nhận đã nhận tiền."

---

## 9. Localization notes

- Design in Vietnamese first. Use auto-layout everywhere so text can grow.
- Text that wraps must use width = fill and auto height. Never clip text.
- Stat values must stay on one line. `1.200.000đ` exactly fills a stat card. Amounts of 10.000.000đ or more need a smaller style or a compact format; decide this before using them.
- For multiple languages, use Figma string variables with one mode per language. Keep key names identical to the app's i18n JSON keys (e.g. `settlement.confirm_received`).

---

## 10. Building new screens: checklist for agents

0. **Never edit existing screens or shared foundations** (see the "Do not edit existing screens" rule at the top). Work on a new page or a duplicated copy.
1. Start from a 360px frame with the `bg/canvas` fill, vertical auto-layout, 16px side padding and 14–16px gaps.
2. Use only the `TroMate` color variables and the text styles listed above.
3. Instance existing components (Button, StatusChip, Badge, Avatar, TabBar, Icon/*) before building anything new. If something new repeats, make it a component and add it to the Components frame.
4. Give each screen or state exactly one Primary action.
5. Show every status with label + icon + color.
6. Use realistic Vietnamese sample data from the Phòng 203 story:
   - Members: Linh (you), Minh, An, Hạnh. Room 203, period 10/2026.
   - Bank: Vietcombank, `1023 4567 89`, NGUYEN HOANG MINH.
7. Name layers and frames clearly, e.g. `0X · <Role> — <State>`, with a label 48px above each frame.
8. Check the result for clipped Vietnamese text, wrapped stat values, and more than one Primary button.
