"""Inspect, deduplicate, group related images, and freeze split copies."""
from pathlib import Path
from collections import defaultdict
import csv
import json
import shutil
import math
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from scipy.sparse.csgraph import connected_components
from .config import IMAGE_EXTENSIONS, EXCLUDED_PREFIXES
from .images import file_hash, image_info


def inspect_raw(raw, excluded_prefixes=EXCLUDED_PREFIXES):
    raw = Path(raw)
    inventory, corrupt = [], []
    for path in sorted(raw.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if any(part.startswith("splits") for part in path.relative_to(raw).parts[:-1]):
            continue  # Never rediscover generated split copies as raw originals.
        try:
            inventory.append(dict(source=path.relative_to(raw).as_posix(),
                                  sha256=file_hash(path), **image_info(path)))
        except Exception as error:
            corrupt.append({"source": path.name, "error": str(error)})
    if corrupt:
        raise ValueError(f"Unreadable raw images: {corrupt}")
    if not inventory:
        raise ValueError(f"No raw images: {raw}")
    excluded_raw = [r for r in inventory if Path(r["source"]).name.lower().startswith(excluded_prefixes)]
    by_pixels = defaultdict(list)
    for row in inventory:
        if row not in excluded_raw:
            by_pixels[row["pixel_hash"]].append(row)
    unique_raw = [dict(rows[0], aliases=[r["source"] for r in rows]) for rows in by_pixels.values()]
    return inventory, unique_raw, excluded_raw

def make_split_plan(rows,ratios,seed,group_csv=None):
    rows = sorted(rows,key=lambda row:row["pixel_hash"])
    # Similarity edges and optional capture IDs form indivisible groups.
    bits = np.array([[(r["dhash"] >> bit)&1 for bit in range(64)] for r in rows])
    distances = np.count_nonzero(bits[:,None,:] != bits[None,:,:],axis=2)
    adjacency = distances <= 4
    if group_csv is not None and Path(group_csv).exists():
        lookup = {name:index for index,row in enumerate(rows) for name in row["aliases"]}
        capture_groups = defaultdict(list)
        with Path(group_csv).open(encoding="utf-8-sig",newline="") as stream:
            for record in csv.DictReader(stream):
                if record["source"] not in lookup or not record["group"].strip():
                    raise ValueError(f"Invalid capture group: {record}")
                capture_groups[record["group"]].append(lookup[record["source"]])
        for indices in capture_groups.values():
            adjacency[np.ix_(indices,indices)] = True
    _,groups = connected_components(adjacency,directed=False)
    indices = np.arange(len(rows))
    if len(np.unique(groups)) < 3:
        raise ValueError("At least three independent groups are required")
    # GroupShuffleSplit proportions refer to groups; image counts are approximate.
    first = GroupShuffleSplit(n_splits=1,test_size=ratios["valid"]+ratios["test"],random_state=seed)
    train,remainder = next(first.split(indices,groups=groups))
    second = GroupShuffleSplit(n_splits=1,test_size=ratios["test"]/(ratios["valid"]+ratios["test"]),random_state=seed+1)
    valid_local,test_local = next(second.split(remainder,groups=groups[remainder]))
    partitions = dict(train=train,valid=remainder[valid_local],test=remainder[test_local])
    plan = []
    for split,members in partitions.items():
        for index in members:
            row = rows[int(index)]
            plan.append(dict(row,group=int(groups[index]),split=split,
                             upload_name=row["pixel_hash"][:24]+Path(row["source"]).suffix.lower()))
    return plan

def write_raw_split(plan, destination, *, raw, inventory, seed, ratios):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(Path(raw).resolve()):
        raise ValueError("Split output must be inside this raw cutoff")
    manifest = dict(seed=seed, ratios=ratios, raw_inventory=inventory, images=plan)
    manifest_path = destination / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Frozen split changed; choose a new RAW_SPLITS directory")
    expected = {Path(r["split"])/r["upload_name"] for r in plan}
    if destination.exists():
        actual = {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()
                  and p != manifest_path}
        if actual - expected:
            raise ValueError("Unexpected files in split output; choose an empty directory")
    for row in plan:
        source = Path(raw) / row["source"]
        target = destination / row["split"] / row["upload_name"]
        if file_hash(source) != row["sha256"]:
            raise ValueError(f"Changed source: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and file_hash(target) != row["sha256"]:
            raise ValueError(f"Refusing to overwrite: {target}")
        if not target.exists():
            shutil.copy2(source, target)
        if file_hash(target) != row["sha256"]:
            raise ValueError(f"Copy failed: {target}")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
