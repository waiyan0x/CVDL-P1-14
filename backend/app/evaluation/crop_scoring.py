"""Frozen, review-gated raw crop scoring. No image decoding or model loading."""

from collections import Counter
import csv
import hashlib
from html import escape
import json
import math
from pathlib import Path
import tempfile
import unicodedata

from .metrics import edit_distance, percentile
from .review_decisions import blockers, digest, load_source


FIELDS = ("front_eds_num", "front_eds_destination", "front_eds_route", "front_eds")
MODELS = {"easyocr": "EasyOCR", "trocr": "Public TrOCR", "paddleocr": "PaddleOCR"}
PROTOCOL = {
    "id": "eds-crop-raw-v1", "unicode": "NFC",
    "whitespace": "one ASCII word space; trim per-line padding; preserve nonempty line breaks",
    "case_and_punctuation": "preserved", "wer": "Unicode whitespace tokens",
    "aggregation": "micro edit counts/reference counts; exact per eligible crop",
    "failures": "empty hypothesis on eligible rows; unavailable runs unscored",
    "partial_illegible": "excluded from primary metrics", "reference_matching": False,
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def canonical_text(text):
    """Declared spacing only; never fix case, punctuation or abbreviations."""
    lines = [" ".join(line.split()) for line in unicodedata.normalize("NFC", text).splitlines()]
    return "\n".join(line for line in lines if line)


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
               "limitations": ["Human attestations recorded, not independently authenticated.",
                               "Declared hashes checked for correspondence; image bytes are not opened.",
                               "Exact overlap checks do not establish absence of near-duplicate leakage."]}
    return {**payload, "manifest_sha256": fingerprint(payload)}


