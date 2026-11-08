"""Audit legacy photo splits and export provisional OCR crops without changing inputs.

The legacy classes contain number/destination boxes but no route-text boxes.
Similarity and source-name links are conservative grouping candidates, not proof
of scene identity. No crop is automatically declared eligible for training.
"""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont


FIELDS = {1: "front_eds_num", 2: "front_eds_destination"}
LEGACY_CLASSES = ["bus_front", "bus_number", "destination", "eds"]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".avif", ".webp", ".bmp"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_key(name):
    return re.sub(r"_(?:jpg|jpeg|png)\.rf\.[^.]+$", "", Path(name).stem, flags=re.I)


def fingerprints(image):
    gray = image.convert("L")
    small = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS), dtype=float)
    differences = small[:, 1:] > small[:, :-1]
    pixels = np.asarray(gray.resize((32, 32), Image.Resampling.LANCZOS), dtype=float)
    axis = np.arange(32)
    basis = np.cos(np.pi * (2 * axis[None, :] + 1) * axis[:, None] / 64)
    low = (basis @ pixels @ basis.T)[:8, :8].flatten()
    perceptual = low > np.median(low[1:])
    pack = lambda bits: sum(int(bit) << i for i, bit in enumerate(bits.flatten()))
    return pack(differences), pack(perceptual)


def parse_boxes(path, size):
    width, height = size
    boxes = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid YOLO row: {path}:{line_number}")
        class_id = int(parts[0])
        cx, cy, bw, bh = map(float, parts[1:])
        if class_id not in range(4) or not all(math.isfinite(v) and 0 <= v <= 1 for v in (cx, cy, bw, bh)) or bw == 0 or bh == 0:
            raise ValueError(f"Invalid YOLO values: {path}:{line_number}")
        raw = [(cx-bw/2)*width, (cy-bh/2)*height, (cx+bw/2)*width, (cy+bh/2)*height]
        box = [max(0, math.floor(raw[0])), max(0, math.floor(raw[1])),
               min(width, math.ceil(raw[2])), min(height, math.ceil(raw[3]))]
        if box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError(f"Empty box: {path}:{line_number}")
        boxes.append((line_number, class_id, box))
    return boxes


