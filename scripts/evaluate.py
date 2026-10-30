#!/usr/bin/env python3
"""Benchmark the running comparison API against reviewed text transcriptions."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.evaluation.benchmark import run_benchmark
from backend.app.evaluation.client import ComparisonClient
from backend.app.evaluation.manifest import load_manifest


def threshold(value):
    number = float(value)
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("Thresholds must be between 0 and 1.")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="Reviewed transcription JSON; see backend/app/evaluation/MANIFEST_FORMAT.md")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, help="Default: evaluation/reports/<run_id>.json")
    parser.add_argument("--warmup", type=int, default=1, help="Unmeasured full comparison requests before timing")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--detection", type=threshold, default=.3)
    parser.add_argument("--ocr-threshold", type=threshold, default=.25)
    parser.add_argument("--similarity", type=threshold, default=.7)
    parser.add_argument("--include-overlap", action="store_true", help="Explicitly allow training overlap; report will state evaluation is not independent")
    args = parser.parse_args()
    if args.warmup < 0 or args.timeout <= 0:
        parser.error("Warmup must be nonnegative and timeout positive.")
    if not .05 <= args.detection <= .95:
        parser.error("Detection threshold must be between 0.05 and 0.95, matching the application API.")
    try:
        manifest = load_manifest(args.manifest)
        options = {"detection": args.detection, "ocr_threshold": args.ocr_threshold, "similarity": args.similarity}
        report = run_benchmark(manifest, ROOT, ComparisonClient(args.base_url, args.timeout), options,
                               args.warmup, args.include_overlap)
        destination = args.output or ROOT / "evaluation/reports" / f"{report['run_id']}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(destination)
        print(f"Saved {report['dataset']['evaluated_images']}-image reviewed benchmark to {destination}")
        for engine, result in report["engines"].items():
            metrics = result.get("metrics")
            accuracy = metrics["complete_normalized_accuracy"] if metrics else None
            print(f"{engine}: {result['status']}; complete normalized accuracy={accuracy}; failures={result['failure_count']}")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Evaluation stopped: {exc}\n")


if __name__ == "__main__":
    main()
