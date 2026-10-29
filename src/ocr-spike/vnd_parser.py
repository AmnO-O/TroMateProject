"""Turn raw OCR text into the fields TroMate needs: total, date, meter reading.

Classic OCR engines return lines of text, not fields, so this is the part of
the pipeline we would have to build and maintain ourselves.
"""
import re
import unicodedata

# Highest priority first. Matched on text without diacritics, because OCR often
# drops or mangles Vietnamese tone marks.
TOTAL_KEYS = [
    "tong cong", "tong thanh toan", "can thanh toan", "thanh tien", "tong tien",
    "total", "tong",
]
SKIP_KEYS = ["tien hang", "khach dua", "tien thoi", "thoi lai", "giam gia", "khach tra"]

AMOUNT = re.compile(r"(\d{1,3}(?:[.,\s]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|tr|củ|cu|đ|d|vnd)?(?![\d])", re.I)
DATE = re.compile(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(20\d{2})")


def strip_accents(text):
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


def parse_amount(token, unit=None):
    """'123.000' -> 123000, '100k' -> 100000, '1,5tr' -> 1500000."""
    unit = (unit or "").lower()
    if unit in ("k",):
        return int(round(float(token.replace(",", ".")) * 1000))
    if unit in ("tr", "củ", "cu"):
        return int(round(float(token.replace(",", ".")) * 1_000_000))
    digits = re.sub(r"[.,\s]", "", token)
    return int(digits) if digits.isdigit() else None


def amounts_in(line):
    found = []
    for m in AMOUNT.finditer(line):
        value = parse_amount(m.group(1), m.group(2))
        if value is not None and value >= 1000:
            found.append(value)
    return found


def find_total(text):
    lines = [l for l in text.splitlines() if l.strip()]
    plain = [strip_accents(l) for l in lines]
    for key in TOTAL_KEYS:
        for i, p in enumerate(plain):
            if key in p and not any(s in p for s in SKIP_KEYS):
                # amount on the same line, else the next line (layout split)
                for candidate in (lines[i], lines[i + 1] if i + 1 < len(lines) else ""):
                    values = amounts_in(candidate)
                    if values:
                        return values[-1]
    return None


def find_date(text):
    m = DATE.search(text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if 1 <= d <= 31 and 1 <= mo <= 12:
        return f"{d:02d}/{mo:02d}/{y}"
    return None


def find_meter_reading(text):
    """Longest run of 4-6 digits, skipping the serial-number line.

    Text OCR can't see that the last drums are red (decimals), so a run of
    7-9 digits is read as 5 whole digits plus decimals.
    """
    best, long_run = None, None
    for line in text.splitlines():
        plain = strip_accents(line)
        if re.search(r"\bno\b|serial|so seri", plain):
            continue
        # nameplate specs: 220V 5(60)A 50Hz 1000 imp/kWh, 450 vòng/kWh, DN15 ...
        line = re.sub(r"\d+\s*(?:imp|v\b|a\b|hz|vong|m3/h|m³/h)|\d+\(\d+\)|(?:dn|r|q\d?)\s*=?\s*[\d,]+", " ", plain)
        for run in re.findall(r"\d+", re.sub(r"(?<=\d)[ \t](?=\d)", "", line)):
            if 4 <= len(run) <= 6 and (best is None or len(run) > len(best)):
                best = run
            elif 7 <= len(run) <= 9 and long_run is None:
                long_run = run
    if best is None and long_run:
        best = long_run[:5]
    return int(best) if best else None


def extract_fields(text, kind):
    if kind == "meter":
        return {"meter_reading": find_meter_reading(text)}
    return {"total": find_total(text), "date": find_date(text)}
