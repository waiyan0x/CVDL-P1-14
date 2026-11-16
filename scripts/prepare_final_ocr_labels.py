"""Select consistent AI training labels and prepare a blank human spot-check."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"front_eds_num": "bus_number", "front_eds_destination": "destination",
          "front_eds_route": "route_text"}


def select(rows, quarantine_cleared=False):
    groups = defaultdict(list)
    for row in rows:
        if (row["legibility"] == "full" and row["transcription"].strip()
                and "[unk]" not in row["transcription"].casefold()
                and row.get("user_scope_policy") != "challenge_only"):
            groups[row["source_name"], row["label"]].append(row)
    selected, quarantined = [], []
    for group in groups.values():
        if (len(group) != 3 or len({r["image"] for r in group}) != 3
                or len({r["transcription"] for r in group}) != 1):
            continue
        held = any(r.get("training_disposition") == "quarantined_legacy_holdout_candidate"
                   for r in group)
        if held and not quarantine_cleared:
            quarantined.extend(group)
        else:
            selected.extend(group)
    return sorted(selected, key=lambda r: r["review_id"]), quarantined


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepare(source, output, review_dir, seed):
    with source.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    selected, held = select(rows)
    if len(selected) < 50:
        raise ValueError("Fewer than 50 selected training crops")
    output.parent.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    final = []
    for row in selected:
        crop = ROOT / ".cache/ocr_training/v4-reviewed-01-ai-01/source" / row["crop"]
        if hashlib.sha256(crop.read_bytes()).hexdigest() != row["crop_sha256"]:
            raise ValueError(f"Crop hash mismatch: {row['review_id']}")
        final.append(dict(crop=crop.relative_to(ROOT).as_posix(), field=FIELDS[row["label"]],
                          text=row["transcription"], source_name=row["source_name"]))
    write_csv(output, ["crop", "field", "text", "source_name"], final)
    sample = random.Random(seed).sample(list(zip(selected, final)), 50)
    decisions = []
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 19)
    except OSError:
        font = ImageFont.load_default(size=19)
    for start in range(0, 50, 10):
        sheet = Image.new("RGB", (1200, 1600), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for offset, (source_row, row) in enumerate(sample[start:start + 10]):
            index = start + offset + 1
            review_id = f"S{index:03d}"
            x, y = (offset % 2) * 600, (offset // 2) * 320
            draw.text((x + 15, y + 10), f"{review_id} — {row['field']}", fill="black", font=font)
            with Image.open(ROOT / row["crop"]) as original:
                image = original.convert("RGB")
                scale = min(560 / image.width, 210 / image.height)
                image = image.resize((max(1, round(image.width * scale)),
                                      max(1, round(image.height * scale))), Image.Resampling.NEAREST)
                sheet.paste(image, (x + 15, y + 50))
            # Keep the answer off the contact sheet: human reads pixels first.
            draw.text((x + 15, y + 285), "Enter visible text in spotcheck.csv", fill="black", font=font)
            decisions.append(dict(review_id=review_id, training_review_id=source_row["review_id"],
                                  crop=row["crop"], crop_sha256=source_row["crop_sha256"],
                                  human_text="", human_legibility="", reviewer="", reviewed_at=""))
        sheet.save(review_dir / f"sheet_{start // 10 + 1:02d}.png")
    write_csv(review_dir / "spotcheck.csv", list(decisions[0]), decisions)
    audit = dict(source=source.relative_to(ROOT).as_posix(),
                 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 filter_order="full/no UNK/nonchallenge; group source_name,label; exactly 3 distinct images with identical literal text",
                 selected_crops=len(final), selected_groups=len(final) // 3,
                 field_counts=dict(Counter(r["field"] for r in final)),
                 consistent_quarantined_crops_held=len(held),
                 quarantine_confirmation="pending Brendan", label_source="Codex AI",
                 spotcheck_seed=seed, spotcheck_n=50,
                 human_spotcheck_status="pending", human_spotcheck_correct_pct=None)
    output.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "evaluation/ocr_review/human-verification-20261113/training.source.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/ocr_training/train_labels_final.csv")
    parser.add_argument("--review-dir", type=Path, default=ROOT / "evaluation/ocr_review/train-spotcheck")
    parser.add_argument("--seed", type=int, default=20261116)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source.resolve(), args.output, args.review_dir, args.seed), indent=2))
