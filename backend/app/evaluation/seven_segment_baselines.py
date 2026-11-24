"""Crop-level baselines for the separate seven-segment reading dataset."""

from pathlib import Path
import csv
import io
import json
import shutil
import subprocess

import numpy as np
from PIL import Image


ALPHABET = "0123456789.+-"
TEMPLATE_NAMES = {"dot": ".", "plus": "+", "minus": "-"}


def _foreground(image: Image.Image) -> np.ndarray:
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    threshold = (int(gray.min()) + int(gray.max())) / 2
    border = np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))
    return gray < threshold if np.median(border) > threshold else gray > threshold


def _standard_mask(mask: np.ndarray, *, width: int = 32, height: int = 64) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return np.zeros((height, width), dtype=np.uint8)
    tight = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    scale = min((width - 4) / tight.shape[1], (height - 4) / tight.shape[0])
    size = (max(1, round(tight.shape[1] * scale)), max(1, round(tight.shape[0] * scale)))
    resized = Image.fromarray(tight.astype(np.uint8) * 255).resize(size, Image.Resampling.NEAREST)
    output = np.zeros((height, width), dtype=np.uint8)
    left, top = (width - size[0]) // 2, (height - size[1]) // 2
    output[top:top + size[1], left:left + size[0]] = np.asarray(resized)
    return output


def _similarity(left: np.ndarray, right: np.ndarray) -> float:
    try:
        import cv2
    except ImportError:
        a, b = left.astype(float).ravel(), right.astype(float).ravel()
        divisor = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / divisor) if divisor else 0.0
    return float(cv2.matchTemplate(left, right, cv2.TM_CCORR_NORMED)[0, 0])


class TemplateBaseline:
    """Projection-split glyphs matched against templates from training only."""

    model_id = "segment_template_v1"
    device = "cpu"

    def __init__(self, template_dir: Path, *, training_sample_ids: set[str] | None = None):
        self.templates = {}
        if training_sample_ids is None:
            sources = [(TEMPLATE_NAMES.get(path.stem, path.stem), path)
                       for path in sorted(template_dir.glob("*.png"))]
        else:
            manifest_path = template_dir / "templates.json"
            if not manifest_path.is_file():
                raise ValueError("Training-only templates.json is required for evaluation.")
            entries = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list) or not entries:
                raise ValueError("templates.json must contain glyph/source records.")
            sources = []
            for item in entries:
                if item.get("source_sample_id") not in training_sample_ids:
                    raise ValueError(f"Template {item.get('glyph')!r} is not sourced from training.")
                filename = item.get("file", "")
                path = (template_dir / filename).resolve()
                if path.parent != template_dir.resolve() or path.suffix.lower() != ".png" or not path.is_file():
                    raise ValueError(f"Invalid template file: {filename!r}")
                sources.append((item.get("glyph"), path))
        for char, path in sources:
            if char not in ALPHABET or char in self.templates:
                raise ValueError(f"Unexpected or repeated glyph template: {path.name}")
            with Image.open(path) as image:
                self.templates[char] = _standard_mask(_foreground(image))
        if not self.templates:
            raise ValueError("Template directory needs at least one training-only glyph PNG.")

    def predict(self, crop_path: Path) -> tuple[str, float]:
        with Image.open(crop_path) as image:
            foreground = _foreground(image)
        columns = np.flatnonzero(foreground.any(axis=0))
        if not len(columns):
            return "", 0.0
        starts = [int(columns[0])]
        ends = []
        for previous, current in zip(columns, columns[1:]):
            if current > previous + 1:
                ends.append(int(previous) + 1)
                starts.append(int(current))
        ends.append(int(columns[-1]) + 1)
        chars, scores = [], []
        for left, right in zip(starts, ends):
            glyph = _standard_mask(foreground[:, left:right])
            score, char = max(((_similarity(glyph, template), char)
                               for char, template in self.templates.items()))
            chars.append(char)
            scores.append(score)
        return "".join(chars), float(sum(scores) / len(scores))


class TesseractBaseline:
    model_id = "tesseract_eng_lstm_psm7"
    device = "cpu"

    def __init__(self):
        self.executable = shutil.which("tesseract")
        if not self.executable:
            raise RuntimeError("Tesseract is not installed.")

    def predict(self, crop_path: Path) -> tuple[str, float]:
        command = [self.executable, str(crop_path), "stdout", "-l", "eng", "--oem", "1", "--psm", "7",
                   "-c", f"tessedit_char_whitelist={ALPHABET}", "tsv"]
        output = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30).stdout
        words = [row for row in csv.DictReader(io.StringIO(output), delimiter="\t")
                 if row.get("text", "").strip() and float(row.get("conf", -1)) >= 0]
        raw = "".join(row["text"] for row in words)
        length = sum(len(row["text"]) for row in words)
        confidence = sum(len(row["text"]) * float(row["conf"]) for row in words) / (100 * length) if length else 0.0
        return raw, confidence


class EasyOCRBaseline:
    model_id = "easyocr_en_pretrained"

    def __init__(self, *, device: str):
        if device not in {"cpu", "cuda", "mps"}:
            raise ValueError("EasyOCR device must be cpu, cuda or mps.")
        import easyocr
        self.reader = easyocr.Reader(["en"], gpu=False if device == "cpu" else device,
                                     detector=False, verbose=False)
        self.device = device

    def predict(self, crop_path: Path) -> tuple[str, float]:
        with Image.open(crop_path) as image:
            rgb = np.asarray(image.convert("RGB"))
        height, width = rgb.shape[:2]
        lines = self.reader.recognize(rgb, horizontal_list=[[0, width, 0, height]], free_list=[],
                                      detail=1, allowlist=ALPHABET)
        if not lines:
            return "", 0.0
        raw = "".join(item[1] for item in lines)
        length = sum(len(item[1]) for item in lines)
        confidence = sum(len(item[1]) * float(item[2]) for item in lines) / length if length else 0.0
        return raw, confidence
