"""Validate accepted COCO labels and optionally write training-only augmentation."""
from pathlib import Path
import argparse
import json
import sys
import cv2
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.config import CUTOFF, SEED, AUGMENTATION, EXCLUDED_PREFIXES
from data_preparation.datasets import load_coco_splits, dataset_summary, find_cross_split_pairs
from data_preparation.readiness import audit_labels
from data_preparation.augmentation import build_augmented_dataset


def main():
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default=CUTOFF)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--multiplier", type=int, default=AUGMENTATION['multiplier'])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    source = args.input or ROOT / "data/labelled" / args.cutoff
    output = args.output or ROOT / "data/processed" / args.cutoff / "eds-torch-v2"
    datasets = load_coco_splits(source)
    drafts = [row['image']['file_name'] for dataset in datasets.values() for row in dataset['rows']
              if row['image'].get('review_status') in {'draft', 'needs_review', 'needs_review_empty'}]
    if drafts:
        raise ValueError("Review/correct draft labels and mark image review_status='accepted' before augmentation")
    pairs = find_cross_split_pairs(datasets)
    print(json.dumps(dict(splits=dataset_summary(datasets), similar_scene_pairs=pairs), indent=2))
    if args.write:
        if not audit_labels(datasets)['automated_checks_passed']:
            raise ValueError("Resolve cross-split similarity, marked-up images and class issues first; "
                             "use scripts/00_audit_dataset.py and the reviewed clean export")
        settings = dict(AUGMENTATION, multiplier=args.multiplier)
        manifest = build_augmented_dataset(datasets, output, settings, args.seed, EXCLUDED_PREFIXES)
        print(json.dumps(dict(output=str(output), files=len(manifest['checksums'])), indent=2))
    else:
        print("Validation only. Review similar-scene pairs; add --write to export training variants.")


if __name__ == "__main__":
    main()
