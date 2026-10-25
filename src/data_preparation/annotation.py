"""Isolated Autodistill EDS proposals; no inference or file writes on import."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from PIL import Image, ImageOps
import supervision as sv
import torch
from torchvision.ops import batched_nms, box_iou
from autodistill.detection import CaptionOntology, DetectionBaseModel

from .config import ROOT
from .annotation_cli import discover_images

EXPERIMENT = ROOT / "experiments/eds_autodistill"
CLASS_NAMES = ["front_eds", "front_eds_num", "front_eds_route", "front_eds_destination"]
# Positive visual captions for Grounding DINO; acceptance rules remain in the guide.
CAPTIONS = {
    "electronic destination sign display panel on the front or side of a bus": "front_eds",
    "bus service number group inside an electronic destination sign": "front_eds_num",
    "small thin intermediate road names or via route details inside a bus electronic destination sign": "front_eds_route",
    "large bold final destination text with its arrow inside a bus electronic destination sign": "front_eds_destination",
}


def sha256(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        # Some existing .jpg files are AVIF; this is a Windows codec fallback.
        with Image.open(path) as opened:
            rgb = np.array(ImageOps.exif_transpose(opened).convert("RGB"))
        image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return image


def write_png(path: Path, bgr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    success, encoded = cv2.imencode(".png", bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not success:
        raise ValueError(f"Cannot encode {path}")
    encoded.tofile(path)

class LocalGroundingDINO(DetectionBaseModel):
    """Autodistill adapter using native Transformers/PyTorch, including Windows CPU."""
    def __init__(self, model_id="IDEA-Research/grounding-dino-tiny", revision="main",
                 box_threshold=.30, text_threshold=.25, device=None):
        # Import/loading is deferred until this constructor is explicitly called.
        from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        cache = EXPERIMENT / "cache"
        self.ontology = CaptionOntology(CAPTIONS)
        self.model_id, self.revision = model_id, revision
        self.box_threshold, self.text_threshold = box_threshold, text_threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        torch.set_num_threads(4)
        self.processor = AutoProcessor.from_pretrained(
            model_id, revision=revision, cache_dir=cache, token=False, trust_remote_code=False)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(
            model_id, revision=revision, cache_dir=cache, token=False,
            trust_remote_code=False, use_safetensors=True, disable_custom_kernels=True,
        ).to(self.device).eval()

    @torch.inference_mode()
    def predict(self, input: str | Path | np.ndarray | Image.Image) -> sv.Detections:
        if isinstance(input, (str, Path)):
            bgr = read_bgr(Path(input))
        elif isinstance(input, Image.Image):
            bgr = cv2.cvtColor(np.array(ImageOps.exif_transpose(input).convert("RGB")), cv2.COLOR_RGB2BGR)
        else:
            bgr = np.asarray(input)  # Autodistill ndarray convention is BGR.
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        boxes, scores, classes = [], [], []
        # Separate prompt passes give explicit canonical class IDs; no text-label guessing.
        for caption, name in CAPTIONS.items():
            inputs = self.processor(images=rgb, text=caption + ".", return_tensors="pt").to(self.device)
            outputs = self.model(**inputs)
            result = self.processor.post_process_grounded_object_detection(
                outputs, input_ids=inputs.input_ids, threshold=self.box_threshold,
                text_threshold=self.text_threshold, target_sizes=[(height, width)],
            )[0]
            boxes.extend(result["boxes"].detach().cpu().tolist())
            scores.extend(result["scores"].detach().cpu().tolist())
            classes.extend([CLASS_NAMES.index(name)] * len(result["boxes"]))
        if not boxes:
            return sv.Detections.empty()
        return sv.Detections(xyxy=np.array(boxes, dtype=np.float32),
                             confidence=np.array(scores, dtype=np.float32),
                             class_id=np.array(classes, dtype=np.int64))


def clean_proposals(raw: sv.Detections, width: int, height: int) -> tuple[sv.Detections, list[str]]:
    """Validate geometry; flag semantic uncertainty instead of inventing labels."""
    flags = ["front_side_coverage_and_rear_exclusion_require_review"]
    if len(raw) == 0:
        return raw, flags + ["empty_prediction_is_not_an_approved_null"]
    boxes = torch.as_tensor(raw.xyxy, dtype=torch.float32).clone()
    scores = torch.as_tensor(raw.confidence, dtype=torch.float32)
    ids = torch.as_tensor(raw.class_id, dtype=torch.int64)
    finite_boxes = torch.isfinite(boxes).all(1)
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clamp(0, width)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clamp(0, height)
    valid = (finite_boxes & torch.isfinite(scores)
             & (scores >= 0) & (scores <= 1) & (ids >= 0) & (ids < len(CLASS_NAMES))
             & (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1]))
    if not valid.all():
        flags.append("invalid_geometry_or_class_discarded")
    boxes, scores, ids = boxes[valid], scores[valid], ids[valid]
    keep = batched_nms(boxes, scores, ids, .50)  # Preserve nested boxes of different classes.
    boxes, scores, ids = boxes[keep], scores[keep], ids[keep]
    retain = torch.ones(len(boxes), dtype=torch.bool)
    panels = torch.where(ids == 0)[0]
    # Content must be inside a panel. No fixed top/bottom or keyword classification.
    for index in torch.where(ids != 0)[0]:
        if not len(panels):
            retain[index] = False
            flags.append("content_without_panel_requires_review")
            continue
        intersection = (torch.minimum(boxes[panels, 2:], boxes[index, 2:])
                        - torch.maximum(boxes[panels, :2], boxes[index, :2])).clamp_min(0).prod(1)
        area = (boxes[index, 2:] - boxes[index, :2]).prod()
        if (intersection / area).max() < .90:
            retain[index] = False
            flags.append("content_outside_panel_requires_review")
    routes, destinations = torch.where((ids == 2) & retain)[0], torch.where((ids == 3) & retain)[0]
    if len(routes) and len(destinations):
        conflicts = torch.where(box_iou(boxes[routes], boxes[destinations]) >= .65)
        if len(conflicts[0]):
            retain[routes[conflicts[0]]] = False
            retain[destinations[conflicts[1]]] = False
            flags.append("ambiguous_route_destination_candidates_withheld")
    if torch.any((ids == 2) | (ids == 3)):
        flags.append("typography_meaning_arrows_and_line_grouping_require_review")
    if len(panels) and torch.any(((boxes[panels, 2:] - boxes[panels, :2]).prod(1) / (width * height)) > .40):
        flags.append("large_panel_candidate_check_bus_body_confusion")
    result = sv.Detections(xyxy=boxes[retain].numpy(), confidence=scores[retain].numpy(),
                           class_id=ids[retain].numpy())
    if not len(result):
        flags.append("empty_draft_is_not_an_approved_null")
    return result, sorted(set(flags))


def detection_records(detections: sv.Detections) -> list[dict]:
    if not len(detections):
        return []
    return [dict(xyxy=box.tolist(), confidence=float(score), class_id=int(class_id),
                 class_name=CLASS_NAMES[int(class_id)])
            for box, score, class_id in zip(detections.xyxy, detections.confidence, detections.class_id)]


def draw_overlay(bgr: np.ndarray, detections: sv.Detections) -> np.ndarray:
    if not len(detections):
        return bgr.copy()
    labels = [f"{CLASS_NAMES[int(i)]} {float(score):.2f}"
              for i, score in zip(detections.class_id, detections.confidence)]
    image = sv.BoxAnnotator().annotate(bgr.copy(), detections=detections)
    return sv.LabelAnnotator().annotate(image, detections=detections, labels=labels)


def run_experiment(model: LocalGroundingDINO, input_root: Path, run_dir: Path, cutoff="2026-10-24",
                   limit_per_split: int | None = 3, declared_negatives: set[str] | None = None) -> Path:
    """Write draft COCO under an isolated, mirrored data/labelled directory."""
    input_root, run_dir = Path(input_root).resolve(), Path(run_dir).resolve()
    allowed = (EXPERIMENT / "outputs").resolve()
    if run_dir == allowed or not run_dir.is_relative_to(allowed):
        raise ValueError("Run output must be a new subdirectory of this experiment's outputs/")
    if run_dir.exists():
        raise FileExistsError(f"Choose a new run name; refusing to overwrite {run_dir}")
    if not cutoff or Path(cutoff).name != cutoff or cutoff in {".", ".."}:
        raise ValueError("Cutoff must be a single directory name")
    inputs = discover_images(input_root, limit_per_split)
    negative_keys = set(declared_negatives or ())
    available = {path.relative_to(input_root).as_posix() for paths in inputs.values() for path in paths}
    if negative_keys - available:
        raise ValueError("Declared negative paths must belong to the selected input images")
    guide = ROOT / "docs/annotation/guide.md"
    guide_before = sha256(guide)
    source_hashes, review, raw_predictions, counts = {}, [], {}, {}
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".draft-", dir=run_dir.parent) as temporary:
        staging = Path(temporary).resolve()
        if not staging.is_relative_to(allowed):
            raise ValueError("Unexpected staging location")
        for split, paths in inputs.items():
            folder = staging / "data/labelled" / cutoff / split
            folder.mkdir(parents=True)
            coco = dict(info=dict(description="UNREVIEWED Autodistill EDS draft", guide_sha256=sha256(guide)),
                        images=[], annotations=[], categories=[dict(id=i, name=name) for i, name in enumerate(CLASS_NAMES)])
            for image_id, path in enumerate(paths, start=1):
                key = path.relative_to(input_root).as_posix()
                source_hashes[key] = sha256(path)
                bgr = read_bgr(path)
                height, width = bgr.shape[:2]
                # Canonical PNGs retain source resolution and resolve EXIF/codec ambiguities.
                name = f"{image_id:06d}_{path.stem}__{source_hashes[key][:8]}.png"
                if key in negative_keys:
                    raw = cleaned = sv.Detections.empty()
                    flags, status = ["explicitly_declared_negative"], "declared_null"
                else:
                    raw = model.predict(bgr)
                    cleaned, flags = clean_proposals(raw, width, height)
                    status = "needs_review" if len(cleaned) else "needs_review_empty"
                write_png(folder / name, bgr)  # Actual dataset images never contain drawn boxes.
                coco["images"].append(dict(id=image_id, file_name=name, width=width, height=height,
                                           source_file=key, review_status=status, null_declared=key in negative_keys))
                for record in detection_records(cleaned):
                    x1, y1, x2, y2 = record["xyxy"]
                    coco["annotations"].append(dict(id=len(coco["annotations"]) + 1, image_id=image_id,
                        category_id=record["class_id"], bbox=[x1, y1, x2-x1, y2-y1],
                        area=(x2-x1)*(y2-y1), iscrowd=0, segmentation=[],
                        score=record["confidence"], review_status="draft"))
                write_png(staging / "overlays" / split / f"{Path(name).stem}__raw.png", draw_overlay(bgr, raw))
                write_png(staging / "overlays" / split / f"{Path(name).stem}__draft.png", draw_overlay(bgr, cleaned))
                raw_predictions[key] = detection_records(raw)
                review.append(dict(source_file=key, output_file=f"data/labelled/{cutoff}/{split}/{name}",
                                   raw_boxes=len(raw), draft_boxes=len(cleaned), status=status, flags=flags))
            (folder / "_annotations.coco.json").write_text(json.dumps(coco, indent=2), encoding="utf-8")
            counts[split] = dict(images=len(coco["images"]), boxes=len(coco["annotations"]))
        if any(sha256(input_root / key) != value for key, value in source_hashes.items()):
            raise RuntimeError("An input changed during inference; output was not accepted")
        if sha256(guide) != guide_before:
            raise RuntimeError("Annotation guide changed during the experiment")
        manifest = dict(status="draft_requires_review", created_utc=datetime.now(timezone.utc).isoformat(),
                        model_id=model.model_id, model_revision=getattr(model.model.config, "_commit_hash", model.revision),
                        guide_sha256=sha256(guide), captions=CAPTIONS, class_ids=dict(enumerate(CLASS_NAMES)),
                        source_hashes=source_hashes, counts=counts,
                        box_threshold=model.box_threshold, text_threshold=model.text_threshold)
        for filename, content in [("run_manifest.json", manifest), ("review_queue.json", review),
                                  ("raw_predictions.json", raw_predictions)]:
            (staging / filename).write_text(json.dumps(content, indent=2), encoding="utf-8")
        if run_dir.exists():
            raise FileExistsError(run_dir)
        staging.rename(run_dir)
    return run_dir
