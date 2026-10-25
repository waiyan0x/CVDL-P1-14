"""Audit accepted labels and create a versioned export from reviewed exclusions."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from .datasets import dataset_summary, find_cross_split_pairs, load_coco_splits
from .images import file_hash

CLASS_ORDER = ("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")


def audit_labels(datasets):
    counts = Counter(a["category_id"] for d in datasets.values() for a in d["data"]["annotations"])
    categories = datasets["train"]["data"]["categories"]
    names = {c["id"]: c["name"] for c in categories}
    pairs = find_cross_split_pairs(datasets)
    marked = [f"{s}/{r['image']['file_name']}" for s, d in datasets.items()
              for r in d["rows"] if Path(r["image"]["file_name"]).name.lower().startswith("annotated_")]
    drafts = [f"{s}/{r['image']['file_name']}" for s, d in datasets.items() for r in d["rows"]
              if r["image"].get("review_status") in {"draft", "needs_review", "needs_review_empty"}]
    unexpected = [names[c] for c in counts if names[c] not in CLASS_ORDER]
    missing = sorted(set(CLASS_ORDER) - set(names.values()))
    mapping = {str(c["id"]): CLASS_ORDER.index(c["name"]) for c in categories if c["name"] in CLASS_ORDER}
    empty = [f"{s}/{r['image']['file_name']}" for s, d in datasets.items()
             for r in d["rows"] if not r["annotations"]]
    return dict(
        structural_checks_passed=True,
        automated_checks_passed=not (pairs or marked or drafts or unexpected or missing),
        # This deliberately does not certify annotation semantics from file checks.
        semantic_review="Use the annotation guide; automated checks cannot verify missed panels or text classes.",
        splits=dataset_summary(datasets), similar_scene_pairs=pairs,
        marked_up_images=marked, unreviewed_drafts=drafts, empty_images=empty,
        unexpected_active_classes=unexpected, missing_classes=missing,
        categories=[dict(c, boxes=counts[c["id"]]) for c in categories],
        category_id_to_training_index=mapping, training_class_order=list(CLASS_ORDER),
        similarity_method="64-bit OpenCV grayscale area-resize dHash, distance <= 4; heuristic only",
    )


def clean_labels(datasets, output, decisions):
    """Drop explicitly reviewed training rows; copy holdouts byte-for-byte."""
    output = Path(output).resolve()
    exclusions = decisions["exclude_train"]
    filenames = [r["file_name"] for r in exclusions]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Duplicate training exclusions")
    rows = {r["image"]["file_name"]: r for r in datasets["train"]["rows"]}
    if set(filenames) - rows.keys():
        raise ValueError("Exclusion is not in training")
    for record in exclusions:
        if file_hash(rows[record["file_name"]]["path"]) != record["sha256"]:
            raise ValueError("Reviewed training image changed")
        split = record["matches_split"]
        if split not in {"valid", "test"}:
            raise ValueError("Exclusions must reference a held-out counterpart")
        counterpart = next((r for r in datasets[split]["rows"]
                            if r["image"]["file_name"] == record["matches_file_name"]), None)
        if counterpart is None or file_hash(counterpart["path"]) != record["matches_sha256"]:
            raise ValueError("Reviewed counterpart missing or changed")
    filtered = deepcopy(datasets)
    filtered["train"]["rows"] = [r for r in datasets["train"]["rows"] if r["image"]["file_name"] not in filenames]
    kept_ids = {r['image']['id'] for r in filtered['train']['rows']}
    filtered['train']['data']['images'] = [im for im in filtered['train']['data']['images'] if im['id'] in kept_ids]
    filtered['train']['data']['annotations'] = [a for a in filtered['train']['data']['annotations'] if a['image_id'] in kept_ids]
    audit = audit_labels(filtered)
    if not audit["automated_checks_passed"]:
        raise ValueError("Unresolved leakage, markup, draft labels or class issues remain")
    inputs = {f"{s}/{r['image']['file_name']}": file_hash(r["path"])
              for s, d in datasets.items() for r in d["rows"]}
    inputs.update({f"{s}/_annotations.coco.json": file_hash(d["folder"] / "_annotations.coco.json")
                   for s, d in datasets.items()})
    spec = dict(recipe="reviewed-training-exclusions-v1", decisions=decisions, inputs=inputs)
    if any(output == d["folder"].resolve().parent or output.is_relative_to(d["folder"].resolve())
           or d["folder"].resolve().is_relative_to(output) for d in datasets.values()):
        raise ValueError("Output must be separate from the accepted input")
    manifest_path = output / "preparation_manifest.json"
    if output.exists():
        if not manifest_path.is_file():
            raise FileExistsError("Output exists without a preparation manifest")
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        if saved["spec"] != spec:
            raise ValueError("Source or decisions changed; choose a new output")
        actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file() and p != manifest_path}
        if actual != set(saved["checksums"]) or any(file_hash(output / n) != h for n, h in saved["checksums"].items()):
            raise ValueError("Cleaned output changed; refusing to overwrite")
        return saved
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".label-cleaning-", dir=output.parent) as temporary:
        stage = Path(temporary)
        for split, dataset in datasets.items():
            target = stage / dataset["folder"].name
            target.mkdir()
            kept = filtered[split]["rows"]
            for row in kept:
                destination = target / row["image"]["file_name"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(row["path"], destination)
            label_path = target / "_annotations.coco.json"
            if split != "train":
                shutil.copy2(dataset["folder"] / label_path.name, label_path)
            else:
                coco = deepcopy(dataset["data"])
                ids = {r["image"]["id"] for r in kept}
                coco["images"] = [im for im in coco["images"] if im["id"] in ids]
                coco["annotations"] = [a for a in coco["annotations"] if a["image_id"] in ids]
                label_path.write_text(json.dumps(coco, indent=2), encoding="utf-8")
        staged_audit = audit_labels(load_coco_splits(stage))
        if not staged_audit["automated_checks_passed"]:
            raise ValueError("Staged export failed readiness checks")
        for split, dataset in datasets.items():
            for key, digest in inputs.items():
                prefix = split + "/"
                if key.startswith(prefix) and file_hash(dataset["folder"] / key[len(prefix):]) != digest:
                    raise ValueError("Source changed while exporting")
        checksums = {p.relative_to(stage).as_posix(): file_hash(p) for p in stage.rglob("*") if p.is_file()}
        saved = dict(spec=spec, audit=staged_audit, checksums=checksums)
        (stage / manifest_path.name).write_text(json.dumps(saved, indent=2), encoding="utf-8")
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    return saved
