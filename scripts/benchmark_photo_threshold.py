"""Benchmark the similarity cutoff on labelled bus photos (full chain: YOLO11s -> PaddleOCR -> matching).

Labels are written before the run: evaluation/photo_benchmark/labels.csv (service on the sign, the sign's
destination text, and the reference endpoint it denotes, or NONE when the text is not an endpoint of
that service, so the correct output is to withhold the destination).

Step 1 reads every photo once (nearest display only, as the app shows it) and caches the OCR text.
Step 2 re-runs only the matcher at each cutoff; every other setting stays at the one in use.

    python scripts/benchmark_photo_threshold.py                      # photos in models/local/photos/benchmark
    python scripts/benchmark_photo_threshold.py --reuse-ocr          # skip step 1, use the cached readings
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.match_reference as mr  # noqa: E402
from backend.app.services.reference_matching import DisplayMatcher, Reference  # noqa: E402

OUT = ROOT / "evaluation/photo_benchmark"
CUTOFFS = [25, 40, 50, 55, 60, 65, 70, 75, 80, 90]
FIELDS = ("number", "destination", "route", "panel")


def read_photos(labels, photo_dir, detector):
    readers = mr.make_readers(SimpleNamespace(ocr_model_dir=None, panel_ocr_model_dir=None))
    rows = []
    for lab in labels:
        path = next(photo_dir.glob(lab["photo"] + ".*"), None)
        if path is None:
            sys.exit(f"photo not found: {lab['photo']}")
        start = time.perf_counter()
        displays, boxes, timing = mr.run_photo(path, detector, readers)
        nearest = displays[0]["texts"] if displays else {}
        rows.append({"photo": lab["photo"], "displays": len(displays), **{f: nearest.get(f) or "" for f in FIELDS},
                     "panel_lines": " || ".join(nearest.get("panel_lines") or []),
                     "frame_ms": round(timing["detection_ms"] + timing["ocr_ms"], 1)})
        print(f"{lab['photo']}: {len(displays)} display(s), nearest {nearest} ({time.perf_counter() - start:.1f} s)")
    return rows


def score(labels, readings, matcher):
    gold = {l["photo"]: l for l in labels}
    res = {"svc_correct": 0, "svc_wrong": 0, "svc_withheld": 0, "dest_correct": 0, "dest_wrong": 0,
           "dest_missed": 0, "none_withheld": 0, "none_shown": 0, "positives": 0, "negatives": 0}
    per = []
    for r in readings:
        g = gold[r["photo"]]
        if r["displays"] in (0, "0"):
            out = matcher.match(detected=False)
        else:
            lines = [l for l in (r.get("panel_lines") or "").split(" || ") if l]
            out = matcher.match(**{f: (r[f] or None) for f in FIELDS}, panel_lines=lines or None)
        svc, dest = out.get("service"), out.get("destination")
        if svc is None:
            res["svc_withheld"] += 1
        elif svc == g["service"]:
            res["svc_correct"] += 1
        else:
            res["svc_wrong"] += 1
        if g["gold_destination"] == "NONE":
            res["negatives"] += 1
            res["none_withheld" if dest is None else "none_shown"] += 1
            verdict = "correct (withheld)" if dest is None else "wrong (shown)"
        else:
            res["positives"] += 1
            if dest == g["gold_destination"]:
                res["dest_correct"] += 1; verdict = "correct"
            elif dest is None:
                res["dest_missed"] += 1; verdict = "withheld"
            else:
                res["dest_wrong"] += 1; verdict = "wrong"
        per.append({"photo": r["photo"], "gold_service": g["service"], "gold_destination": g["gold_destination"],
                    "service": svc or "", "destination": dest or "", "score": out.get("destination_score") or "",
                    "candidate": out.get("candidate") or out.get("runner_up") or "", "status": out["status"],
                    "verdict": verdict})
    res["dest_shown_wrong"] = res["dest_wrong"] + res["none_shown"]
    res["dest_net"] = res["dest_correct"] + res["none_withheld"] - res["dest_shown_wrong"]
    return res, per


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--photos", type=Path, default=ROOT / "models/local/photos/benchmark")
    p.add_argument("--detector", type=Path, default=mr.DEFAULT_DETECTOR)
    p.add_argument("--reuse-ocr", action="store_true")
    args = p.parse_args()
    labels = list(csv.DictReader(open(OUT / "labels.csv", encoding="utf-8")))
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    cache = OUT / "results/ocr_readings.csv"
    if args.reuse_ocr:
        readings = list(csv.DictReader(open(cache, encoding="utf-8")))
    else:
        readings = read_photos(labels, args.photos, args.detector)
        with open(cache, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(readings[0])); w.writeheader(); w.writerows(readings)

    reference = Reference(ROOT / "data/reference/bus_information.cleaned.csv")
    grid, per_by_cutoff = [], {}
    for cutoff in CUTOFFS:
        settings = mr.default_settings(); settings.cutoff = float(cutoff)
        res, per = score(labels, readings, DisplayMatcher(reference, settings))
        grid.append({"cutoff": cutoff, **res}); per_by_cutoff[cutoff] = per
    with open(OUT / "results/cutoff_grid.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(grid[0])); w.writeheader(); w.writerows(grid)
    in_use = int(mr.default_settings().cutoff)
    with open(OUT / "results/per_photo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(per_by_cutoff[in_use][0])); w.writeheader(); w.writerows(per_by_cutoff[in_use])
    json.dump({"cutoffs": CUTOFFS, "in_use": in_use}, open(OUT / "results/run.json", "w"))
    for g in grid:
        print(g)


if __name__ == "__main__":
    main()
