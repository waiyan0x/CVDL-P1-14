"""Normalised project-ground-truth scoring; no model loading or images."""

from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unicodedata

from .metrics import edit_distance, percentile
from .review_decisions import digest, load_source


FIELDS = ("front_eds_num", "front_eds_destination", "front_eds_route", "front_eds")
MODELS = {"easyocr": "EasyOCR", "trocr": "Public TrOCR", "paddleocr": "PaddleOCR"}
PROTOCOL = {
    "id": "eds-crop-normalised-v2",
    "unicode": "NFC, Unicode casefold, NFC",
    "whitespace": "collapse all Unicode whitespace to one ASCII space; trim ends",
    "case_and_punctuation": "Unicode casefold; punctuation and abbreviations preserved",
    "wer": "Unicode whitespace tokens",
    "aggregation": "micro edit counts/reference counts; exact per scored crop",
    "failures": "failed or missing predictions are empty hypotheses",
    "exclusions": ["legibility_not_full", "unknown_text", "blank", "wrong_field", "challenge_only",
                   "validation_train_scene_overlap"],
    "reference_matching": False,
}
# Import compatibility for handoff code: there is only one scoring protocol.
NORMALISED_PROTOCOL = PROTOCOL
VALIDATION_OVERLAP_IDS = {*(f"A{i:03d}" for i in range(42, 49)),
                          *(f"P{i:03d}" for i in range(39, 45))}
TEXT_RECORD_COLUMNS = (
    "review_id", "split", "input_set", "field", "crop_sha256", "source_image_sha256",
    "prediction_status", "scoring_eligible", "reference_reviewer_type", "reference_review_status",
    "reference_legibility", "raw_ocr_text", "raw_ocr_scoring_text", "normalised_ocr_text",
    "raw_reference_text", "raw_reference_scoring_text", "normalised_reference_text",
    "raw_scoring_hypothesis", "normalised_scoring_hypothesis",
)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def canonical_text(text):
    """Declared spacing only; never fix case, punctuation or abbreviations."""
    lines = [" ".join(line.split()) for line in unicodedata.normalize("NFC", text).splitlines()]
    return "\n".join(line for line in lines if line)


def normalise_text(text):
    """Casefold and collapse spaces; never expand abbreviations or match references."""
    folded = unicodedata.normalize("NFC", unicodedata.normalize("NFC", text).casefold())
    return " ".join(folded.split())


def text_record(row, prediction):
    """Preserve source strings even when review gates prohibit numerical scoring."""
    raw = prediction["raw_text"] if prediction else None
    status = prediction["status"] if prediction else "missing"
    reference = row["transcription"]
    return {"review_id": row["review_id"], "split": row["split"],
            "input_set": row["crop_source"], "field": row["label"],
            "crop_sha256": row["crop_sha256"], "source_image_sha256": row["source_image_sha256"],
            "prediction_status": status, "scoring_eligible": row["scoring_eligible"],
            "reference_reviewer_type": row.get("reviewer_type", ""),
            "reference_review_status": row["review_status"], "reference_legibility": row["legibility"],
            "raw_ocr_text": raw,
            "raw_ocr_scoring_text": canonical_text(raw) if raw is not None else None,
            "normalised_ocr_text": normalise_text(raw) if raw is not None else None,
            "raw_reference_text": reference, "raw_reference_scoring_text": canonical_text(reference),
            "normalised_reference_text": normalise_text(reference),
            "raw_scoring_hypothesis": canonical_text(raw) if status == "success" else "",
            "normalised_scoring_hypothesis": normalise_text(raw) if status == "success" else ""}


def freeze_manifest(sources):
    rows, inputs, ids = [], [], set()
    for source in sources:
        before = digest(source)
        _, incoming = load_source(source)
        if digest(source) != before:
            raise ValueError("Review input changed during freeze")
        inputs.append({"name": Path(source).name, "sha256": before})
        for row in incoming:
            if row["review_id"] in ids:
                raise ValueError(f"Duplicate review ID: {row['review_id']}")
            ids.add(row["review_id"])
            row["split"] = "valid" if row["split"] == "val" else row["split"]
            population = row.get("crop_source", "")
            if population == "predicted":
                population = "prediction"
            if population not in {"annotation", "prediction"}:
                raise ValueError(f"Explicit annotation/prediction crop_source required: {row['review_id']}")
            row["crop_source"] = population
            rows.append(row)
    if not rows:
        raise ValueError("At least one review row is required")
    set_eligibility(rows)
    payload = {"schema_version": 1, "protocol": PROTOCOL, "review_inputs": inputs,
               "rows": sorted(rows, key=lambda r: r["review_id"]),
               "limitations": ["Label provenance is retained; human review is not a scoring gate.",
                               "Declared hashes checked for correspondence; image bytes are not opened.",
                               "Exact overlap checks do not establish absence of near-duplicate leakage."]}
    return {**payload, "manifest_sha256": fingerprint(payload)}


