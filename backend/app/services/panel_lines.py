"""Split a whole-display (EDS) crop into its text lines so each line can be read on its own.

Recognition models read one line at a time; a two-line display read as a single image comes back garbled
(`TAPIPIS NS AVE 298` for `TAMPINES AVE 3 / TAMPINES AVE 5 298`). The LED text is bright on a dark
panel, so rows that contain text stand out in a horizontal brightness profile. The service-number column
(known from the detector's number box) spans both lines, so it is blanked before the profile is taken and
left out of the line crops.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def split_lines(crop: Image.Image, exclude: list[tuple[int, int, int, int]] | None = None,
                min_height: int = 5, max_lines: int = 3) -> list[Image.Image]:
    """Return line crops (top to bottom). Fewer than two lines found -> [] (caller keeps the whole read).

    exclude: boxes in crop coordinates (x1, y1, x2, y2) to blank first, e.g. the number box.
    """
    grey = np.asarray(crop.convert("L"), dtype=np.float32)
    h, w = grey.shape
    if h < 2 * min_height or w < 20:
        return []
    keep = np.ones(w, dtype=bool)
    for x1, _, x2, _ in exclude or []:
        keep[max(0, int(x1)):min(w, int(x2))] = False
    if keep.sum() < 0.3 * w:
        return []
    area = grey[:, keep]
    # Otsu threshold; text is the minority class (bright LEDs on a dark panel, or the reverse under glare).
    hist, _ = np.histogram(area, bins=256, range=(0, 256))
    total, levels = area.size, np.arange(256)
    weight = np.cumsum(hist)
    mean = np.cumsum(hist * levels)
    between = (mean[-1] * weight / total - mean) ** 2 / np.maximum(weight * (total - weight), 1)
    level = int(np.argmax(between))
    text = area > level
    if text.mean() > 0.5:
        text = ~text
    profile = text.mean(axis=1)
    on = profile > max(0.02, 0.15 * profile.max())
    runs, start = [], None
    for y, value in enumerate(np.append(on, False)):
        if value and start is None:
            start = y
        elif not value and start is not None:
            runs.append([start, y])
            start = None
    merged = []
    for run in runs:                                    # join runs split by a 1-2 px gap inside a line
        if merged and run[0] - merged[-1][1] <= 2:
            merged[-1][1] = run[1]
        else:
            merged.append(run)
    tallest = max((b - a for a, b in merged), default=0)
    lines = [(a, b) for a, b in merged if b - a >= max(min_height, 0.3 * tallest)]
    if not 2 <= len(lines) <= max_lines:
        return []
    # Widest stretch of kept columns (the text block beside the number column).
    left = right = best = 0
    x = 0
    while x < w:
        if keep[x]:
            y = x
            while y < w and keep[y]:
                y += 1
            if y - x > best:
                left, right, best = x, y, y - x
            x = y
        else:
            x += 1
    if best < 0.3 * w:
        return []
    out = []
    for a, b in lines:
        pad = max(2, (b - a) // 6)
        out.append(crop.crop((left, max(0, a - pad), right, min(h, b + pad))))
    return out
