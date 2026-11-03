"""Build a draft seven-segment OCR manifest from a reviewed crop inventory."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.evaluation.seven_segment_dataset import build_manifest, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True, help="CSV with crop paths and labels")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.inventory, dataset_id=args.dataset_id,
                              version=args.version, seed=args.seed)
    write_manifest(manifest, args.output)
    print(json.dumps({"output": str(args.output), **manifest["audit"]}, indent=2))
    return 0 if manifest["audit"]["ready_for_evaluation"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
