"""Audit accepted labels; optionally export reviewed training-only exclusions."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/labelled/2026-10-24")
    parser.add_argument("--report", type=Path, help="Save the JSON audit outside the input dataset")
    parser.add_argument("--exclusions", type=Path, default=ROOT / "data/manifests/2026-10-24-training-exclusions.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/labelled/2026-10-24-clean-v1")
    parser.add_argument("--write", action="store_true", help="Create a new export; preserve accepted inputs")
    args = parser.parse_args()
    from data_preparation.datasets import load_coco_splits
    from data_preparation.readiness import audit_labels, clean_labels
    import torch
    import cv2
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    if args.report and (args.report.resolve().is_relative_to(args.input.resolve())
                        or args.report.resolve().is_relative_to(args.output.resolve())):
        parser.error("Report must be outside input/output datasets")
    # Audit/cleaning may inspect known exact overlaps; final model loading stays strict.
    datasets = load_coco_splits(args.input, allow_cross_split_duplicates=True)
    report = audit_labels(datasets)
    if args.write:
        decisions = json.loads(args.exclusions.read_text(encoding="utf-8"))
        report = clean_labels(datasets, args.output, decisions)["audit"]
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["automated_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
