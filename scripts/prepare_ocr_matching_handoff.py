"""Package portable matching inputs and separate evaluation evidence; no matching."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.crop_scoring import NORMALISED_PROTOCOL, fingerprint, load_run, normalise_text, validate_manifest
from backend.app.evaluation.review_decisions import digest


FIELD_NAMES = {"front_eds_num": "bus_number", "front_eds_destination": "destination",
               "front_eds_route": "route_text"}


def prepare(report_dir, config_path, reference, guide, output):
    if output.exists() or output.with_suffix(".zip").exists():
        raise FileExistsError("Handoff directory/archive already exists")
    manifest = json.loads((report_dir / "manifest.json").read_text())
    validate_manifest(manifest)
    inventory = {r["review_id"]: r for r in manifest["rows"]}
    if any(r["split"] != "valid" for r in inventory.values()):
        raise ValueError("Only validation diagnostics are included; test remains reserved")
    report = json.loads((report_dir / "report.json").read_text())
    if report.get("manifest_sha256") != manifest["manifest_sha256"]:
        raise ValueError("Report/manifest mismatch")
    config = json.loads(config_path.read_text())
    if (report.get("config_sha256") != fingerprint(config)
            or report.get("normalised_protocol") != NORMALISED_PROTOCOL):
        raise ValueError("Scoring configuration/normalisation protocol mismatch")
    configs = {m["id"]: m for m in config["models"]}
    inputs = []
    for model in report["models"]:
        for variant, data in model["variants"].items():
            if data["availability"] != "Available":
                continue
            root = (config_path.resolve().parent / configs[model["id"]][variant]["run_dir"]).resolve()
            predictions, identity = load_run(root, inventory)
            if any(identity[k] != data["identity"][k] for k in ("report_sha256", "predictions_sha256")):
                raise ValueError("Saved run changed after scoring")
            for record in data["text_records"]:
                row = inventory[record["review_id"]]
                prediction = predictions.get(record["review_id"])
                raw = prediction["raw_text"] if prediction else None
                status = prediction["status"] if prediction else "missing"
                normalised = normalise_text(raw) if raw is not None else None
                if (record["scoring_eligible"] != row["scoring_eligible"]
                        or raw != record["raw_ocr_text"] or normalised != record["normalised_ocr_text"]
                        or status != record["prediction_status"]):
                    raise ValueError("Exported text differs from saved prediction")
                if row["label"] not in FIELD_NAMES:
                    raise ValueError("Panel crops have no matching field protocol")
                inputs.append(dict(
                    record_id=f'{model["id"]}/{variant}/{row["review_id"]}',
                    model=model["id"], variant=variant, review_id=row["review_id"], split=row["split"],
                    input_set=row["crop_source"], dataset_field=row["label"], field=FIELD_NAMES[row["label"]],
                    source_image_sha256=row["source_image_sha256"], crop_sha256=row["crop_sha256"],
                    display_id=None, prediction_status=status, raw_ocr_text=raw,
                    normalised_ocr_text=normalised, error=prediction.get("error") if prediction else None,
                    ocr_confidence=prediction.get("ocr_confidence") if prediction else None,
                    detector_confidence=float(row["detector_confidence"]) if row.get("detector_confidence") else None,
                    successful_nonempty_input=status == "success" and bool(normalised),
                    scoring_eligible=record["scoring_eligible"],
                    field_review_status=row.get("field_review_status", ""),
                    human_field_confirmation=row.get("human_field_confirmation", ""),
                    scope_policy=row.get("user_scope_policy", "review_required"),
                    exclusion_reason=row.get("exclusion_reason", ""),
                    group_review_status=row.get("group_review_status", ""),
                    correspondence_status=row.get("correspondence_status", "")))
    if not inputs or len({r["record_id"] for r in inputs}) != len(inputs):
        raise ValueError("Empty or duplicate matching inputs")
    with reference.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if reader.fieldnames != ["Route number", "Origin", "Destination"]:
            raise ValueError("Unexpected route-reference schema")
    reference_audit = dict(rows=len(rows), columns=reader.fieldnames,
                           blank_cells={k: sum(not r[k].strip() for r in rows) for k in reader.fieldnames},
                           duplicate_full_rows=len(rows)-len({tuple(r[k] for k in reader.fieldnames) for r in rows}),
                           reference_sha256=digest(reference),
                           semantics="Candidate service/endpoints only; not OCR truth or travel-direction evidence.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".matching-handoff-", dir=output.parent) as temp:
        stage = Path(temp) / "handoff"
        stage.mkdir()
        (stage / "matching_inputs.jsonl").write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in inputs))
        with (stage / "matching_inputs.csv").open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(inputs[0]))
            writer.writeheader()
            writer.writerows(inputs)
        with (stage / "matching_outputs.template.csv").open("x", newline="") as handle:
            columns = ["record_id", "matching_status", "matched_service", "matched_endpoint", "reference_row_numbers",
                       "match_similarity", "match_similarity_method", "matching_policy_id", "reason"]
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(dict(record_id=r["record_id"], matching_status="pending") for r in inputs)
        (stage / "reference").mkdir()
        shutil.copyfile(reference, stage / "reference/bus_information.csv")
        (stage / "reference/audit.json").write_text(json.dumps(reference_audit, indent=2) + '\n')
        (stage / "evaluation").mkdir()
        for name in ("report.json", "manifest.json", "summary.csv", "text_records.csv", "tables.html"):
            shutil.copyfile(report_dir / name, stage / "evaluation" / name)
        shutil.copyfile(guide, stage / "README.md")
        summary = dict(schema_version=1, purpose="diagnostic reference-matching handoff; matching not run",
                       records=len(inputs), unique_crops=len(inventory),
                       statuses=dict(Counter(r["prediction_status"] for r in inputs)),
                       challenge_records=sum(r["scope_policy"] == "challenge_only" for r in inputs),
                       scoring_eligible_records=sum(r["scoring_eligible"] for r in inputs),
                       normalised_protocol=report["normalised_protocol"],
                       report_sha256=digest(report_dir / "report.json"), manifest_sha256=manifest["manifest_sha256"],
                       run_identities={m["id"]: {v: d["identity"] for v, d in m["variants"].items()}
                                       for m in report["models"]},
                       reference_audit=reference_audit, test_images_accessed=False,
                       files_sha256={str(p.relative_to(stage)): digest(p) for p in sorted(stage.rglob('*')) if p.is_file()})
        (stage / "handoff_manifest.json").write_text(json.dumps(summary, indent=2) + '\n')
        stage.rename(output)
    shutil.make_archive(str(output), "zip", root_dir=output.parent, base_dir=output.name)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reference", type=Path, default=Path("data/bus_information.csv"))
    parser.add_argument("--guide", type=Path, default=Path("docs/OCR_MATCHING_HANDOFF.md"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = prepare(args.report_dir, args.config, args.reference, args.guide, args.output)
    print(json.dumps({k: summary[k] for k in ("records", "unique_crops", "statuses", "challenge_records",
                                             "scoring_eligible_records")}, indent=2))
