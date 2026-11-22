"""Benchmark a detector-confidence rule for destination/route crops on the labelled photos.

Rule tested: a destination or route crop is used for OCR only if YOLO11s gave its box a confidence of at
least T; below T that field is dropped and the whole-display text (number tokens removed) is used instead.
The number crop is always kept. T = 0.50 is today's behaviour (the detector's own confidence filter).

Step 1 reads every photo once (nearest display; every crop's text, detector confidence, OCR confidence).
Step 2 re-runs only the matcher for each T at the settings in use.

    python scripts/benchmark_crop_confidence.py
    python scripts/benchmark_crop_confidence.py --reuse-ocr
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.match_reference as mr  # noqa: E402
from backend.app.services.reference_matching import DisplayMatcher, Reference  # noqa: E402
from scripts.benchmark_photo_threshold import score  # noqa: E402

OUT = ROOT / "evaluation/photo_benchmark"
THRESHOLDS = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 1.01]   # 1.01 = never use destination/route crops
FIELDS = ("number", "destination", "route", "panel")


def read_photos(labels, photo_dir, detector):
    readers = mr.make_readers(SimpleNamespace(ocr_model_dir=None, panel_ocr_model_dir=None))
    rows = []
    for lab in labels:
        path = next(photo_dir.glob(lab["photo"] + ".*"))
        displays, _, _ = mr.run_photo(path, detector, readers)
        crops = displays[0]["crops"] if displays else {}
        texts = displays[0]["texts"] if displays else {}
        row = {"photo": lab["photo"], "displays": len(displays)}
        for f in FIELDS:
            row[f] = texts.get(f) or ""
            row[f"{f}_det_conf"] = (crops.get(f) or {}).get("detector_confidence") or ""
            row[f"{f}_ocr_conf"] = (crops.get(f) or {}).get("ocr_confidence") or ""
        rows.append(row)
        print(lab["photo"], {f: (row[f], row[f"{f}_det_conf"]) for f in FIELDS})
    return rows


def apply_rule(rows, threshold):
    out = []
    for r in rows:
        r = dict(r)
        for f in ("destination", "route"):
            conf = r[f"{f}_det_conf"]
            if r[f] and conf != "" and float(conf) < threshold:
                r[f] = ""
        out.append(r)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--photos", type=Path, default=ROOT / "models/local/photos/benchmark")
    p.add_argument("--detector", type=Path, default=mr.DEFAULT_DETECTOR)
    p.add_argument("--reuse-ocr", action="store_true")
    args = p.parse_args()
    labels = list(csv.DictReader(open(OUT / "labels.csv", encoding="utf-8")))
    cache = OUT / "results/crop_readings.csv"
    if args.reuse_ocr:
        rows = list(csv.DictReader(open(cache, encoding="utf-8")))
    else:
        rows = read_photos(labels, args.photos, args.detector)
        with open(cache, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    matcher = DisplayMatcher(Reference(ROOT / "data/reference/bus_information.cleaned.csv"), mr.default_settings())
    grid = []
    for t in THRESHOLDS:
        res, _ = score(labels, apply_rule(rows, t), matcher)
        dropped = sum(1 for r in rows for f in ("destination", "route")
                      if r[f] and r[f"{f}_det_conf"] != "" and float(r[f"{f}_det_conf"]) < t)
        grid.append({"threshold": t, "crops_dropped": dropped, **res})
        print(grid[-1])
    with open(OUT / "results/crop_confidence_grid.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(grid[0])); w.writeheader(); w.writerows(grid)
    json.dump({"thresholds": THRESHOLDS}, open(OUT / "results/crop_confidence_run.json", "w"))


if __name__ == "__main__":
    main()