def set_eligibility(rows):
    # Known split overlap blocks affected rows, including otherwise pending rows.
    memberships = {}
    for row in rows:
        for key in ("group_id", "crop_sha256", "source_image_sha256"):
            if row.get(key):
                memberships.setdefault((key, row[key]), set()).add(row["split"])
    for row in rows:
        reasons = blockers(row)
        if row.get("field_review_status") != "reviewed":
            reasons.append("field_review_pending")
        for key in ("group_id", "crop_sha256", "source_image_sha256"):
            if len(memberships.get((key, row.get(key)), ())) > 1:
                reasons.append(f"cross_split_{key}")
        row["scoring_eligible"] = not reasons
        row["scoring_blockers"] = sorted(set(reasons))


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
    eligible = [r for r in rows if r["scoring_eligible"]]
    reasons = Counter(reason for row in rows for reason in row["scoring_blockers"])
    coverage = {"inventory": len(rows), "eligible": len(eligible), "excluded": len(rows)-len(eligible),
                "blocker_counts_overlapping": dict(reasons),
                "legibility_counts": dict(Counter(r.get("legibility", "") for r in rows)),
                "field_status_counts": dict(Counter(r.get("field_status", "") for r in rows))}
    panel = bool(rows) and rows[0]["label"] == "front_eds"
    status = ("Not applicable" if panel else "Not run" if not available else
              "No samples" if not rows else "Review pending" if not eligible else "Scored")
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
        reference = row["transcription"]
        hypothesis = canonical_text(pred["raw_text"]) if state == "success" else ""
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
    result = {"schema_version": 1, "protocol": PROTOCOL,
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
            if spec:
                if spec.get("status") == "Unavailable":
                    availability = "Unavailable"
                    if spec.get("run_dir"):
                        raise ValueError("Unavailable variant cannot also specify run_dir")
                elif spec.get("run_dir"):
                    predictions, identity = load_run(Path(config_root) / spec["run_dir"], inventory)
                    if identity.get("engine", "").lower() != model["id"]:
                        raise ValueError("Run engine does not match configured model")
                    if (not spec.get("splits") or not spec.get("input_sets")
                            or not set(spec["splits"]) <= {"train", "valid", "test"}
                            or not set(spec["input_sets"]) <= {"annotation", "prediction"}):
                        raise ValueError("Run requires explicit splits and input_sets")
                    if any(inventory[rid]["split"] not in spec["splits"]
                           or inventory[rid]["crop_source"] not in spec["input_sets"] for rid in predictions):
                        raise ValueError("Predictions outside declared run scope")
                    identity["declared_scope"] = {k: spec[k] for k in ("splits", "input_sets")}
                    availability = "Available"
                else:
                    raise ValueError("Variant requires run_dir or status=Unavailable")
            cells = []
            for split in ("train", "valid", "test"):
                for population in ("annotation", "prediction"):
                    for field in FIELDS:
                        rows = [r for r in inventory.values() if
                                (r["split"], r["crop_source"], r["label"]) == (split, population, field)]
                        # A validation-only run does not imply train/test were run.
                        population_run = (availability == "Available" and split in spec["splits"]
                                          and population in spec["input_sets"])
                        cell = score_cell(rows, predictions, availability == "Available" and population_run)
                        if availability == "Unavailable" and field != "front_eds":
                            cell["status"] = "Unavailable"
                        if field == "front_eds":
                            cell["status"] = "Not applicable"
                        cells.append({"split": split, "input_set": population, "field": field, **cell})
            output["variants"][variant] = {"availability": availability, "identity": identity, "cells": cells}
        result["models"].append(output)
    return result


def render_html(report):
    def metric(cell, key):
        return "—" if cell[key] is None else f"{100*cell[key]:.2f}"
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>EDS raw OCR results</title>',
             '<style>body{font:15px system-ui;margin:32px}table{border-collapse:collapse;margin-bottom:32px}th,td{border:1px solid #bbb;padding:7px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>',
             '<h1>EDS raw OCR results</h1><p>Percentages; raw output before reference matching. Annotation and predicted crops have separate denominators.</p>',
             '<p>Manifest: '+escape(report["manifest_sha256"])+ '</p>']
    for model in report["models"]:
        parts.append('<h2>'+escape(model["name"])+ '</h2><details><summary>Model identities and timing evidence</summary><pre>'+
                     escape(json.dumps({v: d["identity"] for v, d in model["variants"].items()}, indent=2))+'</pre></details>')
        parts.append('<table><thead><tr><th rowspan="2">Split</th><th rowspan="2">Input set</th><th rowspan="2">Field</th><th rowspan="2">Inventory</th><th rowspan="2">Eligible</th><th colspan="4">Baseline</th><th colspan="4">Fine-tuned</th></tr><tr>'+ '<th>CER %</th><th>WER %</th><th>Exact %</th><th>Status</th>'*2+'</tr></thead><tbody>')
        for a, b in zip(model["variants"]["baseline"]["cells"], model["variants"]["finetuned"]["cells"]):
            values = [a["split"], a["input_set"], a["field"], a["inventory"], a["eligible"]]
            for c in (a, b):
                values += [metric(c, k) for k in ("cer", "wer", "exact_match")] + [c["status"]]
            parts.append('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in values)+'</tr>')
        parts.append('</tbody></table>')
        stats = {v: [{k: value for k, value in c.items() if k != "outcomes"}
                     for c in d["cells"]] for v, d in model["variants"].items()}
        parts.append('<details><summary>Coverage, failures, edit counts and latency</summary><pre>'+
                     escape(json.dumps(stats, indent=2))+'</pre></details>')
    parts.append('<h2>Limits</h2><ul>'+''.join('<li>'+escape(s)+'</li>' for s in report["limitations"])+ '</ul></html>')
    return '\n'.join(parts)


def write_report(report, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".crop-score-", dir=output.parent) as tmp:
        staging = Path(tmp) / "report"
        staging.mkdir()
        (staging / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding="utf-8")
        (staging / "tables.html").write_text(render_html(report), encoding="utf-8")
        columns = ["model", "variant", "split", "input_set", "field", "inventory", "eligible",
                   "cer", "wer", "exact_match", "status", "attempted", "completed", "failed", "missing",
                   "empty", "successful_crop_total_ms_median", "successful_crop_total_ms_p95"]
        with (staging / "summary.csv").open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for model in report["models"]:
                for variant, data in model["variants"].items():
                    for cell in data["cells"]:
                        writer.writerow({"model": model["id"], "variant": variant,
                                         **{k: cell[k] for k in columns[2:]}})
        if output.exists():
            raise FileExistsError(f"Refusing existing output: {output}")
        staging.rename(output)
