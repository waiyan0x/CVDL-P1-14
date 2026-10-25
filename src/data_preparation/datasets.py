"""Load and validate split COCO images, categories, geometry, and leakage."""
from pathlib import Path
from collections import defaultdict
from itertools import combinations
import json
import math
import torch
from torch.utils.data import Dataset
from PIL import Image as PillowImage
from .config import SPLITS, TRAINING_DATASET
from .images import image_info
from .preprocessing import model_input

def split_folder(root, split):
    choices = [Path(root)/split]
    if split == "valid":
        choices.append(Path(root)/"val")
    present = [p for p in choices if (p/"_annotations.coco.json").exists()]
    if len(present) != 1:
        raise ValueError(f"Expected one {split} folder with _annotations.coco.json: {root}")
    return present[0]

def load_coco_splits(root=TRAINING_DATASET):
    """Load a complete COCO export; default to the configured final training version."""
    datasets, categories, seen_pixels = {}, None, {}
    for split in SPLITS:
        folder = split_folder(root, split)
        data = json.loads((folder/"_annotations.coco.json").read_text(encoding="utf-8"))
        images = {image["id"]: image for image in data["images"]}
        classes = {c["id"]: c["name"] for c in data["categories"]}
        if len(images) != len(data["images"]) or len(classes) != len(data["categories"]):
            raise ValueError("Duplicate COCO image/category IDs")
        if categories is not None and categories != classes:
            raise ValueError("Category IDs/names differ across splits")
        categories = classes
        annotations, annotation_ids = defaultdict(list), set()
        for annotation in data["annotations"]:
            if annotation["id"] in annotation_ids:
                raise ValueError("Duplicate COCO annotation ID")
            annotation_ids.add(annotation["id"])
            image = images.get(annotation["image_id"])
            if image is None or annotation["category_id"] not in classes:
                raise ValueError("Unknown annotation image/category")
            if annotation.get("segmentation") or annotation.get("iscrowd", 0):
                raise ValueError("This pipeline supports bounding boxes, not masks or crowd regions")
            x,y,w,h = annotation["bbox"]
            if not all(math.isfinite(v) for v in (x,y,w,h)) or min(w,h) <= 0:
                raise ValueError("Invalid bounding box")
            if min(x,y) < -0.01 or x+w > image["width"]+.01 or y+h > image["height"]+.01:
                raise ValueError(f"Box outside image: {image['file_name']}")
            annotations[image["id"]].append(annotation)
        filenames, rows = set(), []
        for image in images.values():
            path = (folder/image["file_name"]).resolve()
            if not path.is_relative_to(folder.resolve()) or path.name == "_annotations.coco.json":
                raise ValueError("Invalid COCO image path")
            if image["file_name"] in filenames:
                raise ValueError("Two COCO image records reference the same filename")
            filenames.add(image["file_name"])
            with PillowImage.open(path) as opened:
                if opened.getexif().get(274, 1) != 1:
                    raise ValueError(f"Resolve EXIF orientation and boxes before export: {path}")
            info = image_info(path)
            if (info["width"],info["height"]) != (image["width"],image["height"]):
                raise ValueError(f"COCO dimensions differ from image: {path}")
            previous = seen_pixels.get(info["pixel_hash"])
            if previous is not None and previous != split:
                raise ValueError(f"Exact image duplicated across {previous}/{split}: {path.name}")
            seen_pixels[info["pixel_hash"]] = split
            rows.append(dict(image=image, path=path, annotations=annotations[image["id"]], **info))
        datasets[split] = dict(folder=folder, data=data, rows=rows)
    return datasets

def dataset_summary(datasets):
    return [dict(split=split, images=len(data["rows"]),
                 boxes=len(data["data"]["annotations"]),
                 negative_images=sum(not row["annotations"] for row in data["rows"]))
            for split, data in datasets.items()]

def find_cross_split_pairs(datasets, max_distance=4):
    """Flag similar scenes for review without moving any images."""
    return [[a_split, a["path"].name, b_split, b["path"].name]
            for a_split, b_split in combinations(datasets, 2)
            for a in datasets[a_split]["rows"] for b in datasets[b_split]["rows"]
            if (a["dhash"] ^ b["dhash"]).bit_count() <= max_distance]


class DetectionDataset(Dataset):
    def __init__(self,dataset,target_size=None,mean=None,std=None):
        self.rows = dataset["rows"]
        self.target_size,self.mean,self.std = target_size,mean,std

    def __len__(self):
        return len(self.rows)

    def __getitem__(self,index):
        row = self.rows[index]
        sample = model_input(row,self.target_size,self.mean,self.std)
        target = {"boxes":sample["boxes"],"labels":sample["labels"],
                  "image_id":torch.tensor(row["image"]["id"])}
        return sample["image"],target

def detection_collate(batch):
    return tuple(zip(*batch))
