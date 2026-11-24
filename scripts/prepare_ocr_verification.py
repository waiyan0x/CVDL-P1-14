"""Prepare blank human decisions and crop-only review pages from AI proposals."""

import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.review_decisions import create_template, write_rows


def prepare(training, validation, output):
    if output.exists():
        raise FileExistsError(output)
    sources = [("training", [training]), ("validation", validation)]
    loaded = []
    for name, paths in sources:
        rows = []
        for path in paths:
            with path.open(newline="") as handle:
                rows.extend(csv.DictReader(handle))
        allowed = {"train"} if name == "training" else {"valid"}
        if not rows or any(r.get("split") not in allowed for r in rows):
            raise ValueError("Only train/valid crops in the matching review population are permitted")
        if len({r["review_id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate review IDs")
        loaded.append((name, paths, rows))
    output.mkdir(parents=True)
    checksums, counts, challenge = {}, {}, []
    for name, paths, rows in loaded:
        cards = []
        for row in rows:
            disposition = row.get("followup_disposition", "")
            is_challenge = row.get("ai_disposition") == "mixed_fields_confirmed" or (
                bool(disposition) and disposition not in {
                    "field_presence_unresolved_full_photo_required", "road_text_field_definition_pending"})
            row["user_scope_policy"] = "challenge_only" if is_challenge else "review_required"
            if is_challenge:
                reason = "User decision 2026-11-13: mixed-field/operational-message challenge; exclude primary scoring/training pending field ownership."
                row["exclusion_reason"] = "; ".join(filter(None, [row.get("exclusion_reason"), reason]))
                challenge.append(dict(population=name, review_id=row["review_id"],
                                      disposition=disposition or row.get("ai_disposition"), reason=reason))
            row["training_ready"] = "false"
            row["scoring_ready"] = "false"
            crop = Path(row["crop_local_path"]) if name == "training" else (
                Path("evaluation/ocr_annotations/v4-reviewed-01/source") / row["crop"])
            if not crop.is_file():
                raise FileNotFoundError(crop)
            crop_hash = hashlib.sha256(crop.read_bytes()).hexdigest()
            if crop_hash != row["crop_sha256"]:
                raise ValueError(f"Crop hash mismatch: {row['review_id']}")
            href = html.escape(Path(os.path.relpath(crop.resolve(), output.resolve())).as_posix(), quote=True)
            cards.append(f'<article id="{row["review_id"]}"><h2>{row["review_id"]}</h2>'
                         f'<p>Supplied field: {html.escape(row["label"])}; '
                         f'{row["user_scope_policy"]}</p><a href="{href}">'
                         f'<img loading="lazy" src="{href}" alt="Crop {row["review_id"]}"></a></article>')
        columns = list(dict.fromkeys(key for row in rows for key in row))
        snapshot = output / f"{name}.source.csv"
        write_rows(snapshot, columns, rows)
        create_template(snapshot, output / f"{name}.decisions.template.csv")
        (output / f"{name}.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>Human crop verification</title>'
            '<style>body{font:16px sans-serif;margin:30px}article{border-top:1px solid #aaa;'
            'padding:20px 0}img{image-rendering:pixelated;min-width:240px;max-width:95vw}</style>'
            '<h1>Human crop verification</h1><p>Read each crop independently. '
            'AI text and model predictions are hidden. Click a crop for native viewing. '
            'Enter your decision in the CSV; this page does not save edits.</p>' + ''.join(cards))
        counts[name] = len(rows)
        checksums.update({str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
    write_rows(output / "challenge_register.csv", ["population", "review_id", "disposition", "reason"], challenge)
    report = dict(source_sha256=checksums, rows=counts, challenge_rows=len(challenge),
                  challenge_counts={name: sum(r["population"] == name for r in challenge) for name, _, _ in loaded},
                  human_decisions_supplied=0, scoring_ready_rows=0, training_ready_rows=0,
                  test_images_accessed=0, crop_hashes_verified=sum(counts.values()),
                  original_sources_modified=False)
    (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--validation", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.training, args.validation, args.output), indent=2))


if __name__ == "__main__":
    main()
