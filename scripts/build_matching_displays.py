"""Group Cody's fine-tuned PaddleOCR crop readings into displays for matching.

Each photo can show several bus displays, so fields are assigned to the panel
(front_eds) box that contains them, using the app's own association code
(backend/app/services/association.py). Fields outside every panel are paired
by geometry, as the app does. Human labels are attached for evaluation only.

    python scripts/build_matching_displays.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.association import associate_displays  # noqa: E402

INPUTS = ROOT / "evaluation/reference_matching/inputs"
LABEL_MAP = {"front_eds": "eds", "front_eds_num": "bus_number",
             "front_eds_destination": "destination", "front_eds_route": "route"}
FIELD_KEYS = {"bus_number": "number", "destination": "destination", "route": "route"}
SPLITS = {
    "valid": {"labels": "valid_labels.csv", "fields": "paddle_ft_valid_fields.jsonl"},
    "test": {"labels": "test_labels.csv", "fields": "paddle_ft_test_fields.jsonl"},
}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def usable_label(row):
    text = (row.get("transcription") or "").strip()
    return (row.get("legibility") == "full" and row.get("field_status") == "present"
            and text and "[UNK]" not in text)


def build(split, files):
    with (INPUTS / files["labels"]).open(newline="", encoding="utf-8-sig") as stream:
        labels = list(csv.DictReader(stream))
    predictions = {p["review_id"]: p for p in read_jsonl(INPUTS / files["fields"])}
    panels = [p for p in read_jsonl(INPUTS / "paddle_ft_panels.jsonl") if p["split"] == split]

    photos = defaultdict(list)
    for row in labels:
        if row["label"] not in LABEL_MAP or row["label"] == "front_eds":
            continue
        pred = predictions.get(row["review_id"], {})
        photos[(row["crop_source"], row["image"])].append({
            "label": LABEL_MAP[row["label"]], "box": json.loads(row["box_xyxy"]), "confidence": 1.0,
            "review_id": row["review_id"], "raw": pred.get("raw_text"), "ocr_status": pred.get("status", "missing"),
            "ocr_confidence": pred.get("ocr_confidence"),
            "label_text": (row.get("transcription") or "").strip(), "legibility": row.get("legibility"),
            "field_status": row.get("field_status"), "label_usable": usable_label(row)})
    for panel in panels:
        photos[(panel["crop_set"], panel["source_image"])].append({
            "label": "eds", "box": panel["box_xyxy"], "confidence": 1.0, "review_id": panel["review_id"],
            "raw": panel.get("raw_text"), "ocr_status": panel.get("status")})

    displays, notes = [], Counter()
    for (crop_set, image), items in sorted(photos.items()):
        width = max(box["box"][2] for box in items) + 1
        height = max(box["box"][3] for box in items) + 1
        groups, _ = associate_displays(items, width, height)
        for group in groups:
            screen = group["screen"]
            display = {"display_key": f"{split}:{crop_set}:{image}:{group['display_id']}",
                       "split": split, "crop_set": crop_set, "image": image,
                       "panel": None, "fields": {}}
            if screen and screen.get("source") != "field_union":
                display["panel"] = {"review_id": screen["review_id"], "raw": screen["raw"], "box": screen["box"]}
            elif screen:
                notes["display_without_panel_box"] += 1
            for label, field in group["fields"].items():
                display["fields"][FIELD_KEYS[label]] = {k: field.get(k) for k in (
                    "review_id", "raw", "ocr_status", "ocr_confidence", "box", "label_text", "legibility",
                    "field_status", "label_usable")}
            displays.append(display)
        assigned = {f["review_id"] for g in groups for f in g["fields"].values()}
        lost = [f["review_id"] for f in items if f["label"] != "eds" and f["review_id"] not in assigned]
        notes["fields_not_selected"] += len(lost)
    return displays, notes


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/reference_matching/displays.jsonl")
    args = parser.parse_args(argv)
    rows, summary = [], {}
    for split, files in SPLITS.items():
        displays, notes = build(split, files)
        rows += displays
        for crop_set in sorted({d["crop_set"] for d in displays}):
            subset = [d for d in displays if d["crop_set"] == crop_set]
            summary[f"{split}/{crop_set}"] = {
                "displays": len(subset), "with_panel": sum(d["panel"] is not None for d in subset),
                **{f"with_{k}": sum(k in d["fields"] for d in subset) for k in ("number", "destination", "route")}}
        summary[f"{split}/notes"] = dict(notes)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
