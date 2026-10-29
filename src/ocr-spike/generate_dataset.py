"""Generate a synthetic, labelled test set for the SCRUM-99 OCR spike.

Renders Vietnamese supermarket receipts, handwritten landlord bills and
electricity/water meter faces, then degrades them to look like phone photos
(perspective, tilt, blur, uneven light, noise, JPEG). Ground truth goes to
labels.csv so every engine is scored against exact values.

Usage: python generate_dataset.py --out data/synthetic --seed 99
"""
import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SYS_FONTS = Path("/usr/share/fonts/truetype")
NPM = ROOT / "node_modules"

PRINT_FONTS = [
    SYS_FONTS / "dejavu/DejaVuSansMono.ttf",
    SYS_FONTS / "noto/NotoSansMono-Regular.ttf",
    SYS_FONTS / "dejavu/DejaVuSans.ttf",
    SYS_FONTS / "noto/NotoSans-Regular.ttf",
]
BOLD_FONTS = {
    PRINT_FONTS[0]: SYS_FONTS / "dejavu/DejaVuSansMono-Bold.ttf",
    PRINT_FONTS[1]: SYS_FONTS / "noto/NotoSansMono-Bold.ttf",
    PRINT_FONTS[2]: SYS_FONTS / "dejavu/DejaVuSans-Bold.ttf",
    PRINT_FONTS[3]: SYS_FONTS / "noto/NotoSans-Bold.ttf",
}
# Fontsource ships each handwriting font as subsets; a glyph is drawn from the
# first subset that has it.
HAND_FONTS = [
    [NPM / "@fontsource/patrick-hand/files/patrick-hand-latin-400-normal.woff",
     NPM / "@fontsource/patrick-hand/files/patrick-hand-vietnamese-400-normal.woff"],
    [NPM / "@fontsource/mali/files/mali-latin-400-normal.woff",
     NPM / "@fontsource/mali/files/mali-vietnamese-400-normal.woff"],
    [NPM / "@fontsource/charm/files/charm-latin-400-normal.woff",
     NPM / "@fontsource/charm/files/charm-vietnamese-400-normal.woff"],
    [NPM / "@fontsource/itim/files/itim-latin-400-normal.woff",
     NPM / "@fontsource/itim/files/itim-vietnamese-400-normal.woff"],
]
SEG_FONT = NPM / "dseg/fonts/DSEG7-Classic/DSEG7Classic-Bold.ttf"

STORES = [
    ("SIÊU THỊ MINI AN PHÚ", "123 Nguyễn Văn Cừ, P.4, Q.5, TP.HCM"),
    ("CỬA HÀNG TIỆN LỢI 24H", "45 Lê Lợi, P. Bến Nghé, Q.1, TP.HCM"),
    ("TẠP HÓA CÔ BA", "Chợ Bà Chiểu, Q. Bình Thạnh, TP.HCM"),
    ("MART XANH - CN THỦ ĐỨC", "18 Võ Văn Ngân, TP. Thủ Đức"),
    ("SIÊU THỊ HÒA BÌNH", "210 Cầu Giấy, Q. Cầu Giấy, Hà Nội"),
    ("NHÀ THUỐC MINH CHÂU", "77 Trần Hưng Đạo, Q.1, TP.HCM"),
]
ITEMS = [
    ("Nước suối Lavie 1.5L", 9000), ("Mì Hảo Hảo tôm chua cay", 4500),
    ("Sữa tươi Vinamilk 1L", 32000), ("Trứng gà hộp 10 quả", 31000),
    ("Gạo ST25 túi 5kg", 185000), ("Nước mắm Nam Ngư 500ml", 36500),
    ("Dầu ăn Simply 1L", 62000), ("Bột giặt OMO 800g", 54000),
    ("Nước rửa chén Sunlight", 28500), ("Giấy vệ sinh Bless You", 46000),
    ("Kem đánh răng P/S", 29000), ("Bánh mì sandwich", 22000),
    ("Rau muống 1 bó", 12000), ("Thịt ba rọi 500g", 78000),
    ("Coca-Cola lon 330ml", 10500), ("Đường cát trắng 1kg", 27000),
    ("Xà phòng Lifebuoy", 18000), ("Bình nước 20L (đổi vỏ)", 45000),
    ("Hạt nêm Knorr 400g", 39500), ("Cà phê G7 hộp 18 gói", 51000),
]
TOTAL_WORDS = ["TỔNG CỘNG", "Tổng thanh toán", "THÀNH TIỀN", "Tổng tiền", "Cần thanh toán", "TỔNG"]


