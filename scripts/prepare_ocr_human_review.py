"""Create numbered crop sheets and pending submission templates for human review.

Requires Pillow. Does not perform OCR or supply text/reviewer attestations.
"""

import argparse
import csv
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont


def prepare(workspace, output):
    if output.exists():
        raise FileExistsError(f"Review directory exists; choose a new path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".human-review-", dir=output.parent) as temporary:
        staging = Path(temporary) / "review"
        staging.mkdir()
        font = ImageFont.load_default(size=22)
        total = 0
        for kind, prefix in (("annotation", "A"), ("prediction", "P")):
            with (workspace / f"{kind}_review.csv").open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                columns = reader.fieldnames
                rows = list(reader)
            if any(row["review_status"] != "pending" or row["transcription"] for row in rows):
                raise ValueError("Expected pending input; do not replace completed human work")
            for start in range(0, len(rows), 9):
                batch = start // 9 + 1
                sheet_name = f"{prefix}_batch_{batch:02d}.png"
                sheet = Image.new("RGB", (1800, 960), "#f4f4f4")
                draw = ImageDraw.Draw(sheet)
                for position, row in enumerate(rows[start:start + 9]):
                    review_id = f"{prefix}{start + position + 1:03d}"
                    row["review_id"] = review_id
                    row["review_sheet"] = sheet_name
                    x, y = (position % 3) * 600, (position // 3) * 320
                    field = {"front_eds_num": "service number", "front_eds_route": "route text",
                             "front_eds_destination": "destination"}[row["label"]]
                    draw.text((x + 16, y + 12), f"{review_id} | {field}", fill="black", font=font)
                    crop_path = (workspace / "source" / row["crop"]).resolve()
                    if not crop_path.is_relative_to((workspace / "source").resolve()):
                        raise ValueError(f"Crop escapes source directory: {row['crop']}")
                    with Image.open(crop_path) as crop:
                        crop.load()
                        scale = min(4, 568 / crop.width, 254 / crop.height)
                        if scale >= 1:
                            scale = int(scale)
                        size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
                        display = crop.convert("RGB").resize(size, Image.Resampling.NEAREST)
                    sheet.paste(display, (x + (600 - size[0]) // 2, y + 52 + (254 - size[1]) // 2))
                    draw.rectangle((x + 4, y + 4, x + 595, y + 315), outline="#b5b5b5", width=1)
                sheet.save(staging / sheet_name)
            with (staging / f"{kind}_submission.template.csv").open("x", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["review_id", "review_sheet"] + columns, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            total += len(rows)
        (staging / "README.md").write_text(
            "# Human transcription batches\n\n"
            "All 271 crops are pending. No text labels, reviewer identities or review dates "
            "were supplied by this export.\n\n"
            "A = annotation crops (157); P = prediction crops (114). Each numbered sheet "
            "contains up to nine crops. Only neutral IDs and supplied field names appear "
            "on sheets; filenames and IoU candidates are not transcription prompts.\n\n"
            "Read repository-root `docs/OCR_TRANSCRIPTION_RULES.md` and "
            "`docs/OCR_ANNOTATION_PACKAGE.md` before labelling. Sheets use nearest-neighbour "
            "display scaling only; inspect the native crop or same-image panel context "
            "if a thumbnail is insufficient. Missing context stays unresolved.\n\n"
            "Copy the appropriate submission template to a new reviewer-named CSV. "
            "Keep review_id, crop identity, source metadata and review_sheet unchanged. "
            "Supply visible transcription (actual line breaks in quoted CSV cells), "
            "field_status, legibility, actual reviewer/date and exclusions. Uncertain "
            "cases need independent review; never guess from the route CSV or filenames. "
            "Predicted crops require their own transcription and correspondence review.\n\n"
            "For review in chat, return reviewer name, actual review date and each ID's "
            "visible text, line breaks, field status, legibility and any exclusion. "
            "Use [UNK] for unresolved spans; say blank or absent explicitly. Do not type "
            "a guessed completion. The assistant can record submitted labels as a new "
            "review export; it cannot claim to be a human reviewer. Group and image "
            "review remain separate requirements before scoring.\n",
            encoding="utf-8",
        )
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("evaluation/ocr_annotations/v4-reviewed-01"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.workspace / "human_review"
    print(f"Prepared {prepare(args.workspace, output)} pending crops in {output}")


if __name__ == "__main__":
    main()
