"""Paired Torchvision image/box transforms and atomic training-only exports."""
from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
import hashlib
import json
import math
import shutil
import cv2
import torch
import torchvision
from torchvision import tv_tensors
from torchvision.transforms import v2, InterpolationMode
from .config import ROOT, AUGMENTATION_REFERENCE
from .images import file_hash, read_rgb, write_rgb
from .datasets import load_coco_splits, find_cross_split_pairs

def augment_sample(image,annotations,seed,settings, *, parameters=None):
    generator = torch.Generator().manual_seed(seed)
    sample = lambda low,high: low+(high-low)*torch.rand((),generator=generator).item()
    angle = sample(-settings["rotation_degrees"],settings["rotation_degrees"])
    brightness = sample(1-settings["brightness"],1+settings["brightness"])
    sigma = sample(0,settings["blur_radius"])
    # Fixed endpoints support read-only visual comparisons through the same transform.
    if parameters is not None:
        if set(parameters) - {"rotation", "brightness", "blur_sigma"}:
            raise ValueError("Unknown augmentation preview parameter")
        angle = parameters.get("rotation", angle)
        brightness = parameters.get("brightness", brightness)
        sigma = parameters.get("blur_sigma", sigma)
        if not (abs(angle) <= settings["rotation_degrees"]
                and 1-settings["brightness"] <= brightness <= 1+settings["brightness"]
                and 0 <= sigma <= settings["blur_radius"]):
            raise ValueError("Preview parameters exceed configured augmentation ranges")
    boxes = tv_tensors.BoundingBoxes(
        torch.tensor([a["bbox"] for a in annotations],dtype=torch.float32).reshape(-1,4),
        format="XYWH",canvas_size=tuple(image.shape[-2:]))
    # Torchvision v2 applies identical geometric transforms to image and boxes.
    # Pad first, then rotate on a fixed canvas to keep image/box canvas sizes identical.
    padding = (math.ceil(max(image.shape[-2:])*math.sin(math.radians(settings["rotation_degrees"])))+2
               if settings["rotation_degrees"] else 0)
    rotation = v2.Compose([v2.Pad(padding,fill=114),
        v2.RandomRotation((angle,angle),interpolation=InterpolationMode.BILINEAR,
                            expand=False,fill={tv_tensors.Image:114})])
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        image,boxes = rotation(image,boxes)
        image = v2.ColorJitter(brightness=(brightness,brightness))(image)
        # Salt/pepper noise: 1% expected pixel rate; modify RGB channels together.
        noise = torch.rand(tuple(image.shape[-2:]),generator=generator)
        image = image.clone()
        image[:,noise < settings["noise_fraction"]/2] = 0
        image[:,noise > 1-settings["noise_fraction"]/2] = 255
        if sigma > 1e-6:
            kernel = min(7,2*((min(image.shape[-2:])-1)//2)+1)
            image = v2.GaussianBlur(kernel_size=kernel,sigma=(sigma,sigma))(image)
    boxes = v2.ClampBoundingBoxes()(boxes)
    result = deepcopy(annotations)
    for annotation,bbox in zip(result,boxes.tolist()):
        annotation.update(bbox=bbox,area=bbox[2]*bbox[3],segmentation=[])
    return image,result,dict(rotation=angle,brightness=brightness,
                              noise_fraction=settings["noise_fraction"],blur_sigma=sigma,padding=padding)

def build_augmented_dataset(datasets, output, settings, seed, excluded_prefixes=(), *, root=ROOT):
    output = Path(output).resolve()
    training_root = (Path(root)/"data/training").resolve()
    if not output.is_relative_to(training_root) or output == training_root:
        raise ValueError("Augmented output must be under data/training")
    if not isinstance(settings["multiplier"],int) or settings["multiplier"] < 1:
        raise ValueError("Multiplier must be an integer >= 1")
    if not (0 <= settings["noise_fraction"] <= 1 and 0 <= settings["brightness"] <= 1
            and 0 <= settings["rotation_degrees"] <= 3 and settings["blur_radius"] >= 0):
        raise ValueError("Invalid augmentation settings")
    inputs = {}
    for split,dataset in datasets.items():
        inputs[f"{split}/_annotations.coco.json"] = file_hash(dataset["folder"]/"_annotations.coco.json")
        for row in dataset["rows"]:
            inputs[f"{split}/{row['image']['file_name']}"] = file_hash(row["path"])
    spec = dict(recipe="eds-torchvision-v1",
                libraries=dict(torch=torch.__version__,torchvision=torchvision.__version__,opencv=cv2.__version__), seed=seed, settings=settings,
                excluded_train_prefixes=list(excluded_prefixes), inputs=inputs,
                reference_sha256=file_hash(Path(root)/AUGMENTATION_REFERENCE))
    manifest_path = output/"augmentation_manifest.json"
    if output.exists():
        if not manifest_path.exists():
            raise FileExistsError(f"Output exists without a manifest: {output}")
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        if saved["spec"] != spec:
            raise ValueError("Source/settings changed; choose a new training dataset version")
        actual = {p.relative_to(output).as_posix() for p in output.rglob("*")
                  if p.is_file() and p != manifest_path}
        if actual != set(saved["checksums"]):
            raise ValueError("Training dataset file list changed")
        if any(file_hash(output/name) != checksum for name,checksum in saved["checksums"].items()):
            raise ValueError("Training dataset files changed; refusing to overwrite")
        return saved
    output.parent.mkdir(parents=True,exist_ok=True)
    # Build in a verified sibling temporary directory; publish only a complete dataset.
    with TemporaryDirectory(prefix=".augmentation-", dir=output.parent) as temporary:
        staging = Path(temporary).resolve()
        if not staging.is_relative_to(training_root):
            raise ValueError("Unexpected staging location")
        provenance, excluded = [], []
        for split,dataset in datasets.items():
            target = staging/split
            target.mkdir()
            if split != "train":
                for row in dataset["rows"]:
                    destination = target/row["image"]["file_name"]
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(row["path"],destination)
                shutil.copy2(dataset["folder"]/"_annotations.coco.json",target/"_annotations.coco.json")
                continue
            coco = deepcopy(dataset["data"])
            coco["images"], coco["annotations"] = [], []
            next_image_id = max((r["image"]["id"] for r in dataset["rows"]),default=-1)+1
            next_annotation_id = max((a["id"] for a in dataset["data"]["annotations"]),default=-1)+1
            used_names = set()
            for row in dataset["rows"]:
                source = row["image"]
                if Path(source["file_name"]).name.lower().startswith(excluded_prefixes):
                    excluded.append(source["file_name"])
                    continue
                destination = target/source["file_name"]
                destination.parent.mkdir(parents=True,exist_ok=True)
                if source["file_name"] in used_names:
                    raise ValueError("Training filename collision")
                used_names.add(source["file_name"])
                shutil.copy2(row["path"],destination)
                coco["images"].append(deepcopy(source))
                coco["annotations"].extend(deepcopy(row["annotations"]))
                provenance.append(dict(output=source["file_name"], source=source["file_name"], variant=0))
                for variant in range(1,settings["multiplier"]):
                    # Per-source seeds are stable even if source iteration order changes.
                    key = f"{seed}:{inputs['train/'+source['file_name']]}:{variant}".encode()
                    variant_seed = int(hashlib.sha256(key).hexdigest()[:16],16)
                    image = read_rgb(row["path"])
                    image, annotations, parameters = augment_sample(image,row["annotations"],variant_seed,settings)
                    name = f"aug_{source['id']}_{variant}_{hashlib.sha256(key).hexdigest()[:12]}.png"
                    if name in used_names:
                        raise ValueError("Augmented filename collision")
                    used_names.add(name)
                    write_rgb(image,target/name)
                    record = deepcopy(source)
                    record.update(id=next_image_id,file_name=name,width=image.shape[-1],height=image.shape[-2])
                    coco["images"].append(record)
                    for annotation in annotations:
                        annotation.update(id=next_annotation_id,image_id=next_image_id)
                        next_annotation_id += 1
                        coco["annotations"].append(annotation)
                    provenance.append(dict(output=name,source=source["file_name"],variant=variant,**parameters))
                    next_image_id += 1
            (target/"_annotations.coco.json").write_text(json.dumps(coco,indent=2),encoding="utf-8")
        # Detect source changes during processing before accepting the output.
        for split,dataset in datasets.items():
            if file_hash(dataset["folder"]/"_annotations.coco.json") != inputs[f"{split}/_annotations.coco.json"]:
                raise ValueError("Source annotations changed during augmentation")
            for row in dataset["rows"]:
                if file_hash(row["path"]) != inputs[f"{split}/{row['image']['file_name']}"]:
                    raise ValueError("Source image changed during augmentation")
        staged = load_coco_splits(staging)
        if find_cross_split_pairs(staged):
            raise ValueError("Augmented images create cross-split similar scenes; review before publishing")
        checksums = {p.relative_to(staging).as_posix():file_hash(p)
                     for p in staging.rglob("*") if p.is_file()}
        manifest = dict(spec=spec,excluded_train_images=excluded,training_provenance=provenance,checksums=checksums)
        (staging/"augmentation_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    return manifest