def set_eligibility(rows):
    """Apply the user's project scoring policy, independently of review metadata."""
    for row in rows:
        reasons = []
        text = row.get("transcription", "")
        if row.get("legibility") != "full":
            reasons.append("legibility_not_full")
        if "[unk]" in text.casefold():
            reasons.append("unknown_text")
        if not text.strip() or row.get("field_status") in {"blank", "absent"}:
            reasons.append("blank")
        if row.get("field_status") == "wrong_field":
            reasons.append("wrong_field")
        if (row.get("user_scope_policy") == "challenge_only"
                or row.get("training_disposition") == "challenge_only"
                or row.get("human_crop_treatment") in {"challenge", "challenge_only"}
                or str(row.get("challenge_only", "")).lower() in {"true", "1", "yes"}):
            reasons.append("challenge_only")
        if row.get("split") in {"valid", "val"} and row["review_id"] in VALIDATION_OVERLAP_IDS:
            reasons.append("validation_train_scene_overlap")
        row["scoring_eligible"] = not reasons
        row["scoring_blockers"] = reasons


def validate_manifest(manifest):
    payload = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if (manifest.get("schema_version") != 1 or manifest.get("protocol") != PROTOCOL
            or fingerprint(payload) != manifest.get("manifest_sha256")):
        raise ValueError("Manifest hash/version/protocol mismatch")
    # Recompute eligibility rather than trusting an edited scoring-ready flag.
    ids = [r["review_id"] for r in manifest["rows"]]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("Missing or duplicate manifest IDs")
    copies = [dict(r) for r in manifest["rows"]]
    set_eligibility(copies)
    for row, checked in zip(manifest["rows"], copies):
        if (row["scoring_eligible"] != checked["scoring_eligible"]
                or row["scoring_blockers"] != checked["scoring_blockers"]):
            raise ValueError("Manifest eligibility disagrees with review evidence")


def load_run(run_dir, inventory):
    root = Path(run_dir)
    report_path, predictions_path = root / "report.json", root / "predictions.jsonl"
    hashes = {"report_sha256": digest(report_path), "predictions_sha256": digest(predictions_path)}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("reference_matching_used") is not False:
        raise ValueError("Run must explicitly record reference_matching_used=false")
    predictions = {}
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        prediction = json.loads(line)
        rid = prediction.get("review_id")
        if rid not in inventory or rid in predictions:
            raise ValueError(f"Unknown or duplicate prediction ID: {rid}")
        truth = inventory[rid]
        for pred_key, truth_key in (("crop_sha256", "crop_sha256"),
                                    ("source_image_sha256", "source_image_sha256"),
                                    ("crop_id", "crop"), ("field", "label"),
                                    ("crop_set", "crop_source")):
            if prediction.get(pred_key) != truth[truth_key]:
                raise ValueError(f"Prediction identity/hash mismatch: {rid}/{pred_key}")
        if (prediction.get("status") not in {"success", "error"}
                or not isinstance(prediction.get("raw_text"), str)):
            raise ValueError(f"Invalid prediction status/text: {rid}")
        latency = prediction.get("crop_total_ms")
        if latency is not None and (type(latency) not in {int, float} or not math.isfinite(latency) or latency < 0):
            raise ValueError(f"Invalid crop latency: {rid}")
        predictions[rid] = prediction
    if digest(report_path) != hashes["report_sha256"] or digest(predictions_path) != hashes["predictions_sha256"]:
        raise ValueError("Run inputs changed while reading")
    identity_keys = ("engine", "model", "model_provenance", "model_sha256_before",
                     "model_sha256_after", "model_files_sha256", "recognition_settings",
                     "preprocessing", "frozen_line_layout", "actual_device", "timing",
                     "warmup_policy", "warmup_runs_per_field", "run_name", "split")
    return predictions, {**hashes, **{k: report[k] for k in identity_keys if k in report}}


