"""Read-only category sampling and isolated augmentation comparisons."""
from pathlib import Path
import json
import textwrap
import matplotlib.pyplot as plt
from .config import ROOT, AUGMENTATION, SEED
from .images import file_hash, read_rgb
from .augmentation import augment_sample


def load_examples(path=None, *, root=ROOT):
    """Validate reviewed representative paths and hashes, without reclassifying images."""
    root = Path(root).resolve()
    path = Path(path) if path else root / "data/manifests/2026-10-24-preview-samples.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for sample in [s for group in manifest["categories"] for s in group["samples"]] + manifest["augmentation_samples"]:
        image = (root / sample["path"]).resolve()
        if not image.is_relative_to(root / "data"):
            raise ValueError(f"Sample outside local data: {image}")
        if not image.is_file():
            raise FileNotFoundError(f"Restore the local snapshot image: {sample['path']}")
        if file_hash(image) != sample["sha256"]:
            raise ValueError(f"Sample changed since review: {sample['path']}")
    return manifest


def _rgb(image):
    return image.detach().cpu().permute(1, 2, 0).contiguous().numpy()


def plot_category(group, *, root=ROOT):
    """One row of three hand-reviewed examples; categories can overlap."""
    samples = group["samples"]
    figure, axes = plt.subplots(1, len(samples), figsize=(15, 5.8), squeeze=False,
                                layout="constrained")
    figure.suptitle(group["name"], fontsize=17, fontweight="bold")
    for axis, sample in zip(axes.flat, samples):
        image = read_rgb(Path(root) / sample["path"])
        axis.imshow(_rgb(image), interpolation="nearest")
        axis.set_title(textwrap.fill(sample["observation"], 42), fontsize=11)
        axis.set_xlabel(textwrap.fill(Path(sample["path"]).name, 45), fontsize=9)
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_visible(False)
    return figure


def augmentation_cases(settings=AUGMENTATION):
    """Fixed endpoints expose each enabled transform; exported variants remain random combinations."""
    disabled = dict(settings, brightness=0., rotation_degrees=0., noise_fraction=0., blur_radius=0.)
    return [
        ("Brightness", dict(disabled, brightness=settings['brightness']),
         dict(brightness=1-settings['brightness']), f"factor {1-settings['brightness']:.2f}"),
        ("Rotation", dict(disabled, rotation_degrees=settings['rotation_degrees']),
         dict(rotation=settings['rotation_degrees']), f"+{settings['rotation_degrees']:g} degrees"),
        ("Salt/pepper noise", dict(disabled, noise_fraction=settings['noise_fraction']),
         {}, f"{100*settings['noise_fraction']:g}% expected pixel rate"),
        ("Gaussian blur", dict(disabled, blur_radius=settings['blur_radius']),
         dict(blur_sigma=settings['blur_radius']), f"sigma {settings['blur_radius']:g} px"),
    ]


def plot_augmentation(name, rows, settings, parameters, description, *, seed=SEED):
    """One whole-image before/after pair per sample, without cropping or box overlays."""
    if not rows:
        raise ValueError("Select at least one original training example")
    figure, axes = plt.subplots(len(rows), 2, figsize=(12, 4.4*len(rows)), squeeze=False,
                                layout="constrained")
    figure.suptitle(f"{name}: {description}\nWhole original training images", fontsize=15)
    for index, row in enumerate(rows):
        image = read_rgb(row['path'])
        transformed, _, _ = augment_sample(image, row['annotations'], seed+index,
                                                     settings, parameters=parameters)
        for axis, pixels in ((axes[index, 0], image), (axes[index, 1], transformed)):
            axis.imshow(_rgb(pixels), interpolation="nearest")
            axis.axis('off')
        caption = textwrap.fill(Path(row['image']['file_name']).name.split('_jpg.rf.')[0], 50)
        axes[index, 0].set_title(f"Before | {caption}", fontsize=10)
        axes[index, 1].set_title(f"After | {description}", fontsize=10)
    return figure
