"""Run frozen EasyOCR weights on A/P validation crops, without matching or scoring."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.evaluation.ocr_crop_baseline import (
    FIELDS, SEGMENTATION, load_crops, recognize_crop, sha256, summarize,
)


def snapshot(root):
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def run(args):
    import csv
    import easyocr
    import numpy as np
    import torch
    from PIL import Image, ImageDraw

    workspace, cache, output = args.workspace.resolve(), args.cache.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Output exists; choose a new run name: {output}")
    if output.is_relative_to(workspace) or output.is_relative_to(cache):
        raise ValueError("Outputs must be outside the source workspace and model cache")
    if args.device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS unavailable; CPU fallback is forbidden for this run")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; CPU fallback is forbidden for this run")
    records = load_crops(workspace)
    source_before = snapshot(workspace)
    weight_path = cache / "english_g2.pth"
    weight_before = sha256(weight_path)
    cached_weights_before = {p.name: sha256(p) for p in cache.glob("*.pth")}
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    sync = torch.mps.synchronize if args.device == "mps" else torch.cuda.synchronize if args.device == "cuda" else lambda: None
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    try:
        reader = easyocr.Reader(["en"], gpu=False if args.device == "cpu" else args.device,
                                detector=False, recognizer=True, model_storage_directory=str(cache),
                                user_network_directory=str(cache / "user_network"),
                                download_enabled=False, verbose=False)
        reader.recognizer.eval()
        actual_device = str(next(reader.recognizer.parameters()).device)
        if actual_device.split(":")[0] != args.device:
            raise RuntimeError(f"Recognizer device mismatch: requested {args.device}, got {actual_device}")
        print(f"Recognizer parameters: {actual_device}; {len(records)} crops", flush=True)
        environment = {
            "python": sys.version, "python_executable": sys.executable, "platform": platform.platform(),
            "machine": platform.machine(), "processor": platform.processor(), "cpu_count": os.cpu_count(),
            "memory_bytes": os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES"),
            "requested_device": args.device, "reader_device": str(reader.device),
            "recognizer_parameter_device": actual_device, "parameter_dtype": str(next(reader.recognizer.parameters()).dtype),
            "mps_available": torch.backends.mps.is_available(), "cuda_available": torch.cuda.is_available(),
            "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions() if d.metadata.get("Name")},
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "runner_sha256": sha256(Path(__file__)),
            "core_sha256": sha256(ROOT / "backend/app/evaluation/ocr_crop_baseline.py"),
            "mps_environment": {key: os.environ.get(key) for key in ("PYTORCH_ENABLE_MPS_FALLBACK", "PYTORCH_MPS_FAST_MATH")},
            "cpu_threads": torch.get_num_threads(),
        }
        if sys.platform == "darwin":
            environment["chip"] = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        (output / "environment.json").write_text(json.dumps(environment, indent=2)+"\n")
        (output / "command.json").write_text(json.dumps([sys.executable, *sys.argv], indent=2)+"\n")
        (output / "runner_source.py").write_bytes(Path(__file__).read_bytes())
        (output / "core_source.py").write_bytes((ROOT / "backend/app/evaluation/ocr_crop_baseline.py").read_bytes())
        (output / "input_hashes.json").write_text(json.dumps(source_before, indent=2)+"\n")
        (output / "environment_requirements.txt").write_text("\n".join(f"{k}=={v}" for k, v in sorted(environment["packages"].items()))+"\n")
        warmups = []
        for field in FIELDS:
            representative = next(r for r in records if r["field"] == field)
            for index in range(args.warmup):
                with torch.inference_mode():
                    result = recognize_crop(representative, reader, sync)
                warmups.append({"review_id": representative["review_id"], "field": field, "iteration": index+1,
                                "status": result["status"], "error": result["error"]})
                if result["status"] != "success":
                    raise RuntimeError(f"Warmup failed: {result['error']}")
        (output / "warmup.json").write_text(json.dumps(warmups, indent=2)+"\n")
        results = []
        (output / "segmentation_previews").mkdir()
        with (output / "predictions.jsonl").open("x", encoding="utf-8") as handle:
            for index, record in enumerate(records, 1):
                with torch.inference_mode():
                    result = recognize_crop(record, reader, sync)
                results.append(result)
                handle.write(json.dumps(result, ensure_ascii=False, allow_nan=False)+"\n")
                handle.flush()
                # Preview drawing/saving is deliberately outside crop timing.
                with Image.open(record["crop_path"]) as original:
                    preview = original.convert("RGB")
                draw = ImageDraw.Draw(preview)
                for box in result["line_regions"]:
                    x1, y1, x2, y2 = box
                    draw.rectangle((x1, y1, x2-1, y2-1), outline=(0, 255, 0), width=1)
                preview.save(output / "segmentation_previews" / f"{record['review_id']}.png")
                if index % 25 == 0 or index == len(records):
                    print(f"{index}/{len(records)} crops; errors={sum(r['status'] != 'success' for r in results)}", flush=True)
        flat_columns = ["review_id", "crop_set", "field", "crop_id", "crop_sha256", "source_image_sha256",
                        "input_width", "input_height", "status", "raw_text", "ocr_confidence", "line_count",
                        "preprocessing_ms", "recognition_ms", "crop_total_ms", "error"]
        with (output / "predictions.csv").open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=flat_columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows({key: row[key] for key in flat_columns} for row in results)
        source_after = snapshot(workspace)
        cached_weights_after = {p.name: sha256(p) for p in cache.glob("*.pth")}
        if source_after != source_before or cached_weights_after != cached_weights_before:
            raise RuntimeError("Source files or cached pretrained weights changed during the run")
        summary = summarize(results)
        report = {
            "schema_version": 1, "status": "complete", "run_name": output.name,
            "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": str(workspace), "split": "valid", "inputs": len(records),
            "model": "EasyOCR English generation-2 pretrained recognizer",
            "easyocr_version": easyocr.__version__, "model_sha256_before": weight_before,
            "model_sha256_after": sha256(weight_path), "cached_weights_unchanged": True,
            "source_workspace_unchanged": True, "actual_device": actual_device,
            "seed": args.seed, "warmup_runs_per_field": args.warmup, "measured_runs_per_crop": 1,
            "warmup_policy": "First annotation crop per field, repeated before measurements; unseen shapes can incur first-use costs",
            "recognition_settings": {"detector": False, "decoder": "greedy", "batch_size": 1,
                "languages": ["en"], "allowlist": None, "blocklist": None, "workers": 0,
                "contrast_ths": 0.0, "paragraph": False, "reformat": False, "download_enabled": False},
            "preprocessing": {"external_resize": None, "external_padding": None,
                "conversion": "Pillow RGB then OpenCV RGB-to-grayscale", "line_segmentation": SEGMENTATION,
                "recognizer_resize": "Unmodified EasyOCR internal height/aspect-dependent width preprocessing"},
            "confidence_method": "Character-count-weighted mean of EasyOCR returned region confidences, excluding inserted newlines; empty output has null score",
            "raw_text_assembly": "Preserve each returned string; join regions/lines top-to-bottom with actual newlines; no spelling/case/reference correction",
            "timing": {
                "preprocessing_ms": "File read, SHA-256 check, image decode, RGB/grayscale conversion and line segmentation",
                "recognition_ms": "Sum of synchronized wall times around each Reader.recognize call, including internal resize/transfer/forward/decode",
                "crop_total_ms": "Wall time for preprocessing, synchronized recognition and result assembly",
                "excluded": "Model initialization, warmups, preflight/integrity hashing, previews and result-file writes",
                "percentile": "Linear interpolation at (n-1)*q across successful heterogeneous crops, separately by set/field",
            },
            "summary": summary, "accuracy_calculated": False, "reference_matching_used": False,
            "limitations": ["Line regions are unverified heuristic candidates; single-band results may conceal touching/overlapping lines",
                "No foreground/fragmented layouts return an explicit error, never an unreported full-crop fallback",
                "One timed pass per crop; timings include varying image/line counts and first-use shape costs, not sustained end-to-end FPS",
                "Only existing crops are recognized; missing detections and zero-box images are outside this crop-only run",
                "Ground-truth resolution, related-frame group review and prediction correspondence remain outstanding",
                "English pretrained vocabulary may not cover every visible symbol or script",
                "No accuracy, independence, training, model selection or fine-tuning claim is made"],
        }
        (output / "report.json").write_text(json.dumps(report, indent=2)+"\n")
        lines = ["# EasyOCR recognition-only crop run", "", f"Actual recognizer device: **{actual_device}**. All {len(records)} crop IDs attempted.", "",
                 "| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |",
                 "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for row in summary:
            fmt = lambda value: "n/a" if value is None else f"{value:.2f}"
            lines.append(f"| {row['crop_set']} | {row['field']} | {row['completed']} | {row['errors']} | {row['empty_outputs']} | {row['multiline_candidates']} | {fmt(row['recognition_ms_median'])} / {fmt(row['recognition_ms_p95'])} | {fmt(row['crop_total_ms_median'])} / {fmt(row['crop_total_ms_p95'])} |")
        lines += ["", "Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.",
                  "", "Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.",
                  "`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.",
                  "", "All line regions—including single-band cases—are unverified candidates. No claim of correct segmentation or dataset independence is made.",
                  "Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.", ""]
        (output / "README.md").write_text("\n".join(lines))
        print(json.dumps(summary, indent=2), flush=True)
        return report
    except Exception:
        (output / "failure.json").write_text(json.dumps({"status": "failed", "traceback": traceback.format_exc()}, indent=2)+"\n")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "evaluation/ocr_annotations/v4-reviewed-01")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/easyocr")
    parser.add_argument("--device", choices=("cpu", "mps", "cuda"), default="mps")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.warmup < 1:
        parser.error("At least one warmup per field is required")
    run(args)


if __name__ == "__main__":
    main()
