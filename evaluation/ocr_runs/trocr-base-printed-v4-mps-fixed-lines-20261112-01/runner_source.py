"""Run frozen EasyOCR or public TrOCR on A/P crops without matching or scoring."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.evaluation.ocr_crop_baseline import (
    FIELDS, SEGMENTATION, load_crops, recognize_crop, sha256, summarize,
)
from backend.app.evaluation.ocr_line_layout import load_layout


def snapshot(root):
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def run(args):
    import csv
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
    layout_manifest, layouts, layout_hash = None, {}, None
    if args.line_layout:
        layout_manifest, layouts = load_layout(args.line_layout.resolve(), records)
        layout_hash = sha256(args.line_layout.resolve())
    source_before = snapshot(workspace)
    engine = args.engine
    if engine == "trocr" and not layout_manifest:
        raise ValueError("TrOCR comparison requires the shared frozen --line-layout")
    # Actual loading exhausted this Mac's disk through memory/swap pressure.
    # This operational margin is not a model requirement or performance target.
    if engine == "trocr" and shutil.disk_usage(ROOT).free < 3 * 1024**3:
        raise RuntimeError("TrOCR run blocked: free at least 3 GiB on the workspace volume before loading; a previous load exhausted disk space")
    weight_path = cache / ("english_g2.pth" if engine == "easyocr" else "model.safetensors")
    weight_before = sha256(weight_path)
    cached_files = sorted(p for p in cache.iterdir() if p.is_file())
    cached_weights_before = {p.name: sha256(p) for p in cached_files}
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    sync = torch.mps.synchronize if args.device == "mps" else torch.cuda.synchronize if args.device == "cuda" else lambda: None
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    try:
        if engine == "easyocr":
            import easyocr
            reader = easyocr.Reader(["en"], gpu=False if args.device == "cpu" else args.device,
                                    detector=False, recognizer=True, model_storage_directory=str(cache),
                                    user_network_directory=str(cache / "user_network"),
                                    download_enabled=False, verbose=False)
            model_name = "EasyOCR English generation-2 pretrained recognizer"
            model_provenance = {"easyocr_version": easyocr.__version__}
        else:
            from backend.app.evaluation.trocr_crop_reader import TrOCRCropReader
            model_provenance = json.loads((cache / "provenance.json").read_text())
            if model_provenance.get("repository") != "microsoft/trocr-base-printed":
                raise ValueError("Expected public pretrained TrOCR provenance")
            reader = TrOCRCropReader(cache, args.device, args.max_new_tokens)
            model_name = "microsoft/trocr-base-printed (public pretrained)"
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
        if layout_manifest:
            (output / "line_layout.json").write_bytes(args.line_layout.read_bytes())
            (output / "line_layout.sha256").write_text(layout_hash+"  line_layout.json\n")
            (output / "layout_source.py").write_bytes((ROOT / "backend/app/evaluation/ocr_line_layout.py").read_bytes())
        if engine == "trocr":
            (output / "engine_source.py").write_bytes((ROOT / "backend/app/evaluation/trocr_crop_reader.py").read_bytes())
        (output / "input_hashes.json").write_text(json.dumps(source_before, indent=2)+"\n")
        (output / "environment_requirements.txt").write_text("\n".join(f"{k}=={v}" for k, v in sorted(environment["packages"].items()))+"\n")
        warmups = []
        for field in FIELDS:
            representative = next(r for r in records if r["field"] == field and (
                not layouts or layouts[r["review_id"]]["review_status"] == "accepted"))
            for index in range(args.warmup):
                with torch.inference_mode():
                    result = recognize_crop(representative, reader, sync, layouts.get(representative["review_id"]))
                warmups.append({"review_id": representative["review_id"], "field": field, "iteration": index+1,
                                "status": result["status"], "error": result["error"]})
                if engine == "trocr":
                    warmups[-1]["engine_lines"] = reader.history[:]
                    reader.history.clear()
                if result["status"] != "success":
                    (output / "warmup.json").write_text(json.dumps(warmups, indent=2)+"\n")
                    raise RuntimeError(f"Warmup failed: {result['error']}")
        (output / "warmup.json").write_text(json.dumps(warmups, indent=2)+"\n")
        results = []
        engine_history = []
        if engine == "trocr":
            reader.history.clear()
        (output / "segmentation_previews").mkdir()
        with (output / "predictions.jsonl").open("x", encoding="utf-8") as handle:
            for index, record in enumerate(records, 1):
                with torch.inference_mode():
                    result = recognize_crop(record, reader, sync, layouts.get(record["review_id"]))
                if engine == "trocr":
                    engine_history.append({"review_id": record["review_id"], "lines": reader.history[:]})
                    reader.history.clear()
                results.append(result)
                handle.write(json.dumps(result, ensure_ascii=False, allow_nan=False)+"\n")
                handle.flush()
                # Preview drawing/saving is deliberately outside crop timing.
                with Image.open(record["crop_path"]) as original:
                    preview = original.convert("RGB")
                draw = ImageDraw.Draw(preview)
                if result["line_quads"]:
                    for quad in result["line_quads"]:
                        points = [(min(preview.width-1,x),min(preview.height-1,y)) for x,y in quad]
                        draw.line(points+[points[0]], fill=(0,255,0), width=1)
                else:
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
        cached_weights_after = {p.name: sha256(p) for p in cache.iterdir() if p.is_file()}
        if engine == "trocr":
            (output / "engine_history.json").write_text(json.dumps(engine_history, indent=2, allow_nan=False)+"\n")
        if source_after != source_before or cached_weights_after != cached_weights_before:
            raise RuntimeError("Source files or cached pretrained weights changed during the run")
        if layout_manifest and sha256(args.line_layout) != layout_hash:
            raise RuntimeError("Frozen layout changed during the run")
        summary = summarize(results)
        report = {
            "schema_version": 1, "status": "complete", "run_name": output.name,
            "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": str(workspace), "split": "valid", "inputs": len(records),
            "engine": engine, "model": model_name, "model_provenance": model_provenance,
            "model_sha256_before": weight_before,
            "model_sha256_after": sha256(weight_path), "cached_weights_unchanged": True,
            "model_files_sha256": cached_weights_before,
            "source_workspace_unchanged": True, "actual_device": actual_device,
            "seed": args.seed, "warmup_runs_per_field": args.warmup, "measured_runs_per_crop": 1,
            "warmup_policy": "First accepted-layout annotation crop per field (or first crop in automatic mode), repeated before measurements; unseen shapes can incur first-use costs",
            "frozen_line_layout": {"version": layout_manifest["version"], "sha256": layout_hash,
                                   "reviewer_type": layout_manifest["reviewer_type"], "summary": layout_manifest["summary"]} if layout_manifest else None,
            "recognition_settings": {"detector": False, "decoder": "greedy", "batch_size": 1,
                "languages": ["en"], "allowlist": None, "blocklist": None, "workers": 0,
                "contrast_ths": 0.0, "paragraph": False, "reformat": False, "download_enabled": False},
            "preprocessing": {"external_resize": None, "external_padding": None,
                "conversion": "Pillow RGB then OpenCV RGB-to-grayscale",
                "line_segmentation": {"method": layout_manifest["method"], "transform": layout_manifest["transformation"], "unresolved_policy": layout_manifest["unresolved_policy"]} if layout_manifest else SEGMENTATION,
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
        if engine == "trocr":
            report["recognition_settings"] = {"detector": False, "decoder": "greedy", "num_beams": 1,
                "do_sample": False, "batch_size": 1, "use_cache": True, "forced_eos_token_id": None,
                "max_new_tokens": args.max_new_tokens, "missing_eos_policy": "explicit error; retained token history",
                "local_files_only": True, "character_restriction": None}
            report["preprocessing"]["recognizer_resize"] = reader.processor.image_processor.to_dict()
            report["preprocessing"]["processor_input"] = "Shared grayscale region replicated to three RGB channels"
            report["confidence_method"] = "Per-line geometric mean of generated token probabilities excluding special tokens; crop character-weighted mean of line scores; not calibrated or comparable with EasyOCR confidence"
            report["timing"]["recognition_ms"] = "Sum of synchronized wall times around line processor resize/normalization, device transfer, generation, token confidence and text decode"
        if layout_manifest:
            report["limitations"][0] = "Fixed upstream geometry was visually reviewed by AI, not independently adjudicated by a human; it is diagnostic layout information, not automatic deployment performance"
        (output / "report.json").write_text(json.dumps(report, indent=2)+"\n")
        lines = [f"# {model_name} recognition-only crop run", "", f"Actual recognizer device: **{actual_device}**. All {len(records)} crop IDs attempted.", "",
                 "| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |",
                 "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for row in summary:
            fmt = lambda value: "n/a" if value is None else f"{value:.2f}"
            lines.append(f"| {row['crop_set']} | {row['field']} | {row['completed']} | {row['errors']} | {row['empty_outputs']} | {row['multiline_candidates']} | {fmt(row['recognition_ms_median'])} / {fmt(row['recognition_ms_p95'])} | {fmt(row['crop_total_ms_median'])} / {fmt(row['crop_total_ms_p95'])} |")
        lines += ["", "Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.",
                  "", "Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.",
                  "`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.",
                  "", "Fixed layouts, when supplied, are AI-reviewed diagnostic geometry; automatic layouts remain unverified candidates. No independent human review or dataset independence is claimed.",
                  "Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.", ""]
        (output / "README.md").write_text("\n".join(lines))
        print(json.dumps(summary, indent=2), flush=True)
        return report
    except Exception:
        failure = {"status": "failed", "traceback": traceback.format_exc()}
        try:
            (output / "failure.json").write_text(json.dumps(failure, indent=2)+"\n")
        except OSError:
            print("Could not write failure.json; retaining original exception", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "evaluation/ocr_annotations/v4-reviewed-01")
    parser.add_argument("--engine", choices=("easyocr", "trocr"), default="easyocr")
    parser.add_argument("--cache", type=Path, help="Defaults to the selected engine cache under .cache/")
    parser.add_argument("--max-new-tokens", type=int, default=64, help="TrOCR per-line generation cap; missing EOS is an error")
    parser.add_argument("--device", choices=("cpu", "mps", "cuda"), default="mps")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--line-layout", type=Path, help="Optional frozen manifest.json with adjacent manifest.sha256; unresolved rows never fall back")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cache is None:
        args.cache = ROOT / ".cache" / ("easyocr" if args.engine == "easyocr" else "trocr-base-printed")
    if not 1 <= args.max_new_tokens <= 256:
        parser.error("max-new-tokens must be between 1 and 256")
    if args.warmup < 1:
        parser.error("At least one warmup per field is required")
    run(args)


if __name__ == "__main__":
    main()
