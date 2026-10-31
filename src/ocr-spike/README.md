# SCRUM-99 OCR spike

Compares OCR engines on Vietnamese receipts, handwritten landlord bills and
electricity/water meters for TroMate. The findings are in
`TECHNICAL_SPIKES_SCRUM-99_OCR.md`.

## Setup

```bash
sudo apt install tesseract-ocr tesseract-ocr-vie   # macOS: brew install tesseract tesseract-lang
pip install -r requirements.txt
npm install                                         # PaddleOCR models + binding, fonts
cp .env.example .env                                # add API keys for the cloud engines
```

## Run

```bash
python run_spike.py --data data/synthetic           # every engine whose key is set
python run_spike.py --data data/real --out results/real
python summarise.py --results results
```

Run only the cloud engines: `python run_spike.py --engines gemini,google_vision`.

## Files

| File | What it does |
|---|---|
| `generate_dataset.py` | Renders the 36 synthetic photos and `labels.csv` (`--seed 99` reproduces this set) |
| `engines.py` | Tesseract, PaddleOCR, Google Vision, Gemini (`gemini`, plus `gemini_v2` with a tuned meter prompt); `*_prep` variants flatten the page first |
| `paddle_ocr.js` | PaddleOCR PP-OCRv5 (mobile detection, Latin recognition) via `@rustors/node` |
| `layout.py` | Rebuilds text lines from boxes, correcting for photo tilt |
| `vnd_parser.py` | Finds total, date and meter reading in OCR text (VND formats, `k`/`tr`) |
| `preprocess.py` | Page detection, perspective flattening, light correction |
| `run_spike.py` | Runs engines, writes `results/<engine>_raw.jsonl` and `_scored.csv` |
| `summarise.py` | Accuracy by kind and difficulty, latency, confidence → `results/summary.md` |

## Adding real photos

Put photos in `data/real/images/` (blur names, phone and account numbers) and
add one row per photo to `data/real/labels.csv`: `kind` is `receipt`, `bill`
or `meter`; fill `total` and `date` (DD/MM/YYYY) for documents, or
`meter_reading` (whole number, no decimals) for meters.
