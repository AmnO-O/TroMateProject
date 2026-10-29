"""Rebuild text lines from word/line boxes, allowing for a tilted photo.

Both classic engines lose the pairing between a label ("Tổng cộng:") and its
amount when the photo is tilted or the receipt has two columns. We estimate the
page tilt from the boxes, undo it, then group boxes into rows.
"""
from statistics import median


def rebuild_lines(boxes):
    """boxes: dicts with text, cx, cy, h and (optional) slope of the box's top edge."""
    if not boxes:
        return ""
    slopes = [b["slope"] for b in boxes if b.get("slope") is not None]
    slope = median(slopes) if slopes else 0.0
    for b in boxes:
        b["row_y"] = b["cy"] - slope * b["cx"]
    rows = []
    for b in sorted(boxes, key=lambda b: b["row_y"]):
        last = rows[-1] if rows else None
        if last and abs(last["y"] - b["row_y"]) < 0.55 * max(b["h"], last["h"]):
            last["items"].append(b)
            last["y"] = sum(i["row_y"] for i in last["items"]) / len(last["items"])
        else:
            rows.append({"y": b["row_y"], "h": b["h"], "items": [b]})
    return "\n".join(" ".join(i["text"] for i in sorted(r["items"], key=lambda i: i["cx"])) for r in rows)


def tesseract_line_slopes(data):
    """Tilt of each Tesseract line, from the centres of its words."""
    lines = {}
    for i, word in enumerate(data["text"]):
        if word.strip():
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append((data["left"][i] + data["width"][i] / 2,
                                              data["top"][i] + data["height"][i] / 2))
    slopes = {}
    for key, pts in lines.items():
        if len(pts) >= 2 and pts[-1][0] - pts[0][0] > 40:
            n = len(pts)
            mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
            den = sum((p[0] - mx) ** 2 for p in pts)
            slopes[key] = sum((p[0] - mx) * (p[1] - my) for p in pts) / den if den else None
    return slopes
