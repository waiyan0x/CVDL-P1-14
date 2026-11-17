# Colab OCR fine-tuning

Preparation only: no local training, model-loading dry run, GPU run or training
result is claimed. These are new files; existing files/runners were not edited.
No commit or push is part of this task. **TEST was not read or used.**

## Build and upload

From the repository root:

```sh
.venv/bin/python scripts/export_ocr_finetune_bundle.py --output .runtime/ocr_finetune_bundle-20261117.zip
python3 -m zipfile -c .runtime/ocr_finetune_code.zip colab/ocr_finetune
```

The exporter refuses an existing output. Use a new name for another export;
do not overwrite a previously reviewed bundle. Upload both ZIPs to `My Drive/DRIVE`. Rename the data ZIP to
`ocr_finetune_bundle.zip`; keep `ocr_finetune_code.zip` unchanged. The notebook
downloads and hash-verifies initial weights directly into
`DRIVE/CVDL-OCR-inputs/weights/`; no manual weight upload is normally needed.
If a download cannot match the lock, use the original packaged model files,
including all HF processor/config files. Weights/checkpoints never belong in Git.

Open `ocr_finetune.ipynb` in Colab, choose a T4 GPU, and configure `INPUT` and
`OUTPUT`. The default output is
`/content/drive/MyDrive/DRIVE/CVDL-OCR-finetune/<model>/<run_id>/`.
Use your actual shared/team Drive path when needed. The notebook copies only
the small data/code ZIPs to temporary Colab storage. Initial weights stay on
Drive; Paddle's training checkpoint is downloaded directly to Drive and its
official URL and SHA-256 are recorded. Existing inference `.pdiparams` cannot
replace the training `.pdparams`.

## Verified input policy

The current export contains:

| Item | Count |
| --- | ---: |
| Original training crops / groups | 387 / 129 |
| Training line pairs | 366 |
| Skipped training crops | 24 |
| Joined two-label-line / one-region training crops | 9 |
| Validation line pairs | 124 |
| Validation inference region images | 128 |
| Validation crops in crop CER | 130 |
| Test files | 0 |

All 129 augmented groups remain in their original training split. No new
split is made. Eight training crops with two regions/one text line and sixteen
with no region are skipped and listed individually in `skipped.csv`. Nine
one-region/two-text-line labels are joined with one space, logged in `joined.csv`.
Other text is preserved exactly. Literal charset is derived from exported
training labels, not from this README or examples. See `charset.txt` and
`dictionary_check.json`.

**Validation assumption:** retain every eligible crop in crop CER. Four
zero-region crops remain empty hypotheses. Two crops with two regions but one
reference line have no invented line labels: their native inference regions
are retained for crop-level recognition, while their line-label pairs are
skipped. Thus six validation pairing issues are logged, but only four crops
have no inference image. Line CER has 124 labelled pairs; crop CER has 130 crops.

Line extraction imports the repository's `extract_region`: PIL RGB, OpenCV
RGB-to-gray, frozen quadrilateral extraction, lossless grayscale PNG. TrOCR and
Paddle replicate grayscale to RGB at load/decode time. Five seeded validation
crops with regions passed readback equality against evaluation's grayscale
pixel-array bytes. PNG compression bytes themselves are not the model input.
The manifest records sampled IDs, pixel hashes, input file hashes, crop hashes,
source commit and extraction source hash. Every source hash is checked again
before the ZIP is completed to detect concurrent input edits.

## Training and exports

All three use seed 0, batch 8, initial learning rate 5e-5, at most 20 epochs,
no synthetic text and **no augmentation**, consistently across frameworks.
Deterministic operations are requested where supported. Native optimisers and
schedules differ and are recorded: HF AdamW/linear, EasyOCR Adam/constant,
Paddle Adam/cosine. Do not call these identical optimisation algorithms.

Each run writes `config.json`, `epoch_log.csv` and `best/`. CSV columns are
`epoch,train_loss,val_line_CER,val_crop_CER,val_crop_exact`. CER/exact values are
fractions, not percentages. Normalisation is copied from the repository:
NFC, casefold, NFC, collapsed whitespace. Punctuation/abbreviations stay intact.
Failed line predictions and absent regions contribute empty text. Best model
selection always uses lowest **crop CER**, not line accuracy or exact match.