def score_cell(rows, predictions, available):
    transform = normalise_text
    eligible = [r for r in rows if r["scoring_eligible"]]
    reasons = Counter(reason for row in rows for reason in row["scoring_blockers"])
    coverage = {"inventory": len(rows), "eligible": len(eligible), "excluded": len(rows)-len(eligible),
                "blocker_counts_overlapping": dict(reasons),
                "legibility_counts": dict(Counter(r.get("legibility", "") for r in rows)),
                "field_status_counts": dict(Counter(r.get("field_status", "") for r in rows))}
    panel = bool(rows) and rows[0]["label"] == "front_eds"
    status = ("Not applicable" if panel else "Not run" if not available else
              "No samples" if not rows else "No scorable crops" if not eligible else "Scored")
    result = {**coverage, "status": status, "cer": None, "wer": None, "exact_match": None,
              "character_errors": 0, "reference_characters": 0, "word_errors": 0,
              "reference_words": 0, "exact_count": 0, "outcomes": [],
              "attempted": sum(r["review_id"] in predictions for r in rows),
              "completed": 0, "failed": 0, "missing": 0, "empty": 0,
              "successful_crop_total_ms_median": None, "successful_crop_total_ms_p95": None}
    present = [predictions[r["review_id"]] for r in rows if r["review_id"] in predictions]
    successful = [p for p in present if p["status"] == "success"]
    result.update(completed=len(successful), failed=len(present)-len(successful),
                  empty=sum(not canonical_text(p["raw_text"]) for p in successful))
    times = [p["crop_total_ms"] for p in successful if p.get("crop_total_ms") is not None]
    result["successful_crop_total_ms_median"] = percentile(times, .5)
    result["successful_crop_total_ms_p95"] = percentile(times, .95)
    if status != "Scored":
        return result
    for row in eligible:
        rid = row["review_id"]
        pred = predictions.get(rid)
        state = pred["status"] if pred else "missing"
        reference = transform(row["transcription"])
        hypothesis = transform(pred["raw_text"]) if state == "success" else ""
        chars, words = edit_distance(reference, hypothesis), edit_distance(reference.split(), hypothesis.split())
        result["character_errors"] += chars
        result["reference_characters"] += len(reference)
        result["word_errors"] += words
        result["reference_words"] += len(reference.split())
        result["exact_count"] += reference == hypothesis
        result["missing"] += state == "missing"
        result["outcomes"].append({"review_id": rid, "status": state, "reference": reference,
                                   "hypothesis": hypothesis, "character_errors": chars,
                                   "reference_characters": len(reference), "word_errors": words,
                                   "reference_words": len(reference.split()), "exact": reference == hypothesis})
    result.update(cer=result["character_errors"]/result["reference_characters"],
                  wer=result["word_errors"]/result["reference_words"],
                  exact_match=result["exact_count"]/len(eligible))
    return result


