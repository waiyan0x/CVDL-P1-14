"""Freeze reviewed crop eligibility or score saved predictions; never run OCR."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.crop_scoring import freeze_manifest, build_report, write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--review", type=Path, action="append", required=True)
    freeze.add_argument("--output", type=Path, required=True)
    score = commands.add_parser("report")
    score.add_argument("--manifest", type=Path, required=True)
    score.add_argument("--config", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            manifest = freeze_manifest(args.review)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
            print(json.dumps({"rows": len(manifest["rows"]),
                              "eligible": sum(r["scoring_eligible"] for r in manifest["rows"]),
                              "manifest_sha256": manifest["manifest_sha256"]}))
        else:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            config = json.loads(args.config.read_text(encoding="utf-8"))
            report = build_report(manifest, config, args.config.resolve().parent)
            write_report(report, args.output)
            print(f"Created {args.output / 'tables.html'} and report.json; no images opened.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
