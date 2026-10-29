"""OCR engines under test. Each returns {text, fields, confidence, ms} per image.

Classic engines return text, which goes through vnd_parser. Gemini returns the
fields itself, so it skips the parser.
"""
import base64
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytesseract
import requests
from PIL import Image

from layout import rebuild_lines, tesseract_line_slopes
from preprocess import prepare
from vnd_parser import extract_fields

ROOT = Path(__file__).resolve().parent


def check(resp):
    if not resp.ok:
        raise RuntimeError(f"{resp.status_code} from {resp.url.split('?')[0]}: {resp.text[:300]}")


def tesseract(paths, kinds):
    out = {}
    for path, kind in zip(paths, kinds):
        psm = "11" if kind == "meter" else "6"
        started = time.perf_counter()
        data = pytesseract.image_to_data(Image.open(path), lang="vie+eng", config=f"--psm {psm}",
                                         output_type=pytesseract.Output.DICT)
        ms = (time.perf_counter() - started) * 1000
        slopes = tesseract_line_slopes(data)
        boxes, confs = [], []
        for i, word in enumerate(data["text"]):
            if word.strip():
                key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                boxes.append({"text": word, "cx": data["left"][i] + data["width"][i] / 2,
                              "cy": data["top"][i] + data["height"][i] / 2, "h": data["height"][i],
                              "slope": slopes.get(key)})
                confs.append(float(data["conf"][i]))
        text = rebuild_lines(boxes)
        out[path] = {"text": text, "fields": extract_fields(text, kind),
                     "confidence": sum(confs) / len(confs) / 100 if confs else 0.0, "ms": ms}
    return out


def paddleocr(paths, kinds):
    # One Node process for the whole batch, so model loading isn't timed per image.
    proc = subprocess.run(["node", str(ROOT / "paddle_ocr.js"), *map(str, paths)],
                          capture_output=True, text=True, check=True)
    out = {}
    for line, kind in zip(proc.stdout.splitlines(), kinds):
        r = json.loads(line)
        boxes = []
        for b in r["boxes"]:
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = b["box_points"]
            boxes.append({"text": b["text"], "cx": (x0 + x1 + x2 + x3) / 4, "cy": (y0 + y1 + y2 + y3) / 4,
                          "h": ((y3 - y0) + (y2 - y1)) / 2,
                          "slope": (y1 - y0) / (x1 - x0) if x1 - x0 > 40 else None})
        text = rebuild_lines(boxes)
        conf = sum(b["score"] for b in r["boxes"]) / len(r["boxes"]) if r["boxes"] else 0.0
        out[r["image"]] = {"text": text, "fields": extract_fields(text, kind), "confidence": conf, "ms": r["ms"]}
    return out


def google_vision(paths, kinds):
    key = os.environ["GOOGLE_VISION_API_KEY"]
    out = {}
    for path, kind in zip(paths, kinds):
        body = {"requests": [{
            "image": {"content": base64.b64encode(Path(path).read_bytes()).decode()},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            "imageContext": {"languageHints": ["vi"]},
        }]}
        started = time.perf_counter()
        resp = requests.post(f"https://vision.googleapis.com/v1/images:annotate?key={key}", json=body, timeout=30)
        ms = (time.perf_counter() - started) * 1000
        check(resp)
        annotation = resp.json()["responses"][0].get("fullTextAnnotation", {})
        text = annotation.get("text", "")
        pages = annotation.get("pages", [])
        confs = [b.get("confidence", 0) for p in pages for b in p.get("blocks", [])]
        out[path] = {"text": text, "fields": extract_fields(text, kind),
                     "confidence": sum(confs) / len(confs) if confs else 0.0, "ms": ms}
    return out