def vnd(amount, style):
    """Format VND the ways real receipts do."""
    if style == "dot":
        return f"{amount:,}".replace(",", ".")
    if style == "comma":
        return f"{amount:,}"
    if style == "dot_d":
        return f"{amount:,}".replace(",", ".") + "đ"
    if style == "vnd":
        return f"{amount:,}".replace(",", ".") + " VND"
    if style == "k":
        return f"{amount // 1000}k" if amount % 1000 == 0 else f"{amount / 1000:g}k"
    return str(amount)


class HandFont:
    def __init__(self, paths, size):
        self.fonts = [ImageFont.truetype(str(p), size) for p in paths]
        self.cmaps = [set(TTFont(str(p)).getBestCmap()) for p in paths]

    def pick(self, ch):
        for font, cmap in zip(self.fonts, self.cmaps):
            if ord(ch) in cmap:
                return font
        return self.fonts[0]


def draw_hand_line(img, xy, text, hand, ink, rng):
    """Draw text glyph by glyph with jitter so it reads like handwriting."""
    x, y = xy
    drift = 0.0
    for ch in text:
        font = hand.pick(ch)
        if ch == " ":
            x += font.getlength(" ") * rng.uniform(0.8, 1.3)
            continue
        w = font.getlength(ch)
        bbox = font.getbbox(ch)
        tile = Image.new("L", (int(w) + 24, bbox[3] + 24), 0)
        ImageDraw.Draw(tile).text((12, 12), ch, font=font, fill=255)
        tile = tile.rotate(rng.uniform(-6, 6), resample=Image.BICUBIC, expand=False)
        drift += rng.uniform(-0.6, 0.6)
        drift = max(-5, min(5, drift))
        color = Image.new("RGB", tile.size, ink)
        img.paste(color, (int(x) - 12, int(y + drift) - 12), tile)
        x += w * rng.uniform(0.92, 1.08)
    return x


