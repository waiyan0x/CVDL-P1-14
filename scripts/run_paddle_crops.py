"""Run a pinned local PaddleOCR model on the same frozen validation crop layouts."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(args):
    # Keep third-party caches inside the project. Native inference is CPU-only here.
    cache_root = ROOT/".cache/paddle-runtime"
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache_root)
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    from paddleocr import TextRecognition
    import paddle
    import numpy as np
    from backend.app.evaluation.ocr_crop_baseline import load_crops, recognize_crop, sha256, summarize, FIELDS
    from backend.app.evaluation.ocr_line_layout import load_layout
    from backend.app.evaluation.paddle_crop_reader import PaddleCropReader

    workspace, output, model_dir = args.workspace.resolve(), args.output.resolve(), args.model_dir.resolve()
    if output.exists() or output.is_relative_to(workspace) or output.is_relative_to(model_dir):
        raise ValueError("Choose a new output outside workspace/model directory")
    provenance = json.loads((model_dir/"provenance.json").read_text())
    if provenance.get("repository") != "PaddlePaddle/en_PP-OCRv5_mobile_rec":
        raise ValueError("Expected pinned public English PaddleOCR v5 model")
    hashes = {p.name: sha256(p) for p in model_dir.iterdir() if p.is_file()}
    if any(hashes.get(k) != v for k, v in provenance["files_sha256"].items()):
        raise ValueError("Model hash differs from download provenance")
    records = load_crops(workspace)
    manifest, layouts = load_layout(args.line_layout.resolve(), records)
    layout_hash = sha256(args.line_layout)
    # Retain source metadata/bytes unchanged; no test dataset is discovered.
    sources = [p for p in (workspace/"source").rglob("*") if p.is_file()]
    source_hashes = {str(p): sha256(p) for p in sources}
    paddle.seed(0)
    np.random.seed(0)
    model = TextRecognition(model_name="en_PP-OCRv5_mobile_rec", model_dir=str(model_dir),
                            device="cpu", enable_mkldnn=False, cpu_threads=2)
    reader = PaddleCropReader(model)
    warmups = []
    for field in FIELDS:
        record = next(r for r in records if r["field"] == field and layouts[r["review_id"]]["line_quads"])
        for _ in range(args.warmup):
            warm = recognize_crop(record, reader, lambda: None, layouts[record["review_id"]])
            if warm["status"] != "success":
                raise RuntimeError(f"Paddle warmup failed: {warm['error']}")
            warmups.append({"review_id": record["review_id"], "status": warm["status"]})
    output.mkdir(parents=True, exist_ok=False)
    (output/"warmup.json").write_text(json.dumps(warmups, indent=2)+'\n')
    results = []
    started = datetime.now(timezone.utc).isoformat()
    with (output/"predictions.jsonl").open("x", encoding="utf-8") as handle:
        for index, record in enumerate(records, 1):
            result = recognize_crop(record, reader, lambda: None, layouts[record["review_id"]])
            results.append(result)
            handle.write(json.dumps(result, ensure_ascii=False, allow_nan=False)+'\n')
            handle.flush()
            if index % 25 == 0 or index == len(records):
                print(f"{index}/{len(records)} crops", flush=True)
    if any(sha256(Path(p)) != h for p, h in source_hashes.items()):
        raise RuntimeError("Source changed during inference")
    if {p.name: sha256(p) for p in model_dir.iterdir() if p.is_file()} != hashes or sha256(args.line_layout) != layout_hash:
        raise RuntimeError("Model/layout changed during inference")
    report = {"schema_version": 1, "status": "complete", "run_name": output.name,
              "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "engine": "paddleocr", "model": "en_PP-OCRv5_mobile_rec (public pretrained)",
              "model_provenance": provenance, "model_files_sha256": hashes,
              "model_sha256_before": hashes["inference.pdiparams"], "model_sha256_after": hashes["inference.pdiparams"],
              "cached_weights_unchanged": True, "source_workspace_unchanged": True,
              "split": "valid", "inputs": len(records), "actual_device": "cpu",
              "frozen_line_layout": {"sha256": layout_hash, "version": manifest["version"],
                                     "reviewer_type": manifest["reviewer_type"]},
              "recognition_settings": {"batch_size": 1, "cpu_threads": 2, "enable_mkldnn": False, "seed": 0},
              "preprocessing": "Shared frozen grayscale line extraction; RGB replication; native Paddle resize/normalization",
              "warmup_policy": "First accepted crop per field; discarded before measured pass",
              "warmup_runs_per_field": args.warmup,
              "timing": {"crop_total_ms": "Wall time for file/hash/decode, shared layout extraction, CPU prediction and assembly",
                         "recognition_ms": "Sum of wall times around adapter line calls, including native processor and decode",
                         "excluded": "Model loading, warmups, preflight hashing and output writes"},
              "summary": summarize(results), "accuracy_calculated": False, "reference_matching_used": False,
              "limitations": ["CPU diagnostic baseline; do not rank latency against MPS or CUDA runs.",
                              "Shared layouts are AI-reviewed diagnostic geometry, not independently reviewed deployable detection."]}
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    environment = {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
                   "processor": platform.processor(), "packages": {d.metadata["Name"]:d.version for d in importlib.metadata.distributions() if d.metadata.get("Name")}}
    (output/"environment.json").write_text(json.dumps(environment, indent=2)+'\n')
    (output/"command.json").write_text(json.dumps({"argv":sys.argv}, indent=2)+'\n')
    for source in [Path(__file__), ROOT/"backend/app/evaluation/paddle_crop_reader.py", ROOT/"backend/app/evaluation/ocr_crop_baseline.py", ROOT/"backend/app/evaluation/ocr_line_layout.py"]:
        (output/source.name).write_bytes(source.read_bytes())
    print(f"Saved {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--line-layout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=3)
    args = parser.parse_args()
    if args.warmup < 1:
        parser.error("At least one warmup per field required")
    run(args)


if __name__ == "__main__":
    main()
