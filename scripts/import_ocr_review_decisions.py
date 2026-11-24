"""Generate or validate human-review decisions; never modify source labels."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.evaluation.review_decisions import create_template, import_decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("template", help="Create blank, hash-bound human decisions")
    template.add_argument("--source", type=Path, required=True)
    template.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply", help="Validate and export decisions with remaining blockers")
    apply.add_argument("--source", type=Path, required=True)
    apply.add_argument("--decisions", type=Path, required=True)
    apply.add_argument("--output", type=Path)
    apply.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "template":
            result = {"template_rows": create_template(args.source, args.output), "output": str(args.output)}
        else:
            result = import_decisions(args.source, args.decisions, args.output, args.dry_run)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
