"""Validate and freeze explicit visual line-review decisions without reading OCR text."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.evaluation.ocr_crop_baseline import load_crops, sha256
from backend.app.evaluation.ocr_line_layout import METHOD, extract_region, line_quads, validate_entry


def freeze(workspace, decisions_path, proposal_run, output, version):
    if output.exists():
        raise FileExistsError(f"Do not overwrite frozen layouts: {output}")
    records = load_crops(workspace)
    decisions = json.loads(decisions_path.read_text())
    if set(decisions["entries"]) != {r["review_id"] for r in records}:
        raise ValueError("Every crop needs an explicit visual review decision")
    if decisions["reviewer_type"] != "AI" or decisions["independent_human_review"]:
        raise ValueError("Preserve actual AI attribution; no human review has been attested")
    proposals_path = proposal_run / "predictions.jsonl"
    # Inspect geometry only; do not read prediction text/confidence into the decision process.
    proposals = {}
    for line in proposals_path.read_text().splitlines():
        row = json.loads(line)
        proposals[row["review_id"]] = row["line_regions"]
    entries = []
    for record in records:
        decision = decisions["entries"][record["review_id"]]
        if decision["status"] not in {"single_line", "split_lines", "unresolved"}:
            raise ValueError(f"Unexpected review decision: {record['review_id']}")
        accepted = decision["status"] != "unresolved"
        separators = decision["separators"]
        if (decision["status"] == "split_lines") != bool(separators):
            raise ValueError("Split decision and separator count disagree")
        quads = line_quads(record["input_width"], record["input_height"], separators) if accepted else []
        entry = {key: record[key] for key in ("review_id", "crop_id", "crop_sha256", "crop_set", "field", "input_width", "input_height")}
        old = proposals[record["review_id"]]
        old_quads = [[[x1,y1],[x2,y1],[x2,y2],[x1,y2]] for x1,y1,x2,y2 in old]
        entry.update(review_status="accepted" if accepted else "unresolved", separators=separators,
                     line_quads=quads, reason=decision["reason"], reviewer=decisions["reviewer"],
                     reviewer_type=decisions["reviewer_type"], reviewed_at=decisions["reviewed_at"],
                     independent_human_review=False, changed_from_proposal=(quads != old_quads),
                     proposal_line_count=len(old), line_count=len(quads))
        validate_entry(entry, record)
        entries.append(entry)
    manifest = {
        "schema_version": 1, "version": version, "method": METHOD, "frozen": True,
        "reviewed_at": decisions["reviewed_at"], "reviewer": decisions["reviewer"], "reviewer_type": "AI",
        "independent_human_review": False, "purpose": "Fixed-upstream-layout crop recognition diagnostic",
        "evidence": decisions["evidence"], "source_decisions_sha256": sha256(decisions_path),
        "proposal_predictions_sha256": sha256(proposals_path), "proposal_run": proposal_run.name,
        "coordinates": "Native crop pixel edges, x in [0,width], y in [0,height]; right/bottom exclusive",
        "transformation": "Horizontal regions: exact slicing. Sloping full-width regions: perspective rectify to original width and maximum side height, INTER_LINEAR/BORDER_REPLICATE",
        "reading_order": "Top to bottom; no reference matching, text rewriting or OCR-based boundary choice",
        "unresolved_policy": "No recognition regions and no automatic/full-crop fallback; retain crop ID and explicit error",
        "summary": {
            "total": len(entries), "accepted": sum(e["review_status"] == "accepted" for e in entries),
            "unresolved": sum(e["review_status"] == "unresolved" for e in entries),
            "multiline_crops": sum(e["line_count"] > 1 for e in entries),
            "line_regions": sum(e["line_count"] for e in entries),
            "changed_from_proposal": sum(e["changed_from_proposal"] for e in entries),
        },
        "limitations": ["AI visual review, not independent human adjudication",
            "Manually fixed upstream layout is additional diagnostic information, not automatic deployment performance",
            "Unresolved layout exclusions and missing lines must remain visible in coverage counts",
            "Transcription quality, group independence and field correspondence remain separate outstanding checks"],
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".layout-freeze-", dir=output.parent) as temporary:
        staging = Path(temporary) / "layout"
        staging.mkdir()
        (staging / "previews").mkdir()
        (staging / "lines").mkdir()
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
        (staging / "manifest.sha256").write_text(sha256(staging / "manifest.json")+"  manifest.json\n")
        (staging / "review_decisions.json").write_bytes(decisions_path.read_bytes())
        unresolved = []
        source_by_id = {r["review_id"]: r for r in records}
        for entry in entries:
            record = source_by_id[entry["review_id"]]
            with Image.open(record["crop_path"]) as image:
                rgb = np.asarray(image.convert("RGB"))
                preview = image.convert("RGB")
            draw = ImageDraw.Draw(preview)
            if entry["review_status"] == "unresolved":
                draw.rectangle((0,0,preview.width-1,preview.height-1), outline=(255,0,0))
                unresolved.append({key: entry[key] for key in ("review_id", "crop_set", "field", "reason")})
            else:
                for index, quad in enumerate(entry["line_quads"], 1):
                    points = [(min(preview.width-1,x),min(preview.height-1,y)) for x,y in quad]
                    draw.line(points+[points[0]], fill=(0,255,0), width=1)
                    patch = extract_region(rgb, quad)
                    Image.fromarray(patch).save(staging / "lines" / f"{entry['review_id']}-L{index:02d}.png")
            preview.save(staging / "previews" / f"{entry['review_id']}.png")
        with (staging / "unresolved.csv").open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["review_id", "crop_set", "field", "reason"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(unresolved)
        stats = manifest["summary"]
        (staging / "README.md").write_text(
            f"# Frozen OCR line layout: {version}\n\n"
            f"Reviewer: **Codex (AI)**; review date **{decisions['reviewed_at']}**. No independent human review is attested.\n\n"
            f"All {stats['total']} crops visually inspected. Accepted layout: {stats['accepted']}; "
            f"unresolved: {stats['unresolved']}; multiline crops: {stats['multiline_crops']}; "
            f"accepted line regions: {stats['line_regions']}; changed from v2 proposals: {stats['changed_from_proposal']}.\n\n"
            "`manifest.json` is the shared geometry contract; verify `manifest.sha256` before use. "
            "`review_decisions.json` records every explicit decision. `previews/` preserves native-size "
            "overlays; `lines/` holds diagnostic extracted regions. `unresolved.csv` lists exclusions and reasons.\n\n"
            "This is manually reviewed layout information for a recognition-only diagnostic. It does not "
            "establish automatic line-detection performance, correct text, dataset independence or accuracy. "
            "Reuse the same manifest/regions across engines and report layout coverage separately. "
            "Unresolved crops must not fall back to automatic segmentation or full-crop recognition.\n\n"
            "Source images, crops, transcriptions, model weights, previous OCR runs and reference matching "
            "are unchanged. No recognition, scoring or training was run during this freeze. "
            "Use a new version/directory for corrections; never overwrite this version.\n",
            encoding="utf-8",
        )
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "evaluation/ocr_annotations/v4-reviewed-01")
    parser.add_argument("--proposal-run", type=Path, default=ROOT / "evaluation/ocr_runs/easyocr-v4-mps-baseline-02")
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="v4-lines-v1")
    args = parser.parse_args()
    manifest = freeze(args.workspace.resolve(), args.decisions.resolve(), args.proposal_run.resolve(), args.output.resolve(), args.version)
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()
