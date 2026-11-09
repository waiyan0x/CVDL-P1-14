"""Prepare a small, blank human transcription batch from AI review candidates."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont


FIELDS = {
    "front_eds_num": "service number",
    "front_eds_destination": "destination",
    "front_eds_route": "route text",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(workspace, output):
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    candidate_path = workspace / "full_text.ai-candidates.csv"
    with candidate_path.open(newline="", encoding="utf-8") as handle:
        candidates = list(csv.DictReader(handle))
    grouped = defaultdict(list)
    for row in candidates:
        if (row["legibility"] != "full" or row["training_ready"] != "false"
                or row["human_verification_status"] != "pending"):
            raise ValueError("Expected provisional, unverified AI candidates")
        grouped[row["label"], row["group_id"]].append(row)
    selected = []
    used_groups = set()
    for field in FIELDS:
        used_texts = set()
        count = 0
        for label, group in sorted(grouped):
            rows = grouped[label, group]
            texts = {r["transcription"] for r in rows}
            if (label != field or group in used_groups or len(rows) != 3
                    or len({r["image"] for r in rows}) != 3 or len(texts) != 1
                    or texts & used_texts):
                continue
            selected.extend(sorted(rows, key=lambda r: r["review_id"]))
            used_groups.add(group)
            used_texts.update(texts)
            count += 1
            if count == 3:
                break
        if count != 3:
            raise ValueError(f"Insufficient complete candidate families for {field}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".verification-", dir=output.parent) as temporary:
        staging = Path(temporary) / "batch"
        staging.mkdir()
        (staging / "native").mkdir()
        font = ImageFont.load_default(size=22)
        submission = []
        manifest_rows = []
        for index, field in enumerate(FIELDS, 1):
            sheet_name = f"sheet_{index:02d}.png"
            sheet = Image.new("RGB", (1800, 960), "#f4f4f4")
            draw = ImageDraw.Draw(sheet)
            for position, row in enumerate(r for r in selected if r["label"] == field):
                neutral_id = row["review_id"]
                original = Path(row["crop_local_path"])
                if digest(original) != row["crop_sha256"]:
                    raise ValueError(f"Changed crop: {neutral_id}")
                native = f"native/{neutral_id}.png"
                (staging / native).write_bytes(original.read_bytes())
                with Image.open(original) as crop:
                    crop.load()
                    scale = min(8, 568 / crop.width, 254 / crop.height)
                    if scale >= 1:
                        scale = int(scale)
                    size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
                    display = crop.convert("RGB").resize(size, Image.Resampling.NEAREST)
                x, y = position % 3 * 600, position // 3 * 320
                draw.text((x + 16, y + 12), f"{neutral_id} | supplied {FIELDS[field]}",
                          fill="black", font=font)
                sheet.paste(display, (x + (600 - size[0]) // 2, y + 52 + (254 - size[1]) // 2))
                draw.rectangle((x + 4, y + 4, x + 595, y + 315), outline="#b5b5b5")
                submission.append({
                    "review_id": neutral_id, "review_sheet": sheet_name,
                    "native_crop": native, "crop_sha256": row["crop_sha256"],
                    "supplied_label": field, "transcription": "", "field_status": "",
                    "label_confirmed": "", "legibility": "", "review_status": "pending",
                    "reviewer": "", "reviewer_type": "", "reviewed_at": "", "notes": "",
                })
                manifest_rows.append({key: row[key] for key in (
                    "review_id", "crop", "crop_sha256", "image", "source_image_sha256",
                    "label", "annotation_id", "group_id", "box_xyxy")})
            sheet.save(staging / sheet_name)
        with (staging / "submission.template.csv").open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(submission[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(submission)
        manifest = {
            "status": "pending_human_review", "source_candidates_sha256": digest(candidate_path),
            "selection": "First three distinct groups/texts per field with three candidate source variants; groups not reused between fields.",
            "limitations": "Deterministic small batch, not a representative accuracy sample. AI labels informed selection but are hidden from sheets/template. Group independence remains unresolved.",
            "counts": {field: 9 for field in FIELDS}, "rows": manifest_rows,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staging / "README.md").write_text(
            "# Human verification batch 01\n\n"
            "27 crops: nine service numbers, nine destinations and nine route-text crops. "
            "Each row is pending. No human labels or identity/date have been supplied.\n\n"
            "Open sheet_01.png through sheet_03.png; native/ contains byte-identical crops "
            "with neutral IDs. Read each variant separately. Sheets and submission.template.csv "
            "hide the AI transcription; the supplied field label must also be checked. "
            "This small deterministic candidate batch is not an accuracy sample.\n\n"
            "Copy submission.template.csv to a reviewer-named CSV. Keep review_id, review_sheet, "
            "native_crop, crop_sha256 and supplied_label unchanged. Enter visible text, actual "
            "newlines, field_status (present/blank/absent/wrong_field), label_confirmed "
            "(yes/no/uncertain), legibility (full/partial/illegible/not_applicable), "
            "review_status (reviewed/needs_resolution), your actual reviewer identity, "
            "reviewer_type=human, actual ISO review date, and any notes.\n\n"
            "Follow repository docs/OCR_TRANSCRIPTION_RULES.md: preserve case, punctuation "
            "and abbreviations; one word space; actual line breaks. Read only this crop. "
            "Do not complete text using another variant, filenames, route knowledge or AI/OCR "
            "suggestions. Use [UNK] for each unresolved span: partial requires readable text "
            "plus [UNK]; illegible is exactly [UNK]. Blank/absent require explicit states and "
            "empty text. Uncertain field presence stays needs_resolution.\n\n"
            "In chat, you may return reviewer name, actual review date, and each neutral ID's "
            "text/state instead of editing the CSV. Independent human verification is not "
            "established merely by preparing this batch. Full-photo grouping remains unresolved "
            "until the missing full dataset is restored; no batch row is training-ready.\n",
            encoding="utf-8",
        )
        staging.rename(output)
    return submission


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("evaluation/ocr_training/v4-reviewed-01-ai-01"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/ocr_training/v4-human-verification-01"))
    args = parser.parse_args()
    rows = prepare(args.workspace, args.output)
    print(f"Prepared {len(rows)} pending human-review crops in {args.output}")
