"""Assemble audited pre-training baseline tables and actionable review templates."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.crop_scoring import build_report, freeze_manifest, write_report
from backend.app.evaluation.review_decisions import create_template, digest


def write_csv(path, rows, columns):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def timestamp(name):
    # Conservative filename-only candidates. Capture timezone is not inferred.
    match = re.search(r"(?<!\d)(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)[T _-]?([0-2]\d)[.:_-]?([0-5]\d)[.:_-]?([0-5]\d)(?!\d)", name)
    if not match:
        return ""
    try:
        return datetime(*(int(x) for x in match.groups())).isoformat()
    except ValueError:
        return ""


def baseline_html(report, audit):
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Pre-training OCR baselines</title>',
             '<style>body{font:15px system-ui;margin:32px;max-width:1400px}table{border-collapse:collapse;width:100%;margin-bottom:28px}th,td{border:1px solid #bbb;padding:8px;text-align:left}pre{white-space:pre-wrap}</style>',
             '<h1>Pre-training OCR baseline deliverable</h1>',
             '<p>Validation crops only. Primary raw and secondary normalised text before reference matching. Normalisation applies NFC, Unicode casefold and collapsed whitespace equally to references and predictions; punctuation and abbreviations are preserved. Accuracy is pending until human eligibility review is complete. No fine-tuning has been performed.</p>',
             '<p>Recognition timing covers successful saved crops only; crop totals include preprocessing. Initialization and warmup are excluded. CPU and MPS latency must not be ranked as equivalent hardware.</p>']
    for model in report["models"]:
        data = model["variants"]["baseline"]
        identity = data["identity"] or {}
        parts.append('<h2>'+escape(model["name"])+ '</h2><p>Checkpoint: '+escape(str(identity.get("model", "Not run")))+
                     '; device: '+escape(str(identity.get("actual_device", "Not recorded")))+'</p>')
        parts.append('<table><tr>'+''.join('<th>'+s+'</th>' for s in ["Input crops", "Field", "Inventory", "Eligible", "Raw CER %", "Raw WER %", "Raw exact %", "Normalised CER %", "Normalised WER %", "Normalised exact %", "Completed / attempted", "Failed", "Empty", "Crop total median / p95 ms", "Status"])+ '</tr>')
        for cell, normalised in zip(data["cells"], data["normalised_cells"]):
            if cell["split"] != "valid" or cell["field"] == "front_eds":
                continue
            def number(value):
                return '—' if value is None else f'{value:.2f}'
            values = [cell["input_set"], cell["field"], cell["inventory"], cell["eligible"],
                      *[number(None if cell[k] is None else 100*cell[k]) for k in ("cer", "wer", "exact_match")],
                      *[number(None if normalised[k] is None else 100*normalised[k]) for k in ("cer", "wer", "exact_match")],
                      f'{cell["completed"]} / {cell["attempted"]}', cell["failed"], cell["empty"],
                      number(cell["successful_crop_total_ms_median"])+ ' / '+number(cell["successful_crop_total_ms_p95"]), cell["status"]]
            parts.append('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in values)+'</tr>')
        parts.append('</table>')
    parts.append('<h2>Audit and outstanding decisions</h2><pre>'+escape(json.dumps(audit, indent=2))+'</pre></html>')
    return '\n'.join(parts)


def prepare(reviews, config_path, layout_path, source_root, output):
    from PIL import Image
    if output.exists():
        raise FileExistsError(f"Refusing existing output: {output}")
    manifest = freeze_manifest(reviews)
    if any(row["split"] != "valid" for row in manifest["rows"]):
        raise ValueError("Pre-training deliverable accepts validation only; reserved test is not accessed")
    config = json.loads(config_path.read_text())
    report = build_report(manifest, config, config_path.resolve().parent)
    layout_hash = digest(layout_path)
    layout_manifest = json.loads(layout_path.read_text())
    adjacent_hash = layout_path.with_suffix(".sha256")
    if adjacent_hash.read_text().split()[0] != layout_hash:
        raise ValueError("Layout checksum mismatch")
    layout_rows = layout_manifest["entries"]
    layout = {row["review_id"]: row for row in layout_rows}
    if len(layout) != len(layout_rows) or set(layout) != {r["review_id"] for r in manifest["rows"]}:
        raise ValueError("Layout/review ID population mismatch")
    inventory = []
    for row in manifest["rows"]:
        path = (source_root/row["crop"]).resolve()
        if not path.is_relative_to(source_root.resolve()) or digest(path) != row["crop_sha256"]:
            raise ValueError(f'Crop path/hash mismatch: {row["review_id"]}')
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
        entry = layout[row["review_id"]]
        if (entry["crop_sha256"] != row["crop_sha256"] or entry["crop_id"] != row["crop"]
                or (entry["input_width"], entry["input_height"]) != (width, height)
                or entry["field"] != row["label"]):
            raise ValueError("Layout crop identity/size mismatch")
        inventory.append({"review_id": row["review_id"], "crop": row["crop"], "image": row["image"],
            "field": row["label"], "input_set": row["crop_source"], "view": row.get("view", "") or "unknown",
            "lighting": row.get("lighting", "") or "unknown", "width": width, "height": height,
            "aspect_ratio": width/height, "filename_timestamp": timestamp(row["image"]),
            "layout_status": entry["review_status"], "line_count": entry["line_count"],
            "source_sha256": row["source_image_sha256"], "crop_sha256": row["crop_sha256"],
            "proposed_source_group": 'source-'+row["source_image_sha256"][:16],
            "group_review_status": row.get("group_review_status", ""), "legibility": row.get("legibility", ""),
            "issue_codes": row.get("issue_codes", ""), "scoring_blockers": ';'.join(row["scoring_blockers"])})
    compatibility = []
    for model in config["models"]:
        spec = model.get("baseline")
        if not spec or not spec.get("run_dir"):
            continue
        run_dir = (config_path.resolve().parent/spec["run_dir"]).resolve()
        saved = json.loads((run_dir/"report.json").read_text())
        if (saved.get("frozen_line_layout", {}).get("sha256") != layout_hash
                or saved.get("cached_weights_unchanged") is not True
                or saved.get("source_workspace_unchanged") is not True):
            raise ValueError("Saved run layout/model/source integrity mismatch")
        predictions = [json.loads(line) for line in (run_dir/"predictions.jsonl").read_text().splitlines() if line.strip()]
        if {p["review_id"] for p in predictions} != set(layout):
            raise ValueError("Baseline run does not cover the full validation inventory")
        for prediction in predictions:
            entry = layout[prediction["review_id"]]
            if prediction.get("line_quads") != entry["line_quads"]:
                raise ValueError("Saved prediction geometry differs from common layout")
        compatibility.append({"model": model["id"], "run": run_dir.name, "ids": len(predictions),
            "layout_sha256": layout_hash, "geometry_matches": True,
            "prediction_sha256": digest(run_dir/"predictions.jsonl"), "report_sha256": digest(run_dir/"report.json")})
    def distribution(values):
        from backend.app.evaluation.metrics import percentile
        return {"min": min(values), "p25": percentile(values,.25), "median": percentile(values,.5),
                "p75": percentile(values,.75), "p95": percentile(values,.95), "max": max(values)}
    dimensions = []
    for population in ("annotation", "prediction"):
        for field in ("front_eds_num", "front_eds_destination", "front_eds_route"):
            rows = [r for r in inventory if r["input_set"] == population and r["field"] == field]
            dimensions.append({"input_set":population,"field":field,"count":len(rows),
                **{k:distribution([r[k] for r in rows]) if rows else None for k in ("width","height","aspect_ratio")}})
    source_groups = defaultdict(list)
    for row in inventory:
        source_groups[row["source_sha256"]].append(row)
    groups = [{"proposed_group_id":rows[0]["proposed_source_group"], "source_sha256":sha,
               "source_images":json.dumps(sorted({r["image"] for r in rows})),
               "review_ids":';'.join(r["review_id"] for r in rows),
               "filename_timestamps":';'.join(sorted({r["filename_timestamp"] for r in rows if r["filename_timestamp"]})),
               "human_group_id":"", "human_group_review_status":"", "human_reviewer":"", "human_reviewed_at":"", "notes":""}
              for sha, rows in sorted(source_groups.items())]
    # Temporal proximity proposes related sources; it never confirms the same bus.
    timed = sorted(((datetime.fromisoformat(g["filename_timestamps"]),g) for g in groups
                   if g["filename_timestamps"] and ';' not in g["filename_timestamps"]),
                   key=lambda pair:(pair[0],pair[1]["proposed_group_id"]))
    bursts = []
    for (first_time, first), (second_time, second) in zip(timed,timed[1:]):
        gap = (second_time-first_time).total_seconds()
        if gap <= 5:
            bursts.append({"source_group_1":first["proposed_group_id"], "source_group_2":second["proposed_group_id"],
                           "source_images_1":first["source_images"], "source_images_2":second["source_images"],
                           "gap_seconds":gap, "same_bus_human_decision":"", "reviewer":"", "reviewed_at":""})
    source_metadata = {}
    source_manifest = source_root/"manifest.json"
    if source_manifest.is_file():
        supplied = json.loads(source_manifest.read_text())
        if supplied.get("split") != "valid":
            raise ValueError("Source handoff manifest must identify validation")
        images = supplied["images"]
        source_metadata = {"manifest_sha256":digest(source_manifest), "split":supplied["split"],
                           "source_images":len(images),
                           "images_without_annotation_boxes":sum(not im["ground_truth"] for im in images),
                           "images_without_predicted_boxes":sum(not im["predictions"] for im in images),
                           "origin_note":"Supplied v4 validation handoff; not evidence of the earlier 142-image held-out set or Roboflow v2 origin."}
    audit = {"classification":"observed implementation and metadata audit; human decisions remain pending",
             "validation_crops":len(inventory), "distinct_source_hashes_with_crops":len(source_groups),
             "eligible":sum(r["scoring_eligible"] for r in manifest["rows"]),
             "manifest_sha256":manifest["manifest_sha256"], "layout_sha256":layout_hash,
             "layout_human_review":layout_manifest.get("independent_human_review"),
             "layout_status_counts":dict(Counter(r["layout_status"] for r in inventory)),
             "view_counts":dict(Counter(r["view"] for r in inventory)),
             "lighting_counts":dict(Counter(r["lighting"] for r in inventory)),
             "filename_timestamp_crops":sum(bool(r["filename_timestamp"]) for r in inventory),
             "timestamp_pair_candidates_within_5_seconds":len(bursts),
             "timestamp_timezone":"Not stated in filenames; do not infer camera timezone from chat settings",
             "source_handoff":source_metadata,
             "duplicate_crop_hash_families":sum(n>1 for n in Counter(r["crop_sha256"] for r in inventory).values()),
             "augmentation_original_selection":"Not established by crop filenames; original/variant lineage needs source review. No crop removed automatically.",
             "quality_issue_codes":"Existing review proposals, not newly verified visual diagnoses; see inventory.csv",
             "compatibility":compatibility, "size_distributions":dimensions,
             "blockers_overlapping":dict(Counter(b for r in manifest["rows"] for b in r["scoring_blockers"])),
             "unresolved_requirements":["Human text and field adjudication; do not promote AI proposals.",
                 "Human source/augmentation/burst grouping; proposed source hashes do not prove bus identity.",
                 "Predicted-crop correspondence; do not copy annotation text automatically.",
                 "Human line-layout confirmation and mixed-field/operational-message policy.",
                 "View/lighting/source-origin evidence where unknown.",
                 "GPU-equivalent timing comparison requires the same device; CPU is a separate diagnostic."],
             "reserved_test_accessed":False, "training_performed":False}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".baseline-prep-",dir=output.parent) as tmp:
        staging = Path(tmp)/"deliverable"
        write_report(report,staging)
        (staging/"baseline_tables.html").write_text(baseline_html(report,audit),encoding="utf-8")
        for name, data in [("manifest.json",manifest),("audit.json",audit),("comparison.json",config)]:
            (staging/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding="utf-8")
        write_csv(staging/"inventory.csv",inventory,list(inventory[0]))
        write_csv(staging/"source_group_review.csv",groups,list(groups[0]))
        write_csv(staging/"burst_pair_review.csv",bursts,["source_group_1","source_group_2","source_images_1",
                  "source_images_2","gap_seconds","same_bus_human_decision","reviewer","reviewed_at"])
        for index, review in enumerate(reviews,1):
            create_template(review,staging/f"human_decisions_{index}.csv")
        (staging/"README.txt").write_text('Open baseline_tables.html for the three pre-training tables.\nRead audit.json for exact evidence and blockers.\nHuman decision templates are blank; do not mark AI proposals human-reviewed automatically.\nsource_group_review.csv is a proposal worksheet, not an accepted import format.\nDataset origin/view/lighting and relationships require source evidence.\nAll accuracy remains pending unless reviewed rows pass the gate.\n')
        if digest(layout_path) != layout_hash:
            raise ValueError("Layout changed during preparation")
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review",type=Path,action="append",required=True)
    parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--line-layout",type=Path,required=True)
    parser.add_argument("--source-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    audit = prepare(args.review,args.config,args.line_layout,args.source_root,args.output)
    print(json.dumps({"output":str(args.output),"crops":audit["validation_crops"],"eligible":audit["eligible"]}))


if __name__ == "__main__":
    main()
