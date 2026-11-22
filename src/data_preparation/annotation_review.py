"""Offline draft checks, persisted human decisions, and reviewed COCO export.

No detector confidence or file check is treated as a semantic approval.
This module deliberately uses only the Python standard library.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from .config import ROOT

CLASSES = ("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")
STATUSES = {"needs_review", "accepted_positive", "accepted_negative"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def checked_path(folder, name):
    path = (folder / name).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError(f"Missing image or image outside split folder: {name}")
    return path


def validate_boxes(boxes, image, categories):
    """Validate submitted geometry without mistaking it for visual review."""
    if not isinstance(boxes, list):
        raise ValueError("Boxes must be a list")
    result = []
    for box in boxes:
        if not isinstance(box, dict) or box.get("category_id") not in categories:
            raise ValueError("Unknown box class")
        bbox = box.get("bbox")
        if (not isinstance(bbox, list) or len(bbox) != 4
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) for v in bbox)):
            raise ValueError("Each box needs four finite numbers: x, y, width, height")
        x, y, w, h = bbox
        if (min(x, y) < 0 or min(w, h) <= 0
                or x + w > image["width"] + .01 or y + h > image["height"] + .01):
            raise ValueError("Box must have positive size and remain inside the image")
        result.append(dict(category_id=box["category_id"], bbox=list(bbox)))
    return result


def overlap(first, second):
    x, y, w, h = first
    a, b, c, d = second
    return max(0, min(x+w, a+c)-max(x, a)) * max(0, min(y+h, b+d)-max(y, b))


def check_annotations(boxes, image, categories):
    issues = []
    try:
        validate_boxes(boxes, image, categories)
    except ValueError as error:
        return [str(error)]
    panels = [b for b in boxes if categories[b["category_id"]] == "front_eds"]
    if not boxes:
        return ["No boxes: confirm no front/side EDS was missed before accepting as negative."]
    if not panels:
        issues.append("Content detected without an enclosing EDS panel.")
    for index, box in enumerate(boxes):
        name = categories[box["category_id"]]
        x, y, w, h = box["bbox"]
        if name != "front_eds" and not any(
                overlap(box["bbox"], panel["bbox"]) / (w*h) >= .90 for panel in panels):
            issues.append(f"Box {index+1}: content is not contained in a panel.")
        if name == "front_eds" and w*h > .4*image["width"]*image["height"]:
            issues.append(f"Box {index+1}: unusually large panel; check bus-body confusion.")
        if box.get("score", 1) < .5:
            issues.append(f"Box {index+1}: detector confidence below 0.50; heuristic only.")
        for other in boxes[:index]:
            intersection = overlap(box["bbox"], other["bbox"])
            union = w*h + other["bbox"][2]*other["bbox"][3] - intersection
            iou = intersection/union if union else 0
            if box["category_id"] == other["category_id"] and iou >= .5:
                issues.append(f"Box {index+1}: possible duplicate of another box.")
            if {name, categories[other["category_id"]]} == {"front_eds_route", "front_eds_destination"} and iou >= .65:
                issues.append("Overlapping route/destination boxes need a class check.")
    return list(dict.fromkeys(issues))


class ReviewProject:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir).resolve()
        labelled = self.run_dir / "data/labelled"
        batches = sorted(p for p in labelled.iterdir() if p.is_dir()) if labelled.exists() else []
        if len(batches) != 1:
            raise ValueError("Expected one batch under RUN/data/labelled/")
        self.source, self.cutoff = batches[0], batches[0].name
        self.datasets, self.records, self.hashes = {}, {}, {}
        expected_categories = None
        for split, aliases in (("train", ("train",)), ("val", ("val", "valid", "validation")), ("test", ("test",))):
            folders = [self.source / name for name in aliases if (self.source / name / "_annotations.coco.json").is_file()]
            if len(folders) != 1:
                raise ValueError(f"Expected one COCO folder for {split}")
            folder = folders[0]
            label = folder / "_annotations.coco.json"
            data = json.loads(label.read_text(encoding="utf-8"))
            categories = {c["id"]: c["name"] for c in data["categories"]}
            if len(categories) != len(data["categories"]) or len(categories) != len(CLASSES) or set(categories.values()) != set(CLASSES):
                raise ValueError("Expected exactly the four EDS classes with unique IDs")
            if expected_categories is not None and categories != expected_categories:
                raise ValueError("Class mappings differ across splits")
            expected_categories = categories
            image_ids = [i["id"] for i in data["images"]]
            if not image_ids or len(set(image_ids)) != len(image_ids):
                raise ValueError("Each split needs images with unique IDs")
            annotation_ids = [a["id"] for a in data["annotations"]]
            if len(set(annotation_ids)) != len(annotation_ids):
                raise ValueError("Duplicate annotation IDs")
            if any(a["image_id"] not in image_ids for a in data["annotations"]):
                raise ValueError("Annotation references an unknown image")
            if any(a.get("segmentation") or a.get("iscrowd", 0) for a in data["annotations"]):
                raise ValueError("The review editor supports bounding boxes, not masks or crowd regions")
            filenames = set()
            for image in data["images"]:
                if image["file_name"] in filenames:
                    raise ValueError("Duplicate image filename")
                filenames.add(image["file_name"])
                path = checked_path(folder, image["file_name"])
                if min(image["width"], image["height"]) <= 0:
                    raise ValueError("Image dimensions must be positive")
                key = f"{split}/{image['id']}"
                self.records[key] = dict(key=key, split=split, image=image, path=path,
                                         boxes=[a for a in data["annotations"] if a["image_id"] == image["id"]])
                self.hashes[path.relative_to(self.run_dir).as_posix()] = digest(path)
            self.hashes[label.relative_to(self.run_dir).as_posix()] = digest(label)
            self.datasets[split] = data
        self.categories = expected_categories
        self.decisions_path = self.run_dir / "review_decisions.json"
        saved = json.loads(self.decisions_path.read_text(encoding="utf-8")) if self.decisions_path.exists() else {}
        if saved and saved.get("source_hashes") != self.hashes:
            raise ValueError("Draft files changed since review; restore them or start a new run")
        self.decisions = saved.get("decisions", {})
        if set(self.decisions) - self.records.keys():
            raise ValueError("Review references unknown images")
        for key, decision in self.decisions.items():
            self.validate_decision(key, decision)

    def assert_unchanged(self):
        for name, checksum in self.hashes.items():
            if digest(self.run_dir / name) != checksum:
                raise ValueError("Draft files changed; reload and review the current files")

    def validate_decision(self, key, decision):
        if key not in self.records:
            raise ValueError("Unknown image")
        if decision.get("status") not in STATUSES:
            raise ValueError("Unknown review status")
        if not isinstance(decision.get("note", ""), str):
            raise ValueError("Review note must be text")
        boxes = validate_boxes(decision.get("boxes"), self.records[key]["image"], self.categories)
        if decision["status"] == "accepted_negative" and boxes:
            raise ValueError("A confirmed negative must have zero boxes; remove them first")
        if decision["status"] == "accepted_positive" and not any(
                self.categories[b["category_id"]] == "front_eds" for b in boxes):
            raise ValueError("A positive needs at least one front/side EDS panel box")
        return dict(status=decision["status"], boxes=boxes, note=decision.get("note", ""))

    def save(self, key, decision):
        accepted = self.validate_decision(key, decision)
        self.assert_unchanged()
        self.decisions[key] = accepted
        write_json(self.decisions_path, dict(source_hashes=self.hashes, decisions=self.decisions))
        self.write_report()

    def report(self):
        rows = []
        for key, record in self.records.items():
            decision = self.decisions.get(key, {})
            boxes = decision.get("boxes", record["boxes"])
            issues = check_annotations(boxes, record["image"], self.categories)
            rows.append(dict(key=key, split=record["split"], image=record["image"], boxes=boxes,
                             status=decision.get("status", "needs_review"), note=decision.get("note", ""),
                             automatic_issues=issues, candidate="positive" if boxes else "unknown_empty"))
        return dict(cutoff=self.cutoff, categories=self.categories,
                    semantic_review="Human visual confirmation required; automatic checks do not certify front/side coverage or true negatives.",
                    summary=dict(images=len(rows), statuses=dict(Counter(r["status"] for r in rows)),
                                 flagged=sum(bool(r["automatic_issues"]) for r in rows)), rows=rows)

    def write_report(self):
        report = self.report()
        write_json(self.run_dir / "automatic_review.json", report)
        return report

    def export(self, output, *, root=ROOT):
        output = Path(output).resolve()
        allowed = (Path(root) / "data/labelled").resolve()
        if output == allowed or not output.is_relative_to(allowed):
            raise ValueError("Reviewed export must be a version folder under data/labelled/")
        if output.exists():
            raise FileExistsError("Reviewed output already exists; choose a new version")
        if self.run_dir.is_relative_to(output) or output.is_relative_to(self.run_dir):
            raise ValueError("Reviewed output must be separate from the draft run")
        pending = [key for key in self.records if self.decisions.get(key, {}).get("status") not in
                   {"accepted_positive", "accepted_negative"}]
        if pending:
            raise ValueError(f"Review all images before export: {len(pending)} still pending")
        self.assert_unchanged()
        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".reviewed-", dir=output.parent) as temporary:
            staging = Path(temporary)
            for split, data in self.datasets.items():
                folder = staging / split
                folder.mkdir()
                coco = deepcopy(data)
                coco["info"] = dict(coco.get("info", {}), description="Human-reviewed EDS annotations")
                coco["annotations"] = []
                for image in coco["images"]:
                    key = f"{split}/{image['id']}"
                    decision = self.validate_decision(key, self.decisions[key])
                    image.update(review_status="accepted", review_method="human_visual",
                                 null_declared=decision["status"] == "accepted_negative")
                    destination = folder / image["file_name"]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(self.records[key]["path"], destination)
                    for box in decision["boxes"]:
                        coco["annotations"].append(dict(box, id=len(coco["annotations"])+1,
                            image_id=image["id"], area=box["bbox"][2]*box["bbox"][3],
                            iscrowd=0, segmentation=[], review_status="accepted"))
                write_json(folder / "_annotations.coco.json", coco)
            self.assert_unchanged()
            checksums = {p.relative_to(staging).as_posix(): digest(p) for p in staging.rglob("*") if p.is_file()}
            write_json(staging / "preparation_manifest.json", dict(
                spec=dict(recipe="human-reviewed-annotations-v1", source_hashes=self.hashes,
                          decisions=self.decisions), checksums=checksums))
            if output.exists():
                raise FileExistsError(output)
            staging.rename(output)
        return output
