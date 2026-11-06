"""Standalone, ground-truth-based evaluation for single seven-segment readings.

This module does not change the bus EDS scoring contract. A reading contains one
signed or unsigned number; a field can be excluded with a ``None`` truth value.
"""

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from statistics import median
from time import perf_counter
import json
import re
import subprocess
import unicodedata


_READING = re.compile(r"[+-]?\d+(?:\.\d*)?|[+-]?\.\d+")
_SPLITS = {"train", "val", "test"}


def normalize_reading(text: str) -> str:
    """Unify spacing, Unicode minus and integer leading zeros; retain sign/scale."""
    if not isinstance(text, str):
        raise TypeError("A reading must be a string.")
    compact = "".join(unicodedata.normalize("NFKC", text).split()).replace("−", "-")
    if not _READING.fullmatch(compact):
        raise ValueError(f"Not one seven-segment numeric reading: {text!r}")
    sign = compact[0] if compact[0] in "+-" else ""
    body = compact[len(sign):]
    integer, dot, fraction = body.partition(".")
    integer = integer.lstrip("0") or "0"
    return sign + integer + (dot + fraction if dot else "")


def _normalized_prediction(text: str) -> str:
    """Keep invalid OCR text scoreable without interpreting it as a number."""
    if not text.strip():
        return ""
    try:
        return normalize_reading(text)
    except ValueError:
        return "".join(unicodedata.normalize("NFKC", text).split()).replace("−", "-")


def _edit_distance(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for row, left in enumerate(first, 1):
        current = [row]
        for column, right in enumerate(second, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (left != right)))
        previous = current
    return previous[-1]


def cer(truth: str, prediction: str, *, normalized: bool = False) -> float:
    """Character error rate: Levenshtein edits divided by truth characters.

    An empty ground-truth reading is not scoreable; use None in a field record
    for absent or unreadable ground truth instead.
    """
    if normalized:
        truth = normalize_reading(truth)
        prediction = _normalized_prediction(prediction)
    if not truth:
        raise ValueError("CER requires a nonempty ground-truth reading.")
    return _edit_distance(truth, prediction) / len(truth)


def exact_reading_match(truth: str, prediction: str, *, normalized: bool = False) -> bool:
    """Compare literal strings or the declared seven-segment normalization."""
    if normalized:
        return normalize_reading(truth) == _normalized_prediction(prediction)
    return truth == prediction


def per_field_match(truth: Mapping[str, str | None],
                    prediction: Mapping[str, str]) -> dict[str, dict[str, bool | float]]:
    """Score every applicable field; missing predictions count as empty strings."""
    scores = {}
    for field, expected in truth.items():
        if expected is None:
            continue
        observed = prediction.get(field, "")
        scores[field] = {
            "strict_match": exact_reading_match(expected, observed),
            "normalized_match": exact_reading_match(expected, observed, normalized=True),
            "cer": cer(expected, observed),
            "normalized_cer": cer(expected, observed, normalized=True),
        }
    return scores


def check_split_leakage(samples: Sequence[Mapping[str, str | int]],
                        *, adjacent_gap: int = 1) -> list[str]:
    """Report display reuse and near-consecutive cross-split recording frames.

    Required keys: split, display_group_id (stable physical display identity),
    recording_id, frame_index. Call before training and again before evaluation.
    """
    if adjacent_gap < 1:
        raise ValueError("adjacent_gap must be at least one frame.")
    displays: dict[str, set[str]] = defaultdict(set)
    recording_splits: dict[str, set[str]] = defaultdict(set)
    recordings: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for sample in samples:
        split = str(sample["split"])
        display = sample["display_group_id"]
        recording = sample["recording_id"]
        frame = sample["frame_index"]
        if (split not in _SPLITS or not isinstance(display, str) or not display.strip()
                or not isinstance(recording, str) or not recording.strip()
                or isinstance(frame, bool) or not isinstance(frame, int) or frame < 0):
            raise ValueError("Each sample needs train/val/test, stable IDs and a nonnegative integer frame_index.")
        displays[display].add(split)
        recording_splits[recording].add(split)
        recordings[recording].append((frame, split))
    issues = [f"display {name} appears in {', '.join(sorted(splits))}"
              for name, splits in sorted(displays.items()) if len(splits) > 1]
    issues.extend(f"recording {name} appears in {', '.join(sorted(splits))}"
                  for name, splits in sorted(recording_splits.items()) if len(splits) > 1)
    for recording, frames in sorted(recordings.items()):
        ordered = sorted(frames)
        for (left_frame, left_split), (right_frame, right_split) in zip(ordered, ordered[1:]):
            if left_split != right_split and right_frame - left_frame <= adjacent_gap:
                issues.append(f"recording {recording} frames {left_frame}/{right_frame} cross {left_split}/{right_split}")
    return issues


