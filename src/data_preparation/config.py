"""Shared paths and defaults for standalone phase scripts and visual previews."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = "2026-10-24"
SEED = 42
SPLITS = ("train", "valid", "test")
RATIOS = {"train": .70, "valid": .20, "test": .10}
EXCLUDED_PREFIXES = ("annotated_",)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".tif", ".tiff"}
AUGMENTATION = dict(multiplier=3, brightness=.10, rotation_degrees=3.,
                    noise_fraction=.01, blur_radius=1.)