- **TrOCR:** uses packaged `trocr-base-printed` only, verifies its hash lock,
  checks tokenizer round trips, uses `Seq2SeqTrainer`, per-epoch validation,
  `metric_for_best_model=cer`, `greater_is_better=False`, best-model reload and
  early stopping patience 3. `best/` is HF model + processor + provenance.
- **EasyOCR:** imports the official pinned `trainer/model.py` Model. An epoch
  CTC loop selects by full crop CER; it does not use the upstream trainer's
  default accuracy selector. The original English g2 alphabet/checkpoint is
  retained with strict state loading. `best/` contains
  `eds_english_g2.pth/.yaml/.py` and the exact `easyocr.Reader` load call.
- **Paddle:** clones tag `v3.3.2` and verifies its commit, derives the English
  v5 mobile config and writes an explicit dictionary covering this charset.
  The current dictionary needs **zero added characters**. Future missing
  characters fail with an exact list rather than silently dropping labels or
  resizing a pretrained head incorrectly. This is the fail-with-list option
  in the task constraints; automatic head/dictionary expansion is not claimed.
  Training uses `tools/train.py`; custom `cer_score=1/(1+crop_CER)` makes the
  upstream maximum selector equivalent to minimum CER. The historical filename
  `best_accuracy` therefore holds the CER-selected checkpoint. It is exported
  with `tools/export_model.py`; the script requires `inference.json`,
  `inference.pdiparams`, `inference.yml` and writes provenance under `best/`.

Paddle's separate `eval_io_not_ground_truth.tsv` contains `?` placeholders
only to satisfy its upstream label-encoding transform. Its metric ignores
those labels and reads actual line/crop references from the bundle. The
placeholders never enter `train.tsv`, `valid.tsv` or scoring truth.

Pinned direct package versions are in the notebook. Actual resolved versions
are saved with each runtime and each run. Notebook setup has been attempted in Colab, but successful model dry runs and
full GPU training have not been confirmed. GPU kernels, Paddle training-head
loading and checkpoint export still need checks on the target runtime.

## CPU smoke checks

Each trainer supports `--dry-run`: eight pairs, two CPU optimiser steps, no
weight/checkpoint saving. On Colab, after the notebook installs both isolated
environments and copies the inputs, run its dry-run cell, or these exact commands
(replace `$RUN_ID` and the configurable Drive input path):

```sh
/content/ocr-torch-py312/bin/python /content/ocr-finetune/code/colab/ocr_finetune/train_trocr.py --data /content/ocr-finetune/data --pretrained /content/drive/MyDrive/DRIVE/CVDL-OCR-inputs/weights/trocr --output /content/drive/MyDrive/DRIVE/CVDL-OCR-finetune/trocr/$RUN_ID-dry --dry-run
/content/ocr-torch-py312/bin/python /content/ocr-finetune/code/colab/ocr_finetune/train_easyocr.py --data /content/ocr-finetune/data --repo /content/EasyOCR --pretrained /content/drive/MyDrive/DRIVE/CVDL-OCR-inputs/weights/easyocr/english_g2.pth --output /content/drive/MyDrive/DRIVE/CVDL-OCR-finetune/easyocr/$RUN_ID-dry --dry-run
/content/ocr-paddle-py312/bin/python /content/ocr-finetune/code/colab/ocr_finetune/train_paddle.py --data /content/ocr-finetune/data --repo /content/PaddleOCR --pretrained /content/drive/MyDrive/DRIVE/CVDL-OCR-inputs/weights/paddle-training/en_PP-OCRv5_mobile_rec_pretrained.pdparams --output /content/drive/MyDrive/DRIVE/CVDL-OCR-finetune/paddleocr/$RUN_ID-dry --dry-run
```

Model-loading dry runs were not run on the Mac. The checked local environment
lacks Torch/Transformers/Paddle, and the official Paddle training checkpoint
must be downloaded in Colab. Installing full frameworks or producing local
checkpoints is outside this task. Static compilation and data/scoring tests
are not substitutes for these pending smoke checks.

