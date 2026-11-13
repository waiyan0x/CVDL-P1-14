"""Verify paired saved baselines and export every failure without running OCR."""

import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.crop_scoring import freeze_manifest, load_run
from backend.app.evaluation.review_decisions import digest


def check_prediction(prediction, entry):
    rid = entry["review_id"]
    for key in ("input_width", "input_height", "line_quads", "line_count"):
        if prediction.get(key) != entry[key]:
            raise ValueError(f"Frozen layout mismatch: {rid}/{key}")
    regions = [[min(p[0] for p in q), min(p[1] for p in q),
                max(p[0] for p in q), max(p[1] for p in q)] for q in entry["line_quads"]]
    if prediction.get("line_regions") != regions:
        raise ValueError(f"Line regions mismatch: {rid}")
    if entry["review_status"] == "unresolved":
        if (prediction["status"] != "error" or prediction["raw_text"]
                or prediction.get("line_outputs") or not prediction.get("error")):
            raise ValueError(f"Unresolved layout was skipped or replaced: {rid}")
    elif prediction["status"] == "success" and len(prediction["line_outputs"]) != entry["line_count"]:
        raise ValueError(f"Missing successful line outputs: {rid}")
    if prediction["status"] == "error" and not prediction.get("error"):
        raise ValueError(f"Missing failure reason: {rid}")
    for index, line in enumerate(prediction.get("line_outputs", [])):
        if index >= len(regions) or line.get("quad_xy") != entry["line_quads"][index]:
            raise ValueError(f"Line output geometry mismatch: {rid}")
        q = entry["line_quads"][index]
        size = [entry["input_width"], math.ceil(max(q[3][1]-q[0][1], q[2][1]-q[1][1]))]
        if (line.get("line_input_size") != size or line.get("index") != index
                or line.get("box_xyxy") != regions[index]):
            raise ValueError(f"Line output size/order mismatch: {rid}")


def audit(reviews, config_path, layout_path, output):
    if output.exists():
        raise FileExistsError(output)
    manifest = freeze_manifest(reviews)
    if any(r["split"] != "valid" for r in manifest["rows"]):
        raise ValueError("Validation-only audit; reserved test is not accessed")
    inventory = {r["review_id"]: r for r in manifest["rows"]}
    layout_hash = digest(layout_path)
    if layout_path.with_suffix(".sha256").read_text().split()[0] != layout_hash:
        raise ValueError("Layout checksum mismatch")
    entries = json.loads(layout_path.read_text())["entries"]
    layout = {r["review_id"]: r for r in entries}
    if len(layout) != len(entries) or set(layout) != set(inventory):
        raise ValueError("Layout inventory mismatch")
    for rid, entry in layout.items():
        if any(entry[a] != inventory[rid][b] for a, b in (
                ("crop_id", "crop"), ("crop_sha256", "crop_sha256"),
                ("crop_set", "crop_source"), ("field", "label"))):
            raise ValueError("Layout crop identity mismatch")
    config = json.loads(config_path.read_text())
    if Counter(m["id"] for m in config["models"]) != Counter(["easyocr", "trocr", "paddleocr"]):
        raise ValueError("Exactly three baseline models required")
    failures, paired, summaries, snapshot_hashes, evidence, histories = [], {}, [], [], {}, []
    for model in config["models"]:
        root = (config_path.resolve().parent / model["baseline"]["run_dir"]).resolve()
        predictions, identity = load_run(root, inventory)
        report = json.loads((root / "report.json").read_text())
        if (set(predictions) != set(inventory) or report.get("inputs") != len(inventory)
                or report.get("split") != "valid"):
            raise ValueError("Run omitted crops or changed population")
        if (report.get("frozen_line_layout", {}).get("sha256") != layout_hash
                or report.get("cached_weights_unchanged") is not True
                or report.get("source_workspace_unchanged") is not True):
            raise ValueError("Run integrity/layout declarations differ")
        core = root / ("core_source.py" if (root / "core_source.py").exists() else "ocr_crop_baseline.py")
        geometry = root / ("layout_source.py" if (root / "layout_source.py").exists() else "ocr_line_layout.py")
        snapshot_hashes.append((digest(core), digest(geometry)))
        evidence[model["id"]] = {"run_dir": str(root), "identity": identity,
                                 "core_source_sha256": digest(core), "layout_source_sha256": digest(geometry)}
        history_path = root / "engine_history.json"
        if history_path.exists():
            evidence[model["id"]]["engine_history_sha256"] = digest(history_path)
            histories.extend({"model": model["id"], **record} for record in json.loads(history_path.read_text())
                             if predictions[record["review_id"]]["status"] == "error")
        for rid, prediction in predictions.items():
            check_prediction(prediction, layout[rid])
            row = paired.setdefault(rid, {"review_id": rid, "crop_sha256": prediction["crop_sha256"],
                                          "layout_status": layout[rid]["review_status"]})
            row[model["id"] + "_status"] = prediction["status"]
            row[model["id"] + "_empty"] = prediction["status"] == "success" and not prediction["raw_text"].strip()
            if prediction["status"] == "error":
                failures.append({"model": model["id"], **prediction})
        counts = dict(attempted=len(predictions), completed=sum(p["status"] == "success" for p in predictions.values()),
                      failed=sum(p["status"] == "error" for p in predictions.values()),
                      empty_successes=sum(p["status"] == "success" and not p["raw_text"].strip() for p in predictions.values()))
        for summary in report["summary"]:
            selected = [p for p in predictions.values() if p["crop_set"] == summary["crop_set"]
                        and (summary["field"] == "all" or p["field"] == summary["field"])]
            actual = [len(selected), sum(p["status"] == "success" for p in selected),
                      sum(p["status"] == "error" for p in selected),
                      sum(p["status"] == "success" and not p["raw_text"].strip() for p in selected)]
            if actual != [summary[k] for k in ("attempted", "completed", "errors", "empty_outputs")]:
                raise ValueError("Saved summary disagrees with retained predictions")
        summaries.append(dict(model=model["id"], device=report["actual_device"], **counts))
    if len(set(snapshot_hashes)) != 1:
        raise ValueError("Models used different shared crop/layout source snapshots")
    output.mkdir(parents=True)
    with (output / "failures.jsonl").open("x") as handle:
        for failure in failures:
            handle.write(json.dumps(failure, ensure_ascii=False) + "\n")
    (output / "failed_engine_history.json").write_text(json.dumps(histories, indent=2) + "\n")
    with (output / "paired_status.csv").open("x", newline="") as handle:
        rows = [paired[rid] for rid in sorted(paired)]
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = dict(validation_crops=len(inventory), layout_sha256=layout_hash,
                  shared_crop_layout_sources_identical=True, models=summaries,
                  retained_failures=len(failures), evidence=evidence,
                  empty_definition="Successful raw output is empty or whitespace-only; saved text is unchanged.",
                  accuracy_calculated=False, reserved_test_accessed=False,
                  limit="Saved identities, geometry and shared code agree; historical line pixel buffers were not independently hashed.")
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, action="append", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--line-layout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.review, args.config, args.line_layout, args.output), indent=2))
