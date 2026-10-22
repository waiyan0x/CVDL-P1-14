"""Run reviewed-image comparisons and preserve reproducibility evidence."""
import copy
import platform
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

from .manifest import select_images
from .metrics import aggregate_engine, percentile, score_image, screen_detection_counts
from .provenance import dataset_audit

ENGINE_IDS = ("easyocr", "tesseract", "trocr")


def _scaled_truth(image: dict, width: int, height: int) -> list:
    with Image.open(image["resolved_path"]) as original:
        original_width, original_height = ImageOps.exif_transpose(original).size
    displays = copy.deepcopy(image["displays"])
    for display in displays:
        box = display["box"]
        if box[2] > original_width or box[3] > original_height:
            raise ValueError(f"Reviewed box exceeds upright image dimensions: {image['id']}/{display['id']}")
        display["box"] = [box[0] * width / original_width, box[1] * height / original_height,
                          box[2] * width / original_width, box[3] * height / original_height]
    return displays


def _identities(root: Path, catalog: dict) -> dict:
    # Identities come from the serving process, including when --base-url targets another host.
    return {model["id"]: model.get("artifact_files", {}) for model in [catalog["detector"], *catalog["ocr_engines"]]}


def run_benchmark(manifest: dict, root: Path, client, options: dict, warmup: int = 1,
                  include_overlap: bool = False) -> dict:
    selected, excluded = select_images(manifest, root, include_overlap)
    if not selected:
        raise ValueError("No evaluation images remain after excluding duplicate/training-overlap images.")
    catalog = client.models()
    available = {engine["id"] for engine in catalog["ocr_engines"] if engine["available"]}
    if not available:
        raise ValueError("No OCR engines are available on the running server.")
    if not catalog["detector"].get("artifact_files") or any(not engine.get("artifact_files") for engine in catalog["ocr_engines"] if engine["available"]):
        raise ValueError("The server did not provide model file hashes. Restart the current backend before benchmarking.")
    warmup_started = time.perf_counter()
    warmup_outcomes = []
    for _ in range(warmup):
        warmed = client.compare(selected[0]["resolved_path"], options)
        warmup_outcomes.append([{key: entry.get(key) for key in ("backend", "status", "error")} for entry in warmed["comparisons"]])
    warmup_ms = (time.perf_counter() - warmup_started) * 1000
    scored, latencies, ocr_times, failures = ({engine: [] for engine in ENGINE_IDS} for _ in range(4))
    outcomes, roundtrips = [], []
    screen_counts = {key: 0 for key in ("true_positive", "false_positive", "false_negative", "excluded_estimates")}
    for image in selected:
        started = time.perf_counter()
        comparison = client.compare(image["resolved_path"], options)
        roundtrip_ms = (time.perf_counter() - started) * 1000
        roundtrips.append(roundtrip_ms)
        truth = _scaled_truth(image, comparison["width"], comparison["height"])
        for key, count in screen_detection_counts(truth, comparison["detections"]).items():
            screen_counts[key] += count
        comparisons = {engine["backend"]: engine for engine in comparison["comparisons"]}
        image_outcome = {"image_id": image["id"], "image_sha256": image["sha256"], "roundtrip_ms": round(roundtrip_ms, 3), "engines": {}}
        for engine in ENGINE_IDS:
            entry = comparisons.get(engine, {})
            result = entry.get("result")
            success = result is not None and not entry.get("error")
            if not success and engine in available:
                failures[engine].append({"image_id": image["id"], "error": entry.get("error") or "Engine returned no result."})
            if engine not in available:
                image_outcome["engines"][engine] = {"status": "unavailable", "error": entry.get("error")}
                continue
            scored_image = score_image(truth, result.get("results", []) if success else [])
            scored[engine].append(scored_image)
            timings = result.get("timings", {}) if success else {}
            if isinstance(timings.get("total_ms"), (int, float)):
                latencies[engine].append(timings["total_ms"])
            if isinstance(timings.get("ocr_ms"), (int, float)):
                ocr_times[engine].append(timings["ocr_ms"])
            image_outcome["engines"][engine] = {"status": "success" if success else "error", "timings": timings,
                                               "error": entry.get("error"), **scored_image}
        outcomes.append(image_outcome)
    engines = {}
    for engine in ENGINE_IDS:
        metrics = aggregate_engine(scored[engine], latencies[engine]) if engine in available else None
        engines[engine] = {"status": "measured" if engine in available else "unavailable", "metrics": metrics,
                           "failure_count": len(failures[engine]), "failures": failures[engine],
                           "ocr_latency_ms": {"median": percentile(ocr_times[engine], .5), "p95": percentile(ocr_times[engine], .95)}}
    tp, fp, fn = (screen_counts[key] for key in ("true_positive", "false_positive", "false_negative"))
    created = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1, "report_type": "reviewed_manifest_benchmark", "run_id": uuid.uuid4().hex, "created_at": created,
        "dataset": {**manifest["dataset"], "evaluated_images": len(selected), "excluded_images": excluded,
                    "independence": "Known exact training overlap excluded; near-duplicate/scene independence is unverified."
                    if not include_overlap else "Training overlap was explicitly allowed; this is not independent evaluation."},
        "provenance": {"manifest_sha256": manifest["manifest_sha256"], "review": manifest["review"],
                       "manifest_path": manifest["manifest_path"],
                       "images": [{"id": image["id"], "path": str(image["resolved_path"]), "sha256": image["sha256"]} for image in selected],
                       "model_files": _identities(root, catalog), "bundled_dataset_audit": dataset_audit(root)},
        "hardware": {"server": catalog.get("runtime_hardware"), "client": {"system": platform.system(), "machine": platform.machine()}},
        "models": catalog,
        "protocol": {"settings": options, "warmup_requests": warmup, "warmup_elapsed_ms": round(warmup_ms, 3),
                     "warmup_outcomes": warmup_outcomes,
                     "same_detection_and_crops": True, "engine_order": list(ENGINE_IDS), "one_request_at_a_time": True,
                     "normalization": "Unicode NFKC, uppercase, collapse whitespace; exact uses unchanged text.",
                     "cer": "Sum of Levenshtein character errors divided by ground-truth characters; may exceed 1.",
                     "association": "Greedy one-to-one screen IoU >= 0.1; missing predicted displays count as empty text.",
                     "failure_policy": "Initially available engines' errors count as missing predictions; unavailable engines are unscored.",
                     "latency": f"Per-engine server total and OCR times after {warmup} warmup request(s); zero warmup can include lazy model loading. Sequential three-engine request roundtrip is separate. No sustained video FPS claim.",
                     "include_training_overlap": include_overlap},
        "engines": engines,
        "screen_detection": {**screen_counts, "label": "eds", "iou_threshold": .5,
                             "precision": tp / (tp + fp) if tp + fp else None,
                             "recall": tp / (tp + fn) if tp + fn else None,
                             "map_50": None, "map_50_95": None},
        "comparison_roundtrip_ms": {"median": percentile(roundtrips, .5), "p95": percentile(roundtrips, .95)},
        "outcomes": outcomes, "examples": outcomes[:12],
        "limitations": ["Human review is an attestation recorded in the manifest, not an automatic verification of transcription correctness.",
                        "Same-scene and near-duplicate leakage are not ruled out by exact hashes.",
                        "Complete accuracy covers reviewed fields only; null fields are unscored.",
                        "Reference matches are retained as examples; endpoint correctness is not scored without explicit reference ground truth.",
                        "Direct EDS precision/recall exclude inferred envelopes; this report does not calculate detector mAP."],
    }