## T4 runtime

There is no measured T4 runtime. As an **unverified planning allowance**, reserve
roughly 1–3 hours for setup/downloads and the three runs, with substantial
variation from early stopping, Drive speed and GPU memory. This is not a
benchmark, deadline or achieved result. Use the notebook's timers and first
epoch to replace this allowance with measured timing. A successful two-step
CPU smoke test does not establish GPU speed or model accuracy.

## Step 6 runner mapping — changes proposed, not applied

- TrOCR HF `best/` maps to `run_easyocr_crops.py --engine trocr --cache BEST`.
  Keep the same crop/layout arguments. Its baseline-only provenance/model-name
  checks/report wording must recognise `fine_tuned=true` rather than call the
  new weights public pretrained. Verify weight hashes and model reload first.
- Paddle inference `best/` maps to `run_paddle_crops.py --model-dir BEST` with
  identical crop/layout arguments. Exported provenance provides its new hashes.
  The runner's baseline-only model/report wording must likewise identify the
  fine-tuned variant. Existence of filenames alone is not a recognition test.
- EasyOCR currently has no custom-network loading flag. Minimal proposed
  change: add `--recog-network` (default `standard`) and
  `--user-network-directory`, pass them to `easyocr.Reader`, and make the
  weight/provenance path choose `<recog_network>.pth` for custom networks.
  Use `eds_english_g2` plus `best/` for both model and user-network directories.
  Preserve the current defaults for pretrained runs. **No runner was edited.**

Do not select the app model or claim Step 6 results from this preparation.
The user-owned later comparison uses fine-tuned TEST annotation metrics;
neither TEST data nor TEST settings were accessed here.

## Official implementation references

- [HF Trainer](https://huggingface.co/docs/transformers/v4.57.1/en/main_classes/trainer)
- [EasyOCR v1.7.2 trainer](https://github.com/JaidedAI/EasyOCR/tree/v1.7.2/trainer)
- [English Paddle v5 config](https://github.com/PaddlePaddle/PaddleOCR/blob/v3.3.2/configs/rec/PP-OCRv5/multi_language/en_PP-OCRv5_mobile_rec.yaml)
- [Paddle training](https://github.com/PaddlePaddle/PaddleOCR/blob/v3.3.2/tools/train.py)
- [Paddle recognition model list](https://github.com/PaddlePaddle/PaddleOCR/blob/v3.3.2/docs/version3.x/module_usage/text_recognition.en.md)

## Colab run checklist and restart corrections

- Use only the GPU allocated by Google Colab. `nvidia-smi` is a read-only diagnostic on that remote machine, not another GPU and not a Mac requirement. The first code cell checks it before any downloads. Select Runtime > Change runtime type > T4 GPU and reconnect if missing.
- After a runtime restart, run cells from the top. Drive ZIPs, verified initial weights and saved model outputs persist; temporary environments and variables must be recreated. Valid existing weights are reused.
- Keep the bundle/hash/test-use checks. Run all three CPU dry runs in Colab before full GPU training. Do not bypass failures.
- Run one model at a time on that same Colab GPU. Record the exact model/run_id folder. Keep hyperparameters unchanged and report errors, including CUDA out of memory.
- TrOCR and EasyOCR use patience-3 early stopping. Paddle runs its configured epochs and has no patience-3 early stopping. All three select their best checkpoint by lowest validation crop CER.
- Preserve disconnected runs as incomplete. EasyOCR/Paddle checkpoints are on Drive; TrOCR keeps per-epoch checkpoints (model only, `save_only_model`) on Colab's local disk and saves only `best/` to Drive, so free Drive space is not exhausted. Automatic resume is not implemented. Do not assume everything is lost or overwrite a completed run. Keeping a tab open is not a guarantee against disconnection.
- Do not blanket-ignore newly initialised/missing-weight warnings; inspect their parameter names first.
- Check each completed run for config.json, epoch_log.csv, selection.json and a populated best/, then reload the model. Record its lowest val_crop_CER and Drive folder. Dry-run folders are separate and are not trained models.
- When all three are complete and verified, disconnect/delete the Colab runtime to release it. Files on Drive remain. No TEST data is used in this notebook.
