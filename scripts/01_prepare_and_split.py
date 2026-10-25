"""Plan grouped raw-image splits; only --write exports a new frozen snapshot."""
from pathlib import Path
import argparse
from collections import Counter
import json
import sys
import cv2
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.config import CUTOFF, SEED, RATIOS, EXCLUDED_PREFIXES
from data_preparation.splitting import inspect_raw, make_split_plan, write_raw_split


def main():
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default=CUTOFF)
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--groups", type=Path, help="Optional source,group CSV")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    raw = args.raw or ROOT / "data/raw" / args.cutoff
    output = args.output or raw / "splits/torch-v1"
    groups = args.groups or ROOT / "data/groups" / f"{args.cutoff}.csv"
    inventory, unique, excluded = inspect_raw(raw, EXCLUDED_PREFIXES)
    plan = make_split_plan(unique, RATIOS, args.seed, groups)
    print(json.dumps(dict(raw=len(inventory), eligible=len(unique),
                         excluded=[row['source'] for row in excluded],
                         planned=dict(Counter(row['split'] for row in plan))), indent=2))
    if args.write:
        write_raw_split(plan, output, raw=raw, inventory=inventory, seed=args.seed, ratios=RATIOS)
        print(f"Frozen split: {output}")
    else:
        print("Plan only. Use --write with a NEW output directory to freeze splits before annotation.")


if __name__ == "__main__":
    main()
