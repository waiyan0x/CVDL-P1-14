"""Export the benchmark's text references without images or model predictions."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"front_eds_num": "bus_number", "front_eds_destination": "destination",
          "front_eds_route": "route_text"}
COLUMNS = ["review_id", "split", "input_set", "field", "text", "legibility",
           "field_status", "scoring_eligible", "exclusion_reason", "label_source",
           "reviewer", "reviewer_type", "reviewed_at", "original_training_text",
           "crop", "crop_sha256", "matching_record_id", "matching_crop"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--matching", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--zip", type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists() or a.zip.exists():
        raise SystemExit("Refusing to overwrite an export or ZIP")
    manifest = json.loads(a.manifest.read_text())
    original = {r["review_id"]: r for r in csv.DictReader(
        (ROOT / "evaluation/ocr_dataset/labels.csv").open(encoding="utf-8"))}
    records = [json.loads(s) for s in (a.matching / "matching_inputs.jsonl").read_text().splitlines()]
    matching = {r["review_id"]: r for r in records if r["field"] != "front_eds"}
    rows = []
    for r in manifest["rows"]:
        rid, split = r["review_id"], r["split"]
        m = matching.get(rid)
        if split in ("valid", "test"):
            assert m is not None and m["split"] == split, rid
            assert sha(a.matching / m["crop"]) == r["crop_sha256"], rid
        origin = r.get("label_source") or original.get(rid, {}).get("label_source") or "human_reviewed_transcription_initial_origin_not_recorded"
        rows.append(dict(review_id=rid, split=split, input_set=r["crop_source"],
                         field=FIELDS[r["label"]], text=r["transcription"],
                         legibility=r["legibility"], field_status=r["field_status"],
                         scoring_eligible=str(r["scoring_eligible"]),
                         exclusion_reason=";".join(r["scoring_blockers"]),
                         label_source=origin, reviewer=r.get("reviewer", ""),
                         reviewer_type=r.get("reviewer_type", ""),
                         reviewed_at=r.get("reviewed_at", ""),
                         original_training_text=original[rid]["text"] if split == "train" else "",
                         crop=r["crop"], crop_sha256=r["crop_sha256"],
                         matching_record_id=m["record_id"] if m else "",
                         matching_crop=m["crop"] if m else ""))
    assert len(rows) == len({r["review_id"] for r in rows})
    rows.sort(key=lambda r: (r["split"], r["input_set"], r["review_id"]))
    eligible = [r for r in rows if r["split"] in ("valid", "test") and r["scoring_eligible"] == "True"]
    # Verify final text labels against the separate matching label files.
    handoff_labels = {}
    for name in ("validation_labels.csv", "test_labels.csv"):
        handoff_labels.update({r["review_id"]: r for r in csv.DictReader((a.matching / name).open(encoding="utf-8"))})
    for r in rows:
        if r["split"] in ("valid", "test"):
            h = handoff_labels[r["review_id"]]
            assert all(r[k] == h[k] for k in ("text", "legibility", "field_status")), r["review_id"]
    a.output.mkdir(parents=True)
    write_csv(a.output / "labels.csv", rows)
    write_csv(a.output / "evaluation_labels.csv", eligible)
    summary = {s: {"rows": sum(r["split"] == s for r in rows),
                   "scorable": sum(r["split"] == s and r["scoring_eligible"] == "True" for r in rows)}
               for s in ("train", "valid", "test")}
    readme = '''# Reviewed OCR text-label handoff — 19 November 2026

This is the crop-to-text reference dataset, not Brendan's image/box dataset and
not OCR predictions. `text` is the reference transcription used by the benchmark.
Use the same references for pretrained and fine-tuned models.

- `labels.csv`: all 776 benchmark rows: train 387, validation 271, test 118.
- `evaluation_labels.csv`: the 175 eligible held-out rows only: validation 130
  (79 annotation, 51 detector crops), test 45 annotation crops.
- Train: 384 currently scorable rows, diagnostic only; primarily AI labels.
  `original_training_text` preserves the labels actually used for training;
  `text` includes the benchmark's four recorded human spot-check overrides.
  This export does not retrain models or change their training labels.
- Human-confirmed validation/test readings include manual corrections. Review
  provenance is retained; an AI label is not promoted to human ground truth.
- Unreadable/partial, wrong-field, challenge and train-overlap rows remain in
  `labels.csv` with exclusion reasons; they have not been silently discarded.

Read CSVs with a CSV parser: `text` can contain quoted real line breaks. Preserve
case, punctuation, abbreviations and `[UNK]`; do not infer text from route data.
Scoring uses NFC, casefold, NFC and collapsed whitespace; punctuation remains.
Failed/missing predictions count as empty. Train scores are diagnostic only.
TEST is not for training or threshold tuning; prior model selection used TEST,
so it is not an independent final estimate. Synthetic images are not included.

`review_id` identifies the crop. `crop` preserves its benchmark source path;
it is not a path relative to this text-only package. For validation/test,
`matching_record_id` joins to the selected-model matching handoff, and
`matching_crop` locates its image inside that package. Crop SHA-256 values were
verified against all 389 packaged validation/test images. No train images are
included and train pixels were not re-verified by this export.

Matching handoff: `.runtime/ocr-matching-final-20261119.zip` (separate package).
It contains raw/normalised selected-model OCR, separate validation/test labels,
route reference, weights, crop/source images, inference code and an ownership
review form. Display ownership remains a geometry proposal until human review;
text-label review does not establish that fields belong to the same bus.

See `manifest.json` for source hashes, exact counts and file hashes. This export
is derived from the benchmark's frozen labels; it is not a new human review.
'''
    (a.output / "README.md").write_text(readme)
    evidence = {"source_benchmark_manifest": a.manifest.as_posix(),
                "source_benchmark_manifest_sha256": sha(a.manifest),
                "review_inputs": manifest["review_inputs"], "counts": summary,
                "held_out_eligible_rows": len(eligible),
                "matching_handoff_manifest_sha256": sha(a.matching / "handoff_manifest.json"),
                "validation_test_crop_hashes_verified": len(matching),
                "validation_test_texts_equal_matching_handoff": True,
                "files_sha256": {p.name: sha(p) for p in sorted(a.output.iterdir())}}
    (a.output / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
    a.zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.zip, "x", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(a.output.iterdir()):
            z.write(p, p.name)
    with zipfile.ZipFile(a.zip) as z:
        assert z.testzip() is None
        assert list(csv.DictReader(io.StringIO(z.read("labels.csv").decode()))) == rows
    print(json.dumps({"counts": summary, "eligible_evaluation_rows": len(eligible),
                      "output": str(a.output), "zip": str(a.zip)}, indent=2))


if __name__ == "__main__":
    main()
