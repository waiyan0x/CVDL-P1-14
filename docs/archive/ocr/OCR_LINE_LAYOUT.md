# Reviewed and frozen OCR line regions

**Observed work, 8 November 2026:** Codex (AI) visually inspected all 271 native
crops using 31 contact sheets with pixel-coordinate rulers, then inspected all
36 initially proposed multiline decisions as overlays and extracted patches.
No independent human review is attested. OCR predictions, confidence and text
transcriptions were not used to choose boundaries; only the previous candidate
geometry was retained for change accounting.

## Frozen artifact

Use `evaluation/ocr_layouts/v4-lines-v1/manifest.json` with its adjacent
`manifest.sha256`. The package preserves the explicit per-crop decisions,
overlays and extracted diagnostic line images. Every source ID/hash is checked.
No source crop, transcription, model weight or previous run is modified.
All derived line PNGs remain **validation data**. They must not enter OCR training.

| Crop set | Inspected | Accepted geometry | Unresolved | Multiline | Extracted line regions |
| --- | ---: | ---: | ---: | ---: | ---: |
| A: annotation | 157 | 146 | 11 | 5 | 151 |
| P: prediction | 114 | 105 | 9 | 24 | 129 |
| Total | 271 | 251 | 20 | 29 | 280 |

Acceptance is a geometry-review decision by AI, **not** certification of readable
text, correct field ownership, human-reviewed ground truth or scoring eligibility.
Unreadable text can still have an identifiable single spatial row. Conversely,
blur, saturation, mixed adjacent fields and clipped sloping rows can make the
layout unresolved even when some characters are readable.

## Geometry contract and reuse

Each accepted entry contains an explicit ordered list of full-width separators.
A separator records the y coordinate at the left and right crop edges. Native
pixel-edge coordinates use right/bottom-exclusive bounds. Separators must stay
inside the image, never cross, and leave at least two pixels on both sides of
each region. Their quadrilaterals partition the entire source crop; no glyphs
are reconstructed, missing text invented, or field classes changed.

Horizontal bands are exact array slices. Sloping bands are rectified with the
same shared `extract_region` function using original crop width, maximum side
height, OpenCV linear interpolation and replicated borders. This is conventional
geometric preprocessing, not generative enhancement. The manifest records it.
The derived PNGs are diagnostics, not replacements for original crop assets.

Use `load_layout` and `extract_region` from
`backend/app/evaluation/ocr_line_layout.py` for all OCR engines. Never choose
different boundaries based on an engine's predictions. The EasyOCR runner now
accepts the manifest explicitly:

```sh
.venv/bin/python -u scripts/run_easyocr_crops.py \
  --device mps --warmup 3 --seed 0 \
  --line-layout evaluation/ocr_layouts/v4-lines-v1/manifest.json \
  --output evaluation/ocr_runs/easyocr-v4-mps-fixed-lines-01
```

Without `--line-layout`, the runner retains its earlier automatic v2 method.
With it, **no automatic or whole-crop fallback is permitted for unresolved
entries**. All 271 IDs remain in the run; unresolved geometry yields explicit
error records. Warmup uses the first accepted-geometry annotation crop per field.
The actual manifest bytes/hash are copied into any new run and checked again at
completion. This change was tested with a stub recognizer, not an additional
real OCR run or an accuracy calculation.

Manually reviewed upstream geometry provides additional information. Results
using it are a fixed-layout recognition diagnostic and must be distinguished
from automatic segmentation or deployment/pipeline performance. Report geometry
coverage/exclusions alongside later text scores. It does not establish correct
full results or dataset independence.

## Decisions that remain unresolved

The package's `unresolved.csv` retains the reason for each entry:

- A002, A028, A048, A052, A055, A057, A070, A074, A094, A120, A121.
- P002, P005, P029, P041, P046, P048, P087, P089, P105.

A003 and P003 have separately reviewed sloping boundaries instead of their old
single-band proposals. A002 and P002 remain blocked: clipping and skew do not
support reliable full-width line regions. LED dot rows in numeral crops are
retained as part of one character row. Some initially proposed extra bands were
removed after patch-level inspection showed non-text background/glow instead.

Resolve ambiguous cases using original-image context or independent geometry
review, preserving the existing crop task. If the full-width representation is
insufficient, introduce an explicitly documented new geometry version; do not
force a split that cuts a tall neighboring field. Do not silently widen crops,
drop fragments or invent new text.

## Validation and versioning

The freeze script refuses an existing output and requires an explicit decision
for every crop. Reproduce the current file into a **new** directory with:

```sh
.venv/bin/python scripts/freeze_ocr_line_layout.py \
  --decisions evaluation/ocr_layouts/v4-lines-v1/review_decisions.json \
  --version v4-lines-v1 \
  --output /path/to/new-layout-copy
```

Corrections require a new version and directory. The checksum detects accidental
manifest changes; it is not a signature or proof that geometry is correct.
Tests cover full coverage, honest attribution, in-bounds/noncrossing geometry,
pixel-preserving horizontal extraction, documented sloping dimensions, source
hash identity, checksum enforcement, no fallback and overwrite refusal.

Text-label inconsistencies, burst-group review and predicted-field correspondence
remain separate prerequisites. Reference matching, post-processing, training
and accuracy scoring were not performed.
