"""Build the step 6 scoring snapshot: six model versions on train/valid/test.

Usage: .venv/bin/python scripts/build_step6_scoring.py OUTPUT_DIR

- valid: human-verified labels (validation.source.corrected-P065.csv), annotation
  and detector crops, official.
- test: human-confirmed labels (test.source.confirmed.csv), annotation crops only,
  official.
- train: the 387 AI training labels used for fine-tuning, DIAGNOSTIC only (the
  human spot-check rated 27/50 of them not fully legible). The scorer accepts
  only predictions for crops in its review list, so train runs are copied with
  predictions filtered to those 387 crops; nothing else is changed.

Uses the existing scorer (backend/app/evaluation/crop_scoring.py) unchanged.

Since normalised-v6: validation uses the `-valid-layoutv2` runs (layout
v4-lines-v2, fixing A095/P034), and the reviewer's final spot-check readings in
TRAIN_OVERRIDES replace four training labels for diagnostic scoring only.
Snapshot normalised-v5-step6-20261117 was built by the earlier version of this
script (layout v4-lines-v1, no overrides).
"""
import csv
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.crop_scoring import freeze_manifest, build_report, write_report  # noqa: E402

VALID = ROOT / "evaluation/ocr_review/human-verification-20261116/validation.source.corrected-P065.csv"
TEST = ROOT / "evaluation/ocr_review/test-confirmation-20261117/test.source.confirmed.csv"
TRAIN_SOURCE = ROOT / "evaluation/ocr_review/human-verification-20261113/training.source.csv"
TRAIN_LABELS = ROOT / ".runtime/ocr-text-dataset-20261116/labels.csv"
TRAIN_OVERRIDES = ROOT / "evaluation/ocr_review/train-spotcheck-20261117/train_label_overrides.csv"
# Override with OCR_VALID_RUN_SUFFIX=-valid-layoutv3 to score layout v4-lines-v3 runs.
VALID_RUN_SUFFIX = os.environ.get("OCR_VALID_RUN_SUFFIX", "-valid-layoutv2")
RUNS = ROOT / "evaluation/ocr_runs"
MODELS = {"easyocr": "easyocr", "trocr": "trocr", "paddleocr": "paddleocr"}


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    # Train: the 387 fine-tuning labels, as a review source with an explicit population.
    labels = {r["review_id"]: r for r in csv.DictReader(open(TRAIN_LABELS, encoding="utf-8"))
              if r["split"] == "train" and r["scoring_eligible"] == "True"}
    with open(TRAIN_SOURCE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames) + ["crop_source", "label_source"]
        rows = [r for r in reader if r["review_id"] in labels]
    if len(rows) != len(labels):
        raise SystemExit("Training source is missing selected label IDs")
    overrides = {o["training_review_id"]: o for o in csv.DictReader(open(TRAIN_OVERRIDES, encoding="utf-8"))}
    for r in rows:
        if r["transcription"] != labels[r["review_id"]]["text"]:
            raise SystemExit(f"Label text differs for {r['review_id']}")
        r.update(crop_source="annotation", label_source="codex_ai_3copy_consensus (diagnostic)")
        if r["review_id"] in overrides:
            o = overrides[r["review_id"]]
            if o["original_text"] != r["transcription"]:
                raise SystemExit(f"Override does not match label for {r['review_id']}")
            r.update(transcription=o["text"], legibility=o["legibility"],
                     label_source=f"human spot-check {o['spotcheck_id']} (diagnostic)")
    train_source = out / "train.selected387.source.csv"
    with open(train_source, "x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    manifest = freeze_manifest([str(VALID), str(TEST), str(train_source)])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

    # Train runs filtered to the 387 crops (exact copies of those prediction lines).
    filtered = out / "train_runs_filtered"
    config = {"models": []}
    for model in MODELS:
        variants = {}
        for variant, tag in (("baseline", "pretrained"), ("finetuned", "finetuned")):
            src = RUNS / f"{model}-{tag}-train"
            dst = filtered / src.name
            dst.mkdir(parents=True)
            shutil.copy2(src / "report.json", dst / "report.json")
            kept = [line for line in (src / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip() and json.loads(line)["review_id"] in labels]
            if len(kept) != len(labels):
                raise SystemExit(f"{src.name} lacks predictions for some selected crops")
            (dst / "predictions.jsonl").write_text("\n".join(kept) + "\n", encoding="utf-8")
            variants[variant] = {"runs": [
                {"run_dir": f"train_runs_filtered/{src.name}", "splits": ["train"], "input_sets": ["annotation"]},
                {"run_dir": f"../../ocr_runs/{model}-{tag}{VALID_RUN_SUFFIX}", "splits": ["valid"],
                 "input_sets": ["annotation", "prediction"]},
                {"run_dir": f"../../ocr_runs/{model}-{tag}-test", "splits": ["test"], "input_sets": ["annotation"]},
            ]}
        config["models"].append({"id": model, **variants})
    (out / "comparison.json").write_text(json.dumps(config, indent=2) + "\n")
    report = build_report(manifest, config, out)
    write_report(report, out / "scores")
    eligible = {}
    for r in manifest["rows"]:
        if r["scoring_eligible"]:
            key = f"{r['split']}/{r['crop_source']}"
            eligible[key] = eligible.get(key, 0) + 1
    print(json.dumps({"rows": len(manifest["rows"]), "eligible": eligible}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
