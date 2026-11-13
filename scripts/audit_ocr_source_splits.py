"""Audit restored OCR source identities; never read test image bytes or promote labels."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(dataset, manifests):
    preparation = json.loads((dataset / "preparation_manifest.json").read_text())
    checksums = preparation["checksums"]
    records, joins, mismatches = [], [], []
    for split in ("train", "valid", "test"):
        coco_path = dataset / split / "_annotations.coco.json"
        coco = json.loads(coco_path.read_text())
        expected = checksums.get(f"{split}/_annotations.coco.json")
        if not expected or sha256(coco_path) != expected:
            raise ValueError(f"Unverified COCO metadata: {split}")
        for image in coco["images"]:
            name = image["file_name"]
            if Path(name).name != name:
                raise ValueError("Source filenames must be basenames")
            declared = checksums.get(f"{split}/{name}")
            if not declared:
                raise ValueError(f"Missing declared hash: {split}/{name}")
            # Test hashes are metadata attestations only. Do not stat/open images.
            actual = sha256(dataset / split / name) if split != "test" else ""
            if actual and actual != declared:
                mismatches.append(f"{split}/{name}")
            records.append(dict(split=split, image=name,
                                source_name=image.get("extra", {}).get("name", ""),
                                declared_sha256=declared, actual_sha256=actual,
                                pixel_review="not_performed"))
    by_key = {(r["split"], r["image"]): r for r in records}
    for manifest_path, hash_key in manifests:
        manifest = json.loads(manifest_path.read_text())
        split = manifest["split"]
        if split not in {"train", "valid"}:
            raise ValueError("Only training/validation OCR handoffs accepted")
        coco_matches = manifest[hash_key] == sha256(dataset / split / "_annotations.coco.json")
        for image in manifest["images"]:
            restored = by_key.get((split, image["image"]))
            matches = bool(restored and restored["actual_sha256"] == image["image_sha256"])
            joins.append(dict(split=split, image=image["image"],
                              handoff_hash_matches=matches, coco_hash_matches=coco_matches))
    overlaps = []
    for key in ("declared_sha256", "source_name"):
        groups = defaultdict(list)
        for record in records:
            if record[key]:
                groups[record[key]].append(record)
        for value, members in groups.items():
            if len({r["split"] for r in members}) > 1:
                overlaps.append(dict(link_type=key, value=value,
                                     members=[dict(split=r["split"], image=r["image"]) for r in members]))
    return records, joins, dict(
        classification="observed_metadata_and_byte_identity_audit",
        dataset=str(dataset), preparation_sha256=sha256(dataset / "preparation_manifest.json"),
        source_counts={s: sum(r["split"] == s for r in records) for s in ("train", "valid", "test")},
        train_valid_image_hashes_checked=sum(bool(r["actual_sha256"]) for r in records),
        source_hash_mismatches=mismatches,
        handoff_sources_checked=len(joins), handoff_mismatches=[r for r in joins if not all(
            r[k] for k in ("handoff_hash_matches", "coco_hash_matches"))],
        cross_split_links=overlaps, test_image_bytes_read=0, test_images_decoded_or_viewed=0,
        limitations=["Test image hashes are read from preparation metadata, not reverified.",
                     "No cross-split name/hash links does not establish scene/burst independence.",
                     "Metadata source names are candidate families, not human-reviewed groups.",
                     "Existing legacy-holdout quarantine must be preserved.",
                     "No text labels, human attestations or eligibility flags are changed."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--validation-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    records, joins, report = audit(args.dataset, [
        (args.training_manifest, "coco_sha256"),
        (args.validation_manifest, "validation_coco_sha256")])
    args.output.mkdir(parents=True)
    for name, rows in (("sources.csv", records), ("handoff_identity.csv", joins)):
        with (args.output / name).open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (args.output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cross_split_links"}, indent=2))


if __name__ == "__main__":
    main()
