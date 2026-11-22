"""Verify frozen export files and expose original/augmented image provenance."""
import json
from pathlib import Path

from .images import file_hash


def verify_export(root):
    root = Path(root).resolve()
    manifests = [root / name for name in ("augmentation_manifest.json", "preparation_manifest.json")
                 if (root / name).is_file()]
    if len(manifests) > 1:
        raise ValueError("Ambiguous dataset export manifests")
    if not manifests:
        return None
    path = manifests[0]
    saved = json.loads(path.read_text(encoding="utf-8"))
    checksums = saved.get("checksums")
    if not isinstance(checksums, dict) or not checksums:
        raise ValueError("Export manifest must contain file checksums")
    for name in checksums:
        target = (root / name).resolve()
        if not target.is_relative_to(root) or target == path or target == root:
            raise ValueError("Invalid export checksum path")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != path}
    if actual != set(checksums):
        raise ValueError("Export file list changed; restore the frozen dataset")
    for name, digest in checksums.items():
        if file_hash(root / name) != digest:
            raise ValueError(f"Export checksum mismatch: {name}")
    return saved


def training_variants(manifest, filenames):
    """Require exactly one provenance record for every augmented-export image."""
    if manifest is None or "training_provenance" not in manifest:
        if manifest is not None and manifest.get("spec", {}).get("recipe", "").startswith("eds-torchvision"):
            raise ValueError("Augmented export is missing training provenance")
        return {name: 0 for name in filenames}
    records = manifest["training_provenance"]
    variants = {}
    for record in records:
        name, variant = record["output"], record["variant"]
        if name in variants or type(variant) is not int or variant < 0:
            raise ValueError("Invalid or duplicate training provenance")
        variants[name] = variant
    if set(variants) != set(filenames):
        raise ValueError("Training provenance does not match exported images")
    return variants