GEMINI_PROMPT = """You read photos sent to a Vietnamese roommate expense app.
The photo is one of: a shop receipt, a handwritten landlord bill, or an
electricity/water meter. Return JSON only, following the schema.
- kind: "receipt", "bill" or "meter".
- total: the final amount to pay in VND as an integer (after discounts; not the
  cash handed over, not the change). "100k" means 100000. null for meters.
- date: the document date as DD/MM/YYYY, or null if none is written.
- meter_reading: for meters only, the whole-number reading as an integer. Ignore
  red decimal drums, digits after the decimal point and the serial number.
- confidence: 0 to 1, how sure you are of total or meter_reading.
"""

GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "kind": {"type": "STRING", "enum": ["receipt", "bill", "meter"]},
        "total": {"type": "INTEGER", "nullable": True},
        "date": {"type": "STRING", "nullable": True},
        "meter_reading": {"type": "INTEGER", "nullable": True},
        "confidence": {"type": "NUMBER"},
    },
    "required": ["kind", "total", "date", "meter_reading", "confidence"],
}


# v2: written after the v1.4 real-photo run, where 7 of 9 meter misses appended a
# decimal drum. The model transcribes whole and decimal drums separately before
# answering, and the reading is taken from the whole-unit digits only.
GEMINI_V2_PROMPT = """You read photos sent to a Vietnamese roommate expense app.
The photo is one of: a shop receipt, a handwritten landlord bill, or an
electricity/water meter. It may be tilted, rotated or sideways. Return JSON only,
following the schema, filling the fields in order.

Receipts and bills (kind "receipt" or "bill"):
- total: the amount actually owed, in VND, as an integer. Usually labelled Tổng
  cộng, Tổng tiền, Thành tiền, Tiền thanh toán, Cần thanh toán, Phải trả, or
  TIEN MAT/Tiền mặt when it is the only total. Never the cash handed over (Tiền
  khách đưa, Khách trả), the change (Tiền thối, Tiền trả lại), a subtotal before a
  discount or voucher, an item price, a quantity, or an invoice, transaction or
  phone number. Dots and commas are thousands separators; "100k" means 100000
  and "1tr2" means 1200000. null if the total is cut off or hidden.
- date: the document date as DD/MM/YYYY, or null if none is written.
- Leave meter_type, whole_digits and decimal_digits empty.

Meters (kind "meter"): read only the counter window, step by step.
- meter_type: "electricity_drum", "electricity_lcd" or "water".
- whole_digits: every whole-unit digit of the counter, left to right, including
  leading zeros, as a string. Whole-unit drums show black digits on white or
  white digits on black. Stop at the first decimal drum.
- decimal_digits: the decimal drums you skipped, as a string ("" if none).
  Decimal drums are: red drums or drums on a red background; a last drum set
  apart in its own box or frame; any drum marked 1/10, x0.1 or after a decimal
  point. On water meters the small round red pointer dials (x0.1, x0.01, x0.001,
  x0.0001) are decimals. On LCD meters, digits after the decimal point are
  decimals and small text above the main digits (such as 1.8.0) is a register code.
- A drum caught between two digits counts as the lower one (between 9 and 0, use 9).
- Never use serial numbers (Số SX, No.), years, ratings (220V, 5(20)A, 50Hz,
  rev/kWh, imp/kWh), "ISO 4064", model codes or inspection stickers.
- On a rotated photo, read in the counter's own order: the unit label (kWh, m³)
  is to the right of the last digit.
- meter_reading: the integer value of whole_digits.
- total and date are null for meters.

confidence: 0 to 1, how sure you are of total or meter_reading.
"""

GEMINI_V2_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "kind": {"type": "STRING", "enum": ["receipt", "bill", "meter"]},
        "meter_type": {"type": "STRING", "nullable": True},
        "whole_digits": {"type": "STRING", "nullable": True},
        "decimal_digits": {"type": "STRING", "nullable": True},
        "meter_reading": {"type": "INTEGER", "nullable": True},
        "total": {"type": "INTEGER", "nullable": True},
        "date": {"type": "STRING", "nullable": True},
        "confidence": {"type": "NUMBER"},
    },
    "required": ["kind", "meter_type", "whole_digits", "decimal_digits",
                 "meter_reading", "total", "date", "confidence"],
    # Gemini fills fields in this order, so the digits are written down before the reading.
    "propertyOrdering": ["kind", "meter_type", "whole_digits", "decimal_digits",
                         "meter_reading", "total", "date", "confidence"],
}


