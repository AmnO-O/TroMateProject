"""Summarise scored results into one table per engine: accuracy by document
kind and difficulty, latency, and whether confidence flags the misses."""
import argparse
import csv
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent


def pct(ok, n):
    return f"{ok}/{n} ({100 * ok / n:.0f}%)" if n else "-"


def p95(values):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(0.95 * (len(values) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    args = ap.parse_args()
    folder = ROOT / args.results
    lines = ["| Engine | Receipts total | Bills total | Meter reading | Easy | Medium | Hard | Dates | p50 ms | p95 ms | Conf. right / wrong |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for path in sorted(folder.glob("*_scored.csv")):
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        ok = lambda rs: sum(r["main_ok"] == "True" for r in rs)
        by = lambda key, val: [r for r in rows if r[key] == val]
        dated = [r for r in rows if r["date_ok"] in ("True", "False")]
        right = [float(r["confidence"]) for r in rows if r["main_ok"] == "True"]
        wrong = [float(r["confidence"]) for r in rows if r["main_ok"] != "True"]
        ms = [float(r["ms"]) for r in rows]
        name = path.name.replace("_scored.csv", "")
        cells = [name,
                 pct(ok(by("kind", "receipt")), len(by("kind", "receipt"))),
                 pct(ok(by("kind", "bill")), len(by("kind", "bill"))),
                 pct(ok(by("kind", "meter")), len(by("kind", "meter"))),
                 pct(ok(by("difficulty", "easy")), len(by("difficulty", "easy"))),
                 pct(ok(by("difficulty", "medium")), len(by("difficulty", "medium"))),
                 pct(ok(by("difficulty", "hard")), len(by("difficulty", "hard"))),
                 pct(sum(r["date_ok"] == "True" for r in dated), len(dated)),
                 f"{median(ms):.0f}", f"{p95(ms):.0f}",
                 f"{mean(right):.2f} / {mean(wrong):.2f}" if right and wrong else "-"]
        lines.append("| " + " | ".join(cells) + " |")
    table = "\n".join(lines)
    (folder / "summary.md").write_text(table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
