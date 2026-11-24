"""Run one seven-segment baseline on reviewed val/test crops into the CSV schema."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.evaluation.seven_segment import (
    _normalized_prediction, cer, exact_reading_match, normalize_reading,
    time_gpu_inference,
)
from backend.app.evaluation.seven_segment_baselines import (
    EasyOCRBaseline, TemplateBaseline, TesseractBaseline,
)
from backend.app.evaluation.seven_segment_dataset import audit_manifest


ROOT = Path(__file__).resolve().parents[1]


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    point = (len(ordered) - 1) * fraction
    low = int(point)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (point - low)


def _cpu_timing(infer, *, warmup_runs: int, timed_runs: int) -> dict:
    for _ in range(warmup_runs):
        infer()
    samples = []
    for _ in range(timed_runs):
        start = perf_counter()
        infer()
        samples.append((perf_counter() - start) * 1000)
    return {"device": "cpu", "gpu_model": "", "timing_method": "wall_clock_cpu",
            "warmup_runs": warmup_runs, "timed_runs": timed_runs,
            "latency_ms_median": statistics.median(samples),
            "latency_ms_p95": _percentile(samples, .95)}


def run(manifest_path: Path, *, engine: str, split: str, run_id: str,
        output: Path, templates: Path | None = None, device: str = "cpu",
        warmup_runs: int = 2, timed_runs: int = 5,
        checkpoint_sha256: str = "") -> dict:
    if split not in {"val", "test"}:
        raise ValueError("Baselines may run only on a reviewed val or test split.")
    if not run_id.strip():
        raise ValueError("run_id is required.")
    if warmup_runs < 1 or timed_runs < 1:
        raise ValueError("At least one warm-up and one timed run are required.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported manifest schema.")
    samples = manifest.get("samples") or []
    audit = audit_manifest(samples)
    if not audit["ready_for_evaluation"]:
        raise ValueError("Manifest is not ready: " + "; ".join(audit["issues"]))
    selected = [row for row in samples if row["split"] == split and row["label_status"] == "readable"]
    if not selected:
        raise ValueError(f"No reviewed readable crops in {split}.")
    for row in selected:
        path = Path(row["crop_path"])
        if not path.is_file() or _hash(path) != row["crop_sha256"]:
            raise ValueError(f"Crop missing or changed: {row['sample_id']}")
    if engine == "template":
        if templates is None:
            raise ValueError("Template baseline requires --templates from training data.")
        predictor = TemplateBaseline(templates, training_sample_ids={row["sample_id"] for row in samples
                                                             if row["split"] == "train"})
        checkpoint_sha256 = hashlib.sha256("".join(sorted(
            _hash(path) for path in templates.glob("*.png"))).encode()
            + (templates / "templates.json").read_bytes()).hexdigest()
        confidence_method = "mean_glyph_template_similarity"
    elif engine == "tesseract":
        predictor = TesseractBaseline()
        confidence_method = "character_weighted_word_confidence"
    elif engine == "easyocr":
        predictor = EasyOCRBaseline(device=device)
        confidence_method = "character_weighted_recognition_score"
    else:
        raise ValueError("engine must be template, tesseract or easyocr.")
    if predictor.device != device:
        raise ValueError(f"{engine} runs on {predictor.device}; use --device {predictor.device}.")
    schema_path = ROOT / "evaluation/seven_segment_results.schema.csv"
    with schema_path.open(newline="", encoding="utf-8") as stream:
        columns = next(csv.reader(stream))
    rows = []
    for sample in selected:
        path = Path(sample["crop_path"])
        prediction, confidence = predictor.predict(path)
        call = lambda: predictor.predict(path)
        timing = (time_gpu_inference(call, device=device, warmup_runs=warmup_runs,
                                     timed_runs=timed_runs)
                  if device in {"cuda", "mps"} else
                  _cpu_timing(call, warmup_runs=warmup_runs, timed_runs=timed_runs))
        truth = sample["truth_raw"]
        rows.append({"run_id": run_id, "dataset_version": manifest["dataset"]["version"],
                     "split": split, "display_group_id": sample["display_group_id"],
                     "recording_id": sample["recording_id"], "frame_index": sample["frame_index"],
                     "field_name": sample["field_name"], "truth_raw": truth,
                     "prediction_raw": prediction, "prediction_normalized": _normalized_prediction(prediction),
                     "truth_normalized": normalize_reading(truth), "ocr_confidence": confidence,
                     "confidence_method": confidence_method,
                     "strict_match": str(exact_reading_match(truth, prediction)).lower(),
                     "normalized_match": str(exact_reading_match(truth, prediction, normalized=True)).lower(),
                     "cer": cer(truth, prediction), "normalized_cer": cer(truth, prediction, normalized=True),
                     "model_id": predictor.model_id, "checkpoint_sha256": checkpoint_sha256,
                     "crop_source": "reviewed_crop", "crop_sha256": sample["crop_sha256"],
                     "input_width": sample["input_width"], "input_height": sample["input_height"],
                     **{key: timing[key] for key in ("device", "gpu_model", "timing_method", "warmup_runs",
                                                        "timed_runs", "latency_ms_median", "latency_ms_p95")}})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    return {"output": str(output), "engine": engine, "split": split,
            "samples": len(rows), "strict_matches": sum(r["strict_match"] == "true" for r in rows),
            "normalized_matches": sum(r["normalized_match"] == "true" for r in rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--engine", choices=("template", "tesseract", "easyocr"), required=True)
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--templates", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--timed-runs", type=int, default=5)
    parser.add_argument("--checkpoint-sha256", default="")
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, engine=args.engine, split=args.split,
                         run_id=args.run_id, output=args.output, templates=args.templates,
                         device=args.device, warmup_runs=args.warmup_runs,
                         timed_runs=args.timed_runs,
                         checkpoint_sha256=args.checkpoint_sha256), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