def render_receipt(rng):
    font_path = rng.choice(PRINT_FONTS)
    size = rng.randint(20, 24)
    font = ImageFont.truetype(str(font_path), size)
    bold = ImageFont.truetype(str(BOLD_FONTS[font_path]), size + 2)
    width = 560
    style = rng.choice(["dot", "dot", "comma", "dot_d", "vnd"])
    store, addr = rng.choice(STORES)
    when = datetime(2026, 9, 1) + timedelta(days=rng.randint(0, 55), minutes=rng.randint(420, 1300))
    date_fmt = rng.choice(["%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y"])
    n_items = rng.randint(2, 9)
    picks = rng.sample(ITEMS, n_items)
    lines = []  # (text_left, text_right, font, align)
    lines.append((store, None, bold, "center"))
    lines.append((addr, None, font, "center"))
    lines.append(("ĐT: 028 3" + "".join(str(rng.randint(0, 9)) for _ in range(7)), None, font, "center"))
    lines.append((rng.choice(["HÓA ĐƠN BÁN LẺ", "PHIẾU THANH TOÁN", "HÓA ĐƠN BÁN HÀNG"]), None, bold, "center"))
    lines.append((f"Số HĐ: {rng.randint(100000, 999999)}", None, font, "left"))
    lines.append((("Ngày: " if rng.random() < 0.6 else "Ngày bán: ") + when.strftime(date_fmt), None, font, "left"))
    lines.append(("-" * 40, None, font, "rule"))
    subtotal = 0
    for name, price in picks:
        qty = rng.choice([1, 1, 1, 2, 2, 3])
        amount = qty * price
        subtotal += amount
        lines.append((name, None, font, "left"))
        lines.append((f"  {qty} x {vnd(price, style)}", vnd(amount, style), font, "split"))
    lines.append(("-" * 40, None, font, "rule"))
    discount = rng.choice([0, 0, 0, 5000, 10000, round(subtotal * 0.05, -3)])
    discount = int(min(discount, subtotal // 4))
    total = subtotal - discount
    lines.append(("Tổng tiền hàng:", vnd(subtotal, style), font, "split"))
    if discount:
        lines.append(("Giảm giá:", "-" + vnd(discount, style), font, "split"))
    lines.append((rng.choice(TOTAL_WORDS) + ":", vnd(total, style), bold, "split"))
    paid = next(v for v in [50000, 100000, 200000, 500000, 1000000, 2000000] if v >= total)
    lines.append(("Tiền khách đưa:", vnd(paid, style), font, "split"))
    lines.append(("Tiền thối lại:", vnd(paid - total, style), font, "split"))
    lines.append(("-" * 40, None, font, "rule"))
    lines.append(("Cảm ơn quý khách! Hẹn gặp lại.", None, font, "center"))

    line_h = int(size * 1.45)
    height = 60 + line_h * len(lines) + 40
    paper = rng.choice([(252, 252, 248), (245, 244, 238), (250, 248, 240)])
    img = Image.new("RGB", (width, height), paper)
    d = ImageDraw.Draw(img)
    ink = rng.choice([(20, 20, 20), (45, 45, 55), (70, 70, 75)])
    y = 40
    for left, right, f, align in lines:
        if align == "center":
            w = d.textlength(left, font=f)
            d.text(((width - w) / 2, y), left, font=f, fill=ink)
        elif align == "rule":
            d.line((24, y + line_h // 2, width - 24, y + line_h // 2), fill=ink, width=1)
        elif align == "split":
            d.text((24, y), left, font=f, fill=ink)
            w = d.textlength(right, font=f)
            d.text((width - 24 - w, y), right, font=f, fill=ink)
        else:
            d.text((24, y), left, font=f, fill=ink)
        y += line_h
    labels = {"total": total, "date": when.strftime("%d/%m/%Y"), "item_count": n_items, "meter_reading": ""}
    return img, labels


def render_bill(rng):
    hand = HandFont(rng.choice(HAND_FONTS), rng.randint(36, 42))
    width, height = 1150, 1100
    paper = rng.choice([(250, 250, 244), (246, 243, 230), (252, 252, 252)])
    img = Image.new("RGB", (width, height), paper)
    d = ImageDraw.Draw(img)
    for yy in range(150, height - 40, 64):  # notebook lines
        d.line((40, yy, width - 40, yy), fill=(180, 200, 225), width=2)
    d.line((110, 0, 110, height), fill=(230, 160, 160), width=2)
    ink = rng.choice([(25, 45, 140), (20, 20, 30), (40, 60, 160)])
    month = rng.randint(9, 10)
    room = rng.choice(["101", "203", "302", "405", "A2", "B5"])
    style = rng.choice(["dot", "dot", "k"])
    rent = rng.choice([2800000, 3200000, 3500000, 4000000, 4500000, 5200000])
    old = rng.randint(800, 4000)
    kwh = rng.randint(80, 260)
    rate = rng.choice([3500, 3800, 4000])
    elec = kwh * rate
    people = rng.randint(2, 4)
    water = people * 100000
    charges = [("Tiền phòng", vnd(rent, "dot"), rent),
               ("Điện", f"{old + kwh} - {old} = {kwh} số x {vnd(rate, 'dot')} = {vnd(elec, 'dot')}", elec),
               ("Nước", f"{people} người x {vnd(100000, style)} = {vnd(water, style)}", water)]
    if rng.random() < 0.8:
        charges.append(("Wifi", vnd(100000, style), 100000))
    if rng.random() < 0.6:
        charges.append(("Rác", vnd(30000, style), 30000))
    if rng.random() < 0.3:
        charges.append(("Gửi xe", vnd(150000, style), 150000))
    total = sum(c[2] for c in charges)
    has_date = rng.random() < 0.6
    due = datetime(2026, month + 1, rng.randint(1, 5))
    def row(i):  # text sits on the notebook line
        return 150 + 64 * i - 54

    draw_hand_line(img, (140, row(0)), f"TIỀN PHÒNG THÁNG {month}/2026", hand, ink, rng)
    draw_hand_line(img, (140, row(1)), f"Phòng {room}", hand, ink, rng)
    for i, (name, text, _) in enumerate(charges):
        draw_hand_line(img, (140, row(2 + i)), f"- {name}: {text}", hand, ink, rng)
    i = 3 + len(charges)
    end = draw_hand_line(img, (140, row(i)), f"Tổng cộng: {vnd(total, 'dot')}", hand, ink, rng)
    d.line((140, row(i) + 56, end, row(i) + 56), fill=ink, width=3)
    if has_date:
        draw_hand_line(img, (140, row(i + 2)), f"Ngày {due.strftime('%d/%m/%Y')} - Chủ nhà", hand, ink, rng)
    labels = {"total": total, "date": due.strftime("%d/%m/%Y") if has_date else "",
              "item_count": len(charges), "meter_reading": ""}
    return img, labels


def render_meter(rng):
    kind = rng.choice(["digital", "mech_elec", "mech_water"])
    img = Image.new("RGB", (900, 700), rng.choice([(235, 235, 230), (210, 215, 220), (240, 236, 225)]))
    d = ImageDraw.Draw(img)
    label = ImageFont.truetype(str(SYS_FONTS / "dejavu/DejaVuSans-Bold.ttf"), 34)
    small = ImageFont.truetype(str(SYS_FONTS / "dejavu/DejaVuSans.ttf"), 24)
    serial = str(rng.randint(10_000_000, 99_999_999))
    if kind == "digital":
        reading = rng.randint(100, 49999)
        d.rounded_rectangle((60, 40, 840, 660), 30, outline=(90, 90, 90), width=6, fill=(225, 228, 230))
        d.text((110, 80), "CÔNG TƠ ĐIỆN TỬ 1 PHA", font=label, fill=(30, 30, 30))
        d.rounded_rectangle((140, 190, 760, 380), 12, fill=(160, 180, 150), outline=(60, 60, 60), width=4)
        seg = ImageFont.truetype(str(SEG_FONT), 120)
        d.text((180, 220), "88888.8", font=seg, fill=(150, 168, 140))  # ghost segments
        dec = rng.randint(0, 9)
        d.text((180, 220), f"{reading:05d}.{dec}", font=seg, fill=(25, 30, 25))
        d.text((660, 395), "kWh", font=label, fill=(30, 30, 30))
        d.text((110, 470), "220V  5(60)A  50Hz  1000 imp/kWh", font=small, fill=(40, 40, 40))
        d.text((110, 520), f"No. {serial}", font=small, fill=(40, 40, 40))
    else:
        water = kind == "mech_water"
        reading = rng.randint(10, 9999) if water else rng.randint(100, 99999)
        n_black = 5 if water else 5
        n_red = 3 if water else 1
        title = "ĐỒNG HỒ NƯỚC" if water else "CÔNG TƠ ĐIỆN 1 PHA"
        unit = "m³" if water else "kWh"
        d.rounded_rectangle((60, 40, 840, 660), 40, outline=(70, 70, 90), width=6,
                            fill=(215, 225, 240) if water else (240, 240, 236))
        d.text((110, 80), title, font=label, fill=(20, 30, 60))
        drum = ImageFont.truetype(str(SYS_FONTS / "dejavu/DejaVuSans-Bold.ttf"), 92)
        x0, y0, cw = 150, 210, 86
        digits = f"{reading:0{n_black}d}"
        reds = "".join(str(rng.randint(0, 9)) for _ in range(n_red))
        for i, ch in enumerate(digits + reds):
            red = i >= n_black
            box = (x0 + i * cw, y0, x0 + i * cw + cw - 8, y0 + 130)
            d.rectangle(box, fill=(170, 20, 20) if red else (20, 20, 20))
            off = rng.randint(-6, 6)  # drums sit slightly out of line
            d.text((box[0] + 14, y0 + 12 + off), ch, font=drum, fill=(245, 245, 245))
        d.text((x0 + (n_black + n_red) * cw + 10, y0 + 40), unit, font=label, fill=(20, 20, 20))
        d.text((110, 400), "Q3 = 2,5 m³/h   R160   DN15" if water else "220V  10(40)A  50Hz  450 vòng/kWh",
               font=small, fill=(40, 40, 40))
        d.text((110, 450), f"No. {serial}", font=small, fill=(40, 40, 40))
    labels = {"total": "", "date": "", "item_count": "", "meter_reading": reading}
    return img, labels


def photograph(doc, rng, level):
    """Turn a flat render into something that looks like a phone photo."""
    src = cv2.cvtColor(np.array(doc), cv2.COLOR_RGB2BGR)
    h, w = src.shape[:2]
    pad = int(max(h, w) * 0.18)
    canvas_w, canvas_h = w + 2 * pad, h + 2 * pad
    bg_color = np.array(rng.choice([(70, 90, 120), (40, 55, 75), (150, 150, 145), (95, 75, 60)]), np.float32)
    bg = np.ones((canvas_h, canvas_w, 3), np.float32) * bg_color
    bg += np.random.default_rng(rng.randint(0, 10**6)).normal(0, 9, bg.shape)
    jitter = {"easy": 0.02, "medium": 0.06, "hard": 0.10}[level]
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = corners + pad + np.float32([[rng.uniform(-1, 1) * jitter * w, rng.uniform(-1, 1) * jitter * h] for _ in range(4)])
    m = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(src.astype(np.float32), m, (canvas_w, canvas_h), borderValue=0)
    mask = cv2.warpPerspective(np.ones((h, w), np.float32), m, (canvas_w, canvas_h))
    if level == "hard" and rng.random() < 0.5:  # crumpled paper
        yy, xx = np.mgrid[0:canvas_h, 0:canvas_w].astype(np.float32)
        amp = rng.uniform(4, 8)
        map_x = xx + amp * np.sin(yy / rng.uniform(40, 70))
        map_y = yy + amp * np.sin(xx / rng.uniform(50, 90))
        warped = cv2.remap(warped, map_x, map_y, cv2.INTER_LINEAR)
        mask = cv2.remap(mask, map_x, map_y, cv2.INTER_LINEAR)
    out = warped * mask[..., None] + bg * (1 - mask[..., None])
    angle = rng.uniform(-1, 1) * {"easy": 2, "medium": 6, "hard": 10}[level]
    rot = cv2.getRotationMatrix2D((canvas_w / 2, canvas_h / 2), angle, 1.0)
    out = cv2.warpAffine(out, rot, (canvas_w, canvas_h), borderMode=cv2.BORDER_REFLECT)
    yy, xx = np.mgrid[0:canvas_h, 0:canvas_w].astype(np.float32)
    gx, gy = rng.uniform(-1, 1), rng.uniform(-1, 1)
    light = 1 + {"easy": 0.08, "medium": 0.2, "hard": 0.35}[level] * ((xx / canvas_w - 0.5) * gx + (yy / canvas_h - 0.5) * gy)
    if level == "hard" and rng.random() < 0.5:
        light *= 0.55  # low light
    if level != "easy" and rng.random() < 0.5:  # a phone's shadow across part of the page
        sx = rng.uniform(0.2, 0.8) * canvas_w
        light *= np.where(xx < sx, 0.75, 1.0)
        light = cv2.GaussianBlur(light, (0, 0), 25)
    out = out * light[..., None]
    out += np.random.default_rng(rng.randint(0, 10**6)).normal(0, {"easy": 3, "medium": 6, "hard": 11}[level], out.shape)
    sigma = {"easy": 0.4, "medium": 1.0, "hard": 1.8}[level] * rng.uniform(0.7, 1.3)
    out = cv2.GaussianBlur(np.clip(out, 0, 255), (0, 0), sigma)
    if level == "hard" and rng.random() < 0.35:  # cut off at one edge
        cut = int(canvas_w * rng.uniform(0.04, 0.09))
        out = out[:, :-cut] if rng.random() < 0.5 else out[:, cut:]
    scale = 1280 / max(out.shape[:2])
    out = cv2.resize(np.clip(out, 0, 255).astype(np.uint8), None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    quality = {"easy": 90, "medium": 75, "hard": 60}[level]
    return out, quality


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/synthetic")
    ap.add_argument("--seed", type=int, default=99)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    out = ROOT / args.out
    (out / "images").mkdir(parents=True, exist_ok=True)
    plan = ([("receipt", render_receipt, lvl) for lvl in ["easy"] * 6 + ["medium"] * 6 + ["hard"] * 4]
            + [("bill", render_bill, lvl) for lvl in ["easy"] * 4 + ["medium"] * 4 + ["hard"] * 2]
            + [("meter", render_meter, lvl) for lvl in ["easy"] * 4 + ["medium"] * 4 + ["hard"] * 2])
    rows = []
    counters = {}
    for kind, render, level in plan:
        counters[kind] = counters.get(kind, 0) + 1
        image_id = f"{kind}_{counters[kind]:02d}"
        doc, labels = render(rng)
        photo, quality = photograph(doc, rng, level)
        cv2.imwrite(str(out / "images" / f"{image_id}.jpg"), photo, [cv2.IMWRITE_JPEG_QUALITY, quality])
        rows.append({"id": image_id, "kind": kind, "difficulty": level, **labels})
    with open(out / "labels.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "kind", "difficulty", "total", "date", "item_count", "meter_reading"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} images to {out}")


if __name__ == "__main__":
    main()
