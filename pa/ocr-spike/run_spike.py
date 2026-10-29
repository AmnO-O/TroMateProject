"""Run every available OCR engine on a labelled image set and score it.

Usage:
  python run_spike.py --data data/synthetic                 # all engines it can run
  python run_spike.py --data data/synthetic --engines gemini

Cloud engines run only when their API key is set (GOOGLE_VISION_API_KEY,
GEMINI_API_KEY); put them in a local .env, never in the repo.
"""
import argparse
import csv
import json
import os
from pathlib import Path

from engines import ENGINES

ROOT = Path(__file__).resolve().parent


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def as_int(value):
    try:
        return int(str(value).replace(".", "").replace(",", "")) if value not in ("", None) else None
    except ValueError:
        return None


def score(labels, results):
    """Per image: is each field exactly right?"""
    rows = []
    for lab in labels:
        r = results[lab["path"]]
        f = r["fields"]
        row = {"id": lab["id"], "kind": lab["kind"], "difficulty": lab["difficulty"],
               "ms": round(r["ms"]), "confidence": round(r["confidence"], 3)}
        if lab["kind"] == "meter":
            row["truth"] = lab["meter_reading"]
            row["got"] = f.get("meter_reading")
            row["main_ok"] = as_int(f.get("meter_reading")) == as_int(lab["meter_reading"])
            row["date_ok"] = ""
        else:
            row["truth"] = lab["total"]
            row["got"] = f.get("total")
            # total_alt: a second defensible answer, e.g. before rounding or vouchers
            accepted = {as_int(lab["total"]), as_int(lab.get("total_alt"))} - {None} or {None}
            row["main_ok"] = as_int(f.get("total")) in accepted
            row["date_ok"] = (f.get("date") or "") == lab["date"] if lab["date"] else ""
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic")
    ap.add_argument("--engines", default=",".join(ENGINES))
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    load_env()
    data = ROOT / args.data
    out = ROOT / args.out
    out.mkdir(exist_ok=True)
    with open(data / "labels.csv", encoding="utf-8") as f:
        labels = list(csv.DictReader(f))
    for lab in labels:
        lab["path"] = str(data / "images" / f"{lab['id']}.jpg")
    paths = [lab["path"] for lab in labels]
    kinds = [lab["kind"] for lab in labels]

    for name in args.engines.split(","):
        fn, key = ENGINES[name]
        if key and not os.environ.get(key):
            print(f"skip {name}: set {key} to run it")
            continue
        print(f"running {name} on {len(paths)} images...")
        results = fn(paths, kinds)
        with open(out / f"{name}_raw.jsonl", "w", encoding="utf-8") as f:
            for lab in labels:
                f.write(json.dumps({"id": lab["id"], **results[lab["path"]]}, ensure_ascii=False) + "\n")
        rows = score(labels, results)
        with open(out / f"{name}_scored.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        ok = sum(r["main_ok"] for r in rows)
        print(f"  {name}: {ok}/{len(rows)} main field correct")
    print("summarise with: python summarise.py")


if __name__ == "__main__":
    main()