def _mps_gpu_model() -> str:
    """Read the macOS GPU model rather than guessing it from CPU architecture."""
    result = subprocess.run(["system_profiler", "SPDisplaysDataType", "-json"],
                            capture_output=True, text=True, check=True, timeout=15)
    devices = json.loads(result.stdout).get("SPDisplaysDataType", [])
    names = [item.get("sppci_model") for item in devices
             if item.get("spdisplays_metal") and item.get("sppci_model")]
    if not names:
        raise RuntimeError("Could not identify the Apple GPU model for timing provenance.")
    return str(names[0])


def _timing_summary(samples_ms: list[float], *, device: str, gpu_model: str,
                    device_index: int | None, warmup_runs: int) -> dict[str, object]:
    ordered = sorted(samples_ms)
    p95_index = (len(ordered) - 1) * .95
    lower = int(p95_index)
    p95 = ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (p95_index - lower)
    return {"device": device, "gpu_model": gpu_model, "device_index": device_index,
            "timing_method": "cuda_events" if device == "cuda" else "synchronized_wall_clock",
            "warmup_runs": warmup_runs, "timed_runs": len(samples_ms),
            "latency_ms_median": median(ordered), "latency_ms_p95": p95,
            "samples_ms": samples_ms}


def time_gpu_inference(infer: Callable[[], object], *, device: str = "cuda",
                       warmup_runs: int = 5, timed_runs: int = 30,
                       device_index: int = 0, torch_module=None) -> dict[str, object]:
    """Time an already-loaded model on CUDA or Apple MPS with GPU sync.

    ``infer`` must run one fixed-shape, fixed-batch forward pass and return no
    lazy model initialization. Data transfer must be included in ``infer`` only
    if the declared timing boundary includes transfer. No checkpoint is loaded
    by this function.
    """
    if warmup_runs < 1 or timed_runs < 1:
        raise ValueError("At least one warm-up and one timed run are required.")
    if device not in {"cuda", "mps"}:
        raise ValueError("device must be cuda or mps.")
    if torch_module is None:
        import torch as torch_module
    if device == "cuda":
        cuda = torch_module.cuda
        if not cuda.is_available():
            raise RuntimeError("CUDA is unavailable; a GPU inference time cannot be recorded.")
        with cuda.device(device_index), torch_module.inference_mode():
            gpu_model = cuda.get_device_name(device_index)
            for _ in range(warmup_runs):
                infer()
            cuda.synchronize(device_index)
            samples_ms = []
            for _ in range(timed_runs):
                start = cuda.Event(enable_timing=True)
                end = cuda.Event(enable_timing=True)
                start.record()
                infer()
                end.record()
                end.synchronize()
                samples_ms.append(float(start.elapsed_time(end)))
        return _timing_summary(samples_ms, device=device, gpu_model=gpu_model,
                               device_index=device_index, warmup_runs=warmup_runs)
    if not torch_module.backends.mps.is_available():
        raise RuntimeError("Apple MPS is unavailable; a GPU inference time cannot be recorded.")
    gpu_model = _mps_gpu_model()
    with torch_module.inference_mode():
        for _ in range(warmup_runs):
            infer()
        torch_module.mps.synchronize()
        samples_ms = []
        for _ in range(timed_runs):
            started = perf_counter()
            infer()
            torch_module.mps.synchronize()
            samples_ms.append((perf_counter() - started) * 1000)
    return _timing_summary(samples_ms, device=device, gpu_model=gpu_model,
                           device_index=None, warmup_runs=warmup_runs)
