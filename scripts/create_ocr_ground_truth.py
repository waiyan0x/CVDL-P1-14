"""Create an unannotated EDS ground-truth CSV, one row per crop file.

Uses only the Python standard library. Never runs OCR or guesses labels.
"""

import argparse
import csv
import os
from pathlib import Path


COLUMNS = [
    "crop_id", "source_image", "group_id", "view", "field", "bbox", "text",
    "legibility", "lighting", "split",
]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crop_folder", type=Path, help="Folder containing crops; searched recursively")
    parser.add_argument("--output", type=Path, required=True, help="New CSV path; existing files are never overwritten")
    parser.add_argument("--view", choices=["front", "side", "rear"], default="")
    parser.add_argument("--field", choices=["front_eds_num", "front_eds_destination", "front_eds_route"], default="")
    parser.add_argument("--lighting", choices=["day", "night"], default="")
    parser.add_argument("--split", choices=["train", "valid", "test"], default="")
    args = parser.parse_args()
    root = args.crop_folder.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Crop folder is not a directory: {root}")
    # Do not follow symlinks into a different dataset or outside the crop root.
    crops = []

    def walk_error(exc: OSError) -> None:
        parser.error(f"Cannot read crop folder: {exc}")

    for directory, subdirs, filenames in os.walk(root, followlinks=False, onerror=walk_error):
        subdirs[:] = sorted(name for name in subdirs if not name.startswith(".")
                            and not (Path(directory) / name).is_symlink())
        for name in filenames:
            path = Path(directory) / name
            if (not name.startswith(".") and not path.is_symlink()
                    and path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS):
                crops.append(path)
    crops.sort()
    if not crops:
        parser.error(f"No supported crop files found in {root}; no CSV created")
    output = args.output.expanduser().absolute()
    try:
        with output.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            for crop in crops:
                row = dict.fromkeys(COLUMNS, "")
                row.update(crop_id=crop.relative_to(root).as_posix(), view=args.view,
                           field=args.field, lighting=args.lighting, split=args.split)
                writer.writerow(row)
    except FileExistsError:
        parser.error(f"Output already exists; choose a new path: {output}")
    except OSError as exc:
        parser.error(f"Cannot write output: {exc}")
    print(f"Created {output} with {len(crops)} unannotated rows (crop root: {root}).")
    print("Review all metadata and transcribe visible text before using this CSV for scoring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
