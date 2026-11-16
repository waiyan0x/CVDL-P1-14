# OCR model recommendation and weights

Updated 16 November 2026. Start matching development with **PaddleOCR
`en_PP-OCRv5_mobile_rec`**, keeping the other two engines for comparison.
On the selected validation subsets it has the lowest CER and highest exact
match. Public TrOCR has lower WER on predicted crops. This is a **provisional
project choice from local diagnostics**: photo grouping is pending and official
independent-benchmark eligibility remains zero. Train scores use AI-assisted
labels; this handoff contains no fine-tuned OCR weights.

## Start with saved OCR outputs

Read `matching_inputs.jsonl` and select `model == "paddleocr"` (271 saved records,
including failures and exclusions). Retain raw and normalised OCR separately and
respect `prediction_status`. Error records are not usable recognition text.
Keep annotation and detector-predicted populations separate; annotation crops
are evaluation evidence. Respect exclusions when evaluating. Preserve the
other engines' records for comparison. Confirm display ownership before
combining fields. Weights are unnecessary for matching these saved outputs.

## Actual weights included

All three locally cached public pretrained checkpoints are supplied under
`weights/`. Their bytes match the baseline report hashes, including tokenizer,
processor and inference configuration files where required. Weights were
unchanged before/after the original train/validation inference runs.

| Engine | Checkpoint | Packaged files |
| --- | --- | --- |
| PaddleOCR | `PaddlePaddle/en_PP-OCRv5_mobile_rec` | `weights/paddleocr/`, including `inference.pdiparams`, `inference.json`, `inference.yml` and provenance |
| TrOCR | `microsoft/trocr-base-printed` | `weights/trocr/`, including `model.safetensors`, tokenizer, processor and model configuration |
| EasyOCR | English generation-2 recognizer, EasyOCR 1.7.2 | `weights/easyocr/english_g2.pth` and cached `craft_mlt_25k.pth`; the scored baseline used detector-disabled recognition |

Pinned revisions:

- PaddleOCR: `267c36e24c331595590fe7bd72bde2436fd286f2`.
- Public TrOCR: `93450be3f1ed40a930690d951ef3932687cc1892`.
- EasyOCR: original file SHA-256 values are pinned in `weights/models.lock.json`.

`weights/models.lock.json` records each file hash, checkpoint identity, baseline
recognition settings, preprocessing, device and validation-layout hash. TrOCR is
the public pretrained checkpoint used in this comparison; select this supplied
directory when reproducing these results.

From the unzipped handoff root, verify all packaged model files with standard
Python (no OCR dependencies needed):

```sh
python3 verify_weights.py
```

## Running OCR again

Use the repository and its OCR dependencies, input crops and the appropriate
model directory. The ZIP supplies weights and audit evidence; it is not a full
standalone application/environment or a replacement for the original dataset.
Baseline source snapshots are under `inference/source/`. Frozen validation and
training layouts are under `inference/layouts/`. Validation uses AI-reviewed
line geometry; training uses unreviewed automatic geometry. New images need
their own detection/cropping and line-layout preparation before these runners.
Whole-display OCR/field extraction has not been evaluated in these saved runs.

For example, from the repository root, set `HANDOFF` to the absolute path of the
unzipped handoff folder, then rerun the existing validation crop inventory:

```sh
HANDOFF='/absolute/path/to/reference-matching-20261115-01'
.venv/bin/python scripts/run_paddle_crops.py \
  --workspace evaluation/ocr_annotations/v4-reviewed-01 \
  --model-dir "$HANDOFF/weights/paddleocr" \
  --line-layout "$HANDOFF/inference/layouts/validation/manifest.json" \
  --output .cache/ocr_runs/paddle-handoff-reproduction-01
```

Choose a new output directory for each run. This reproduces crop recognition,
without reference matching; it does not fine-tune weights. The original Paddle
run used CPU, batch size 1, two threads and MKLDNN disabled. EasyOCR and public
TrOCR use `scripts/run_easyocr_crops.py` with `--engine easyocr|trocr`, the matching
`--cache` directory, explicit `--line-layout`, a supported `--device` and a new
`--output`. Default model inference alone, with different line handling/settings,
does not reproduce the scored baseline. Device differences mean the saved
timings are unsuitable for ranking deployment speed.

## Local diagnostic evidence for the recommendation

Step 4-normalised scores below transform predictions and references identically.
These are selected readable crops; P028 is excluded. The populations are scored
separately. Source: `ocr_tables/` and the validation diagnostic snapshot copied
to `inference/recommendation_diagnostics.csv`. No reference matching contributed
to these values. The normalisation preserves suffixes, zeros and abbreviations.

### Annotation crops (n=67)

| OCR | CER (%) ↓ | WER (%) ↓ | Exact match (%) ↑ |
| --- | ---: | ---: | ---: |
| easyocr | 34.17 | 64.34 | 40.30 |
| trocr | 11.20 | 31.01 | 65.67 |
| paddleocr | 7.72 | 24.81 | 79.10 |

### Prediction crops (n=40)

| OCR | CER (%) ↓ | WER (%) ↓ | Exact match (%) ↑ |
| --- | ---: | ---: | ---: |
| easyocr | 24.79 | 52.38 | 60.00 |
| trocr | 8.12 | 15.87 | 82.50 |
| paddleocr | 7.69 | 25.40 | 85.00 |