def gemini(paths, kinds, prompt=GEMINI_PROMPT, schema=GEMINI_SCHEMA):
    # Requests are slow (10s+ each), so send a few at once.
    with ThreadPoolExecutor(max_workers=int(os.environ.get("GEMINI_WORKERS", "2"))) as pool:
        return dict(zip(paths, pool.map(lambda p, k: gemini_one(p, k, prompt, schema), paths, kinds)))


def gemini_v2(paths, kinds):
    return gemini(paths, kinds, GEMINI_V2_PROMPT, GEMINI_V2_SCHEMA)


def gemini_one(path, kind, prompt=GEMINI_PROMPT, schema=GEMINI_SCHEMA):
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg",
                             "data": base64.b64encode(Path(path).read_bytes()).decode()}},
        ]}],
        # Cap output so a runaway reply fails fast instead of generating for minutes.
        # Thinking models (Flash) count their reasoning against this cap; raise GEMINI_MAX_TOKENS for them.
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": schema,
                             "maxOutputTokens": int(os.environ.get("GEMINI_MAX_TOKENS", "512"))},
    }
    # Gemini can take 30s+ per image; retry timeouts and 429/5xx instead of losing the run.
    for attempt in range(4):
        started = time.perf_counter()
        try:
            resp = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=180)
        except requests.exceptions.Timeout:
            if attempt == 3:
                raise
            continue
        if resp.status_code != 429 and resp.status_code < 500:
            break
        time.sleep(30 * (attempt + 1) if resp.status_code == 429 else 5)  # 429 is a per-minute quota
    ms = (time.perf_counter() - started) * 1000
    check(resp)
    candidate = resp.json()["candidates"][0]
    raw = candidate["content"]["parts"][0]["text"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Truncated output (finishReason MAX_TOKENS) counts as a miss.
        print(f"  {Path(path).stem}: unparsable reply, finishReason={candidate.get('finishReason')}")
        data = {}
    reading = data.get("meter_reading")
    whole = str(data.get("whole_digits") or "").strip()
    if whole.isdigit():  # v2: trust the transcribed whole-unit digits over the model's own sum
        reading = int(whole)
    fields = ({"meter_reading": reading} if kind == "meter"
              else {"total": data.get("total"), "date": data.get("date")})
    # usageMetadata has the token counts (prompt, reply, thinking) needed for cost estimates.
    return {"text": raw, "fields": fields, "confidence": data.get("confidence", 0.0), "ms": ms,
            "usage": resp.json().get("usageMetadata", {})}


def with_prep(engine):
    """Run an engine on flattened, light-corrected copies of the photos."""
    def run(paths, kinds):
        tmp = Path(tempfile.mkdtemp(prefix="ocr_prep_"))
        prepped, prep_ms = [], {}
        for path in paths:
            dst = tmp / Path(path).name
            started = time.perf_counter()
            prepare(path, dst)
            prep_ms[str(dst)] = (time.perf_counter() - started) * 1000
            prepped.append(str(dst))
        results = engine(prepped, kinds)
        return {orig: {**results[new], "ms": results[new]["ms"] + prep_ms[new]}
                for orig, new in zip(paths, prepped)}
    return run


ENGINES = {
    "tesseract": (tesseract, None),
    "paddleocr": (paddleocr, None),
    "tesseract_prep": (with_prep(tesseract), None),
    "paddleocr_prep": (with_prep(paddleocr), None),
    "google_vision": (google_vision, "GOOGLE_VISION_API_KEY"),
    "gemini": (gemini, "GEMINI_API_KEY"),
    "gemini_v2": (gemini_v2, "GEMINI_API_KEY"),
}