def build_report(manifest, config, config_root):
    validate_manifest(manifest)
    inventory = {r["review_id"]: r for r in manifest["rows"]}
    models = config.get("models", [])
    if set(m["id"] for m in models) != set(MODELS) or len(models) != 3:
        raise ValueError("Config requires exactly easyocr, trocr and paddleocr model entries")
    result = {"schema_version": 3, "protocol": PROTOCOL, "normalised_protocol": NORMALISED_PROTOCOL,
              "manifest_sha256": manifest["manifest_sha256"], "config_sha256": fingerprint(config),
              "crop_pixels_accessed": False, "models": [],
              "limitations": manifest["limitations"] + ["Crop-conditional accuracy, not end-to-end detection accuracy.",
                  "Latency covers successful saved crops only; hardware/warmup boundaries are run-specific.",
                  "Blank/absent and partial/illegible populations are counted but have no primary text score."]}
    for model in models:
        output = {"id": model["id"], "name": MODELS[model["id"]], "variants": {}}
        for variant in ("baseline", "finetuned"):
            spec = model.get(variant)
            predictions, identity = {}, None
            availability = "Not run"
            scopes = set()
            if spec:
                if spec.get("status") == "Unavailable":
                    availability = "Unavailable"
                    if spec.get("run_dir") or spec.get("runs"):
                        raise ValueError("Unavailable variant cannot also specify run_dir")
                elif spec.get("run_dir") or spec.get("runs"):
                    if spec.get("run_dir") and spec.get("runs"):
                        raise ValueError("Choose run_dir or runs, not both")
                    runs = spec.get("runs") or [spec]
                    identities = []
                    for run in runs:
                        if (not run.get("run_dir") or not run.get("splits") or not run.get("input_sets")
                                or not set(run["splits"]) <= {"train", "valid", "test"}
                                or not set(run["input_sets"]) <= {"annotation", "prediction"}):
                            raise ValueError("Run requires explicit run_dir, splits and input_sets")
                        run_scopes = {(s, p) for s in run["splits"] for p in run["input_sets"]}
                        if scopes & run_scopes:
                            raise ValueError("Multiple runs have overlapping split/population scopes")
                        current, current_identity = load_run(Path(config_root) / run["run_dir"], inventory)
                        if current_identity.get("engine", "").lower() != model["id"]:
                            raise ValueError("Run engine does not match configured model")
                        if any((inventory[rid]["split"], inventory[rid]["crop_source"]) not in run_scopes for rid in current):
                            raise ValueError("Predictions outside declared run scope")
                        if set(predictions) & set(current):
                            raise ValueError("Duplicate prediction IDs across runs")
                        current_identity["declared_scope"] = {k: run[k] for k in ("splits", "input_sets")}
                        identities.append(current_identity)
                        scopes.update(run_scopes)
                        predictions.update(current)
                    identity = identities[0] if len(identities) == 1 else {"runs": identities}
                    availability = "Available"
                else:
                    raise ValueError("Variant requires run_dir or status=Unavailable")
            cells = []
            for split in ("train", "valid", "test"):
                for population in ("annotation", "prediction"):
                    for field in (*FIELDS, "all"):
                        rows = [r for r in inventory.values() if
                                (r["split"], r["crop_source"]) == (split, population)
                                and (r["label"] == field or (field == "all" and r["label"] != "front_eds"))]
                        # A validation-only run does not imply train/test were run.
                        population_run = availability == "Available" and (split, population) in scopes
                        cell = score_cell(rows, predictions, availability == "Available" and population_run)
                        if availability == "Unavailable" and field != "front_eds":
                            cell["status"] = "Unavailable"
                        if field == "front_eds":
                            cell["status"] = "Not applicable"
                        cells.append({"split": split, "input_set": population, "field": field, **cell})
            records = [text_record(row, predictions.get(rid)) for rid, row in inventory.items()
                       if availability == "Available" and (row["split"], row["crop_source"]) in scopes]
            output["variants"][variant] = {"availability": availability, "identity": identity,
                                           "cells": cells,
                                           "text_records": records}
        result["models"].append(output)
    return result


def render_markdown(report):
    fields = {"front_eds_num": "number", "front_eds_destination": "destination",
              "front_eds_route": "route", "all": "all"}
    parts = ["# OCR results", "", "Scoring: normalised (casefold, whitespace collapsed).",
             "Failed/missing predictions count as empty strings.", ""]
    for population, title in (("annotation", "Table 1: annotation crops"),
                              ("prediction", "Table 2: detector crops")):
        parts += ["## " + title, "",
                  "| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |",
                  "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |"]
        for model in report["models"]:
            for variant, data in model["variants"].items():
                for cell in data["cells"]:
                    if (cell["input_set"] != population or cell["field"] not in fields
                            or (population == "prediction" and cell["split"] == "train")):
                        continue
                    values = [f"{100*cell[k]:.1f}" if cell[k] is not None else cell["status"]
                              for k in ("cer", "wer", "exact_match")]
                    version = "pretrained" if variant == "baseline" else "finetuned"
                    parts.append("| " + " | ".join([model["name"], version, cell["split"],
                                 fields[cell["field"]], str(cell["eligible"]), *values]) + " |")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_report(report, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".crop-score-", dir=output.parent) as tmp:
        staging = Path(tmp) / "report"
        staging.mkdir()
        (staging / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding="utf-8")
        (staging / "OCR_RESULTS.md").write_text(render_markdown(report), encoding="utf-8")
        columns = ["model", "variant", "scoring_mode", "split", "input_set", "field", "inventory", "eligible",
                   "cer", "wer", "exact_match", "status", "attempted", "completed", "failed", "missing",
                   "empty", "successful_crop_total_ms_median", "successful_crop_total_ms_p95"]
        with (staging / "summary.csv").open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for model in report["models"]:
                for variant, data in model["variants"].items():
                    for mode, key in (("normalised", "cells"),):
                        for cell in data[key]:
                            writer.writerow({"model": model["id"], "variant": variant, "scoring_mode": mode,
                                             **{k: cell[k] for k in columns[3:]}})
        text_columns = ["model", "variant", *TEXT_RECORD_COLUMNS]
        with (staging / "text_records.csv").open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=text_columns, lineterminator="\n")
            writer.writeheader()
            for model in report["models"]:
                for variant, data in model["variants"].items():
                    writer.writerows({"model": model["id"], "variant": variant, **record}
                                     for record in data["text_records"])
        if output.exists():
            raise FileExistsError(f"Refusing existing output: {output}")
        staging.rename(output)