def write_csv(path, columns, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepare(repo, output):
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    if (repo / "data/classes.txt").read_text().splitlines() != LEGACY_CLASSES:
        raise ValueError("Legacy class mapping changed; do not reuse a v4 mapping")
    records = {}
    parent = {}
    links = []
    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]
    def link(a, b, kind, **details):
        left, right = find(a), find(b)
        if left != right:
            parent[max(left, right)] = min(left, right)
        links.append({"left": a, "right": b, "kind": kind, **details})

    by_file, by_pixels, by_source = defaultdict(list), defaultdict(list), defaultdict(list)
    for split in ("train", "val", "test"):
        for path in sorted((repo / "data/images" / split).iterdir()):
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            with Image.open(path) as image:
                orientation = image.getexif().get(274, 1)
                rgb = image.convert("RGB")
                size = rgb.size
                pixels = digest(str(size).encode() + rgb.tobytes())
                dh, ph = fingerprints(rgb)
            key = f"legacy:{split}/{path.name}"
            record = {"source_id": key, "path": path.relative_to(repo).as_posix(), "split": split,
                      "sha256": digest(path.read_bytes()), "pixel_sha256": pixels,
                      "width": size[0], "height": size[1], "exif_orientation": orientation,
                      "dhash": f"{dh:016x}", "phash": f"{ph:016x}"}
            records[key] = record
            find(key)
            by_file[record["sha256"]].append(key)
            by_pixels[pixels].append(key)
            by_source[source_key(path.name)].append(key)
    v4_path = repo / "evaluation/ocr_annotations/v4-reviewed-01/source/manifest.json"
    v4 = json.loads(v4_path.read_text())
    for image in v4["images"]:
        key = f"v4:valid/{image['image']}"
        records[key] = {"source_id": key, "path": image["image"], "split": "valid",
                        "sha256": image["image_sha256"], "width": image["width"], "height": image["height"]}
        find(key)
        by_file[image["image_sha256"]].append(key)
        by_source[source_key(image["image"])].append(key)
    for kind, groups in (("exact_file", by_file), ("exact_pixels", by_pixels), ("source_name_candidate", by_source)):
        for members in groups.values():
            for other in members[1:]:
                link(members[0], other, kind)
    local = [r for r in records.values() if "phash" in r]
    for i, a in enumerate(local):
        for b in local[i+1:]:
            if a["pixel_sha256"] == b["pixel_sha256"]:
                continue
            dh = (int(a["dhash"], 16) ^ int(b["dhash"], 16)).bit_count()
            ph = (int(a["phash"], 16) ^ int(b["phash"], 16)).bit_count()
            if dh <= 6 and ph <= 10:
                link(a["source_id"], b["source_id"], "perceptual_candidate", dhash_distance=dh, phash_distance=ph)
    groups = defaultdict(list)
    for key in records:
        groups[find(key)].append(key)
    group_records = []
    for members in sorted(groups.values(), key=lambda m: min(m)):
        group_id = "local88-" + digest("\n".join(sorted(members)).encode())[:12]
        splits = sorted({records[key]["split"] for key in members})
        blocked = any(split != "train" for split in splits)
        group_records.append({"group_id": group_id, "members": sorted(members), "splits": splits,
                              "holdout_link": blocked, "review_status": "pending"})
        seen_pixels = set()
        for key in sorted(members):
            record = records[key]
            record.update(group_id=group_id, group_review_status="pending")
            if record["split"] == "train":
                if blocked:
                    disposition = "excluded_holdout_link"
                elif record["exif_orientation"] != 1:
                    disposition = "needs_orientation_review"
                elif record["pixel_sha256"] in seen_pixels:
                    disposition = "excluded_duplicate"
                else:
                    disposition = "candidate_pending_review"
                seen_pixels.add(record["pixel_sha256"])
                record["training_disposition"] = disposition

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".local88-", dir=output.parent) as temporary:
        staging = Path(temporary) / "package"
        staging.mkdir()
        rows = []
        class_counts = Counter()
        for record in sorted((r for r in records.values() if r["split"] == "train"), key=lambda r: r["path"]):
            source = repo / record["path"]
            labels = repo / "data/labels/train" / (source.stem + ".txt")
            if not labels.is_file():
                raise FileNotFoundError(labels)
            record["label_path"] = labels.relative_to(repo).as_posix()
            record["label_sha256"] = digest(labels.read_bytes())
            with Image.open(source) as opened:
                image = opened.convert("RGB")
                for line_number, class_id, box in parse_boxes(labels, image.size):
                    class_counts[str(class_id)] += 1
                    if class_id not in FIELDS:
                        continue
                    review_id = f"T{len(rows)+1:03d}"
                    field = FIELDS[class_id]
                    crop_path = Path("crops") / field / f"{review_id}.png"
                    target = staging / crop_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.crop(box).save(target)
                    rows.append({
                        "crop_id": crop_path.as_posix(), "source_image": record["path"],
                        "group_id": record["group_id"], "view": "", "field": field,
                        "bbox": json.dumps(box, separators=(",", ":")), "text": "", "legibility": "",
                        "lighting": "", "split": "train", "review_id": review_id,
                        "source_image_sha256": record["sha256"], "crop_sha256": digest(target.read_bytes()),
                        "source_label_sha256": record["label_sha256"], "source_label_line": line_number,
                        "legacy_class_id": class_id, "training_disposition": record["training_disposition"],
                        "group_review_status": "pending", "review_status": "pending", "reviewer": "",
                        "reviewer_type": "", "reviewed_at": "", "exclusion_reason": record["training_disposition"] if record["training_disposition"].startswith("excluded_") else "",
                        "notes": "Legacy destination box may include multiple semantic fields; inspect before labelling",
                    })
        write_csv(staging / "transcriptions.template.csv", list(rows[0]), rows)
        source_rows = [r for r in records.values() if r["split"] == "train"]
        audit = {
            "status": "provisional_not_training_ready", "source_images": len(source_rows),
            "legacy_class_mapping": dict(enumerate(LEGACY_CLASSES)), "legacy_box_counts": dict(class_counts),
            "text_crop_counts": dict(Counter(r["field"] for r in rows)),
            "image_dispositions": dict(Counter(r["training_disposition"] for r in source_rows)),
            "crop_dispositions": dict(Counter(r["training_disposition"] for r in rows)),
            "v4_manifest_sha256": digest(v4_path.read_bytes()), "grouping_links": links,
            "groups": group_records, "sources": list(records.values()), "training_ready_rows": 0,
            "missing_route_annotations": True,
            "limitations": ["No route-text class exists in the legacy boxes; manual geometry is required",
                "Name and perceptual links are conservative candidates; holdout-linked groups are excluded",
                "Missing a link does not prove unrelated scenes; remaining source/group review is pending",
                "No crop is automatically eligible; text and field identity need visible review",
                "V4 test source images are absent; no claim of comparison against the full v4 test set",
                "Existing 271 A/P validation crops are never exported into training"],
        }
        (staging / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        source_columns = ["source_id", "path", "sha256", "pixel_sha256", "width", "height",
                          "group_id", "training_disposition", "group_review_status", "label_path", "label_sha256"]
        write_csv(staging / "source_review.csv", source_columns,
                  [{key: r[key] for key in source_columns} for r in source_rows])
        (staging / "README.md").write_text(
            "# Local 88-photo OCR training preparation\n\n"
            "Status: provisional, **not training-ready**. Sources and existing A/P validation crops are unchanged.\n\n"
            "This export uses the legacy mapping in `data/classes.txt`, not the v4 class order. "
            "Source image paths are relative to the repository root; crop paths are relative to this directory.\n\n"
            f"Exported {len(rows)} tight PNG crops: {audit['text_crop_counts']}. "
            f"Source-photo dispositions: {audit['image_dispositions']}. "
            f"Crop dispositions: {audit['crop_dispositions']}.\n\n"
            "`transcriptions.template.csv` preserves the requested ten columns then appends provenance, "
            "review and training-disposition columns. `source_review.csv` lists all 88 photos. "
            "`audit.json` records hashes, split members, conservative group links and exclusions. "
            "`review/candidate_*.png` shows only nonexcluded candidates, with neutral T IDs.\n\n"
            "The exported crops include quarantined material for traceability. Never train by recursively "
            "loading the `crops/` directory. Select explicit eligible manifest rows only. "
            "Rows marked excluded_holdout_link or excluded_duplicate must remain out of training.\n\n"
            "File/pixel duplicates are deterministic links. Source-name and perceptual links are "
            "conservative candidates, not verified scene identities. Candidate links crossing validation/test "
            "boundaries are quarantined; duplicates within training retain one candidate copy. "
            "No link does not prove independence. Review remaining related scenes/bursts before training. "
            "Full v4 test sources are unavailable and were not inspected.\n\n"
            "The legacy destination boxes often contain both a road line and a destination line. "
            "Their field meaning must be reviewed and, when needed, split into separately annotated boxes. "
            "There is no legacy route-text class: no route crops have been invented. New route geometry "
            "must come from visible training-photo content. Keep panel/bus-front boxes as context, not text targets.\n\n"
            "Next: inspect candidate source groups and native crops; add/correct route and destination geometry; "
            "transcribe visible text using `docs/OCR_TRANSCRIPTION_RULES.md`; validate labels. "
            "Assistant-authored labels must identify reviewer_type=AI and must not claim human review. "
            "Use the actual review date, not the export date. Blank cells remain unannotated. "
            "Partial/illegible text and [UNK] syntax are not literal whole-string training targets.\n\n"
            "Reproduce from the repository root with a new output path:\n\n"
            "```sh\n.venv/bin/python scripts/prepare_local_ocr_training.py --output evaluation/ocr_training/local88-02\n```\n",
            encoding="utf-8",
        )
        # Sheets are aids only; every file and metadata row remains available at native resolution.
        font = ImageFont.load_default(size=20)
        selected = [r for r in rows if r["training_disposition"] == "candidate_pending_review"]
        (staging / "review").mkdir()
        for start in range(0, len(selected), 9):
            sheet = Image.new("RGB", (1800, 960), "#f4f4f4")
            draw = ImageDraw.Draw(sheet)
            for index, row in enumerate(selected[start:start+9]):
                x, y = index % 3 * 600, index // 3 * 320
                draw.text((x+12, y+10), f"{row['review_id']} | {row['field']}", font=font, fill="black")
                with Image.open(staging / row["crop_id"]) as crop:
                    scale = min(4, 570/crop.width, 250/crop.height)
                    if scale >= 1:
                        scale = int(scale)
                    crop = crop.resize((max(1,int(crop.width*scale)), max(1,int(crop.height*scale))), Image.Resampling.NEAREST)
                    sheet.paste(crop, (x+(600-crop.width)//2, y+50+(260-crop.height)//2))
                draw.rectangle((x+3,y+3,x+596,y+316), outline="#aaa")
            sheet.save(staging / "review" / f"candidate_{start//9+1:02d}.png")
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evaluation/ocr_training/local88-01"))
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    audit = prepare(repo, args.output.absolute())
    print(json.dumps({key: audit[key] for key in ("source_images", "text_crop_counts", "image_dispositions", "crop_dispositions", "training_ready_rows")}, indent=2))


if __name__ == "__main__":
    main()
