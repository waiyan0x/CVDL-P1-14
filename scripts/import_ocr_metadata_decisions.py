"""Prepare bound human metadata forms or import text/group/pair decisions together."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.metadata_review import ReviewBundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("template", "apply"))
    parser.add_argument("--review", action="append", type=Path, required=True)
    parser.add_argument("--policy-review", action="append", type=Path, default=[])
    parser.add_argument("--group-source", type=Path, required=True)
    parser.add_argument("--pair-source", type=Path, required=True)
    parser.add_argument("--split-registry", type=Path, required=True)
    parser.add_argument("--source-policy", type=Path)
    parser.add_argument("--groups", type=Path)
    parser.add_argument("--pairings", type=Path)
    parser.add_argument("--text-decisions", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        bundle = ReviewBundle(args.review, args.policy_review, args.group_source,
                              args.pair_source, args.split_registry, args.source_policy)
        if args.command == "template":
            if args.dry_run:
                parser.error("template does not use --dry-run")
            bundle.prepare(args.output)
            result = {"templates": str(args.output), "source_bundle_sha256": bundle.binding}
        else:
            if not args.groups or not args.pairings:
                parser.error("apply requires --groups and --pairings")
            result = bundle.apply(args.groups, args.pairings, args.output,
                                  args.text_decisions, args.dry_run)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
