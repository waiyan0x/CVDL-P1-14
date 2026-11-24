# Five-thousand-pair OCR dataset — train/validation/test

User decision: split the 5,000 exported image/text pairs into training,
validation and test. Default ratio selected: 80/10/10, exactly 4,000/500/500.
Each example is one exported line image and its text reference. Multiple
lines from one original crop are kept in the same split. It is not 5,000
training pairs plus extra validation/test, nor 5,000 original field boxes.

| Split | Total pairs | Original real | Rendered | Number | Destination | Route |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 4,000 | 297 | 3,703 | 1,688 | 1,554 | 758 |
| Validation | 500 | 45 | 455 | 212 | 186 | 102 |
| Test | 500 | 24 | 476 | 217 | 173 | 110 |

All 5,000 parent pairs are retained once. Origin is metadata; the same model
and scoring rules apply to every pair. Original real transcriptions retain
AI-assisted provenance; rendered strings are adopted project reference labels.
The user's human review covers the prior 100 sampled source crops, not every
row. The small real-photo portions and shared rendering process limit how well
combined results establish performance on actual buses.

## Grouping and verification

Seed 0. Connected groups use NFC/casefold/whitespace-normalised exact text,
original source crop, known original real source photo, and identical PNG hash.
304 groups were assigned whole; field balance was optimised without looking
at OCR predictions. There is zero cross-split overlap for these identifiers
and exact normalised text. Near-duplicate photos, shared glyph families,
templates and partial text similarities are not proven independent.
Every output image preserves its parent bytes and SHA-256; ZIP CRC and payload
hashes passed. split_manifest.json records the policy and actual counts.
labels.csv contains all rows; train_labels.csv, valid_labels.csv and
test_labels.csv contain their respective text references and image hashes.
No bus_information.csv value replaces the text in an image.

## Files and Colab

Use colab/ocr_finetune/ocr_finetune_5k_split.ipynb. Upload these to My Drive/DRIVE:

- ocr_dataset-20261120-5k-train-valid.zip
- ocr_finetune_code-20261120-earlystop.zip
- ocr_5k_split_review.csv (provided here)

Keep the separate ocr_dataset-20261120-5k-test.zip locally until the final test
phase. It contains test.tsv, test_crops.jsonl and the 500 held-out images.
The training ZIP has only train/validation images and references, initial-weight
lock, train charset and hashes; its test_files=0. The notebook never reads the
test archive. The review receipt contains only IDs/verdict/reviewer/date from
the prior user-confirmed sample; it contains no held-out text or images.

The trainer loader verified 4,000 train and 500 validation examples, including
all file hashes. The test ZIP separately passed 500-example/hash checks.
Training settings: T4, batch 32, max 20 epochs, validation crop-CER patience 3.
This is 125 training steps/epoch, at most 2,500 steps/model. Run CPU smoke
checks for this new input/code combination, then each model sequentially.

## Colab training results — validation only (20 November 2026)

Observed from the returned `selection.json` and `epoch_log.csv` of run
`ocr5k-split-b32-e20-20261120-084105` (Colab T4). Scores are on the 500
validation line images (45 original real, 455 rendered) that also selected each
checkpoint, so they are optimistic and are not test results. CER and exact
match use the trainer's normalisation (NFC, casefold, NFC, whitespace
collapse). The 500-example test set has not been opened.

| Model | Batch | Epochs run | Selected epoch | Val crop CER | Val exact | Training time | Stop reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| PaddleOCR (en_PP-OCRv5_mobile_rec) | 32 | 12 | 9 | 0.0097 | 0.972 | 1,138 s | Early stop (patience 3; epoch 12 tied epoch 9) |
| EasyOCR (english_g2) | 32 | 20 | 20 | 0.0263 | 0.918 | Not recorded in `selection.json` | Reached 20-epoch maximum; CER still falling |
| TrOCR (trocr-base-printed) — run `…-123420` | 16 | 8 | 5 | 0.410 | 0.258 | 7,564 s | Early stop (epochs 6–8 worse: 0.521, 0.679, 0.828) |
| TrOCR pretrained, epoch 0 (no training) | — | — | 0 | 0.0761 | 0.632 | — | Same-code baseline printed at start of training |

Notes:

- PaddleOCR selection: epoch 12 equalled epoch 9's CER; ties are not
  improvements, so the plateau stop fired before epoch 12 was saved. The
  exported `best/` (`inference.json`, `inference.pdiparams`, `inference.yml`)
  is the epoch 9 checkpoint. The early-stop and export path is therefore
  verified on Colab. Paddle's `train_loss` includes the NRTR branch and is not
  comparable with the other models' losses.
- EasyOCR selection is by CER: epoch 20 has the lowest CER, although epoch 18
  has the highest exact match (0.924).
- Batch 32 fitted T4 memory for PaddleOCR and EasyOCR. TrOCR at batch 32 ran out
  of CUDA memory on its first step in fp32 (14.55 of 14.56 GiB in use), so it
  was retrained at batch 16 after a runtime restart, as run
  `ocr5k-split-b32-e20-20261120-123420` with reinstalled environments. State the
  batch difference and the separate RUN_ID when comparing TrOCR with the other
  two models.
- **TrOCR fine-tuning failed on validation.** Every fine-tuned epoch (CER
  0.410–0.828) is far worse than the untouched pretrained epoch 0 (0.0761), while
  training loss fell to about 0.03. Diagnosis from this run's
  `validation_predictions.jsonl` and the label files: the 4,000 training lines
  contain only 302 distinct normalised texts, and none of the 28 validation
  texts occur in training (by design of the grouped split). The fine-tuned
  decoder substitutes memorised training strings for unseen ones: `195` → `145`
  and `33` → `30` (both outputs are training texts; neither target is), and
  `TIONG BAHRU RD` → `TION BAU RD RD`. By epoch 8 it loops (`TER TER TER …`),
  so 80 of 500 lines hit the 64-token cap without EOS and score as empty. The
  CTC models (PaddleOCR, EasyOCR) have no autoregressive text decoder and did
  not show this. Do not use this `best/` checkpoint (epoch 5,
  `checkpoint-1250`); the pretrained TrOCR is better on this validation set.
- Validation (28 distinct texts; `> SIMS PLACE TER` and `TIONG BAHRU RD` are
  225 of 500 lines) and test (14 distinct texts; the top three are 61% of
  lines) are dominated by a few strings. Every model's scores here mainly
  reflect those strings, not broad text coverage.
- `val_line_CER` equals `val_crop_CER` in every epoch on this split.
- GPU training used non-deterministic CUDA kernels (`warn_only=True`), so
  repeat runs with seed 0 need not be bit-identical.

## Benchmark and handoff policy

Start new runs from ORIGINAL PUBLIC PRETRAINED weights. Earlier fine-tuned
models trained on some of these newly held-out examples, including models
trained on the full 10k/5k pools. They are not independent baselines here;
previous real-only/old-synthetic scores cannot be relabelled as results for
this new 500-example test set. Keep those experiments unchanged and separate.

Select checkpoints/settings using the new validation set. Once frozen, compare
original pretrained versus new fine-tuned predictions on the same 500 test
examples. Use NFC, casefold, NFC and whitespace collapse; retain punctuation;
failed/missing outputs count as empty. Report micro CER/WER and per-image exact
match, per field and origin as well as combined. The unit is exported line
image, so these denominators differ from historical whole-field-crop results.
Model selection on TEST under the project's existing rule must be labelled as
such, not an independent final estimate. Do not tune settings on TEST.
The original real-photo benchmark can be retained separately as a supplementary
release check, with its earlier known limitations and selection history.

A new selected model must be reloaded and its weights hashed against the scored
checkpoint before generating new raw/normalised matching_inputs.jsonl on the
agreed matching crop inventory. This split does not change the existing round 1
PaddleOCR matching delivery or confirm display ownership. No CSV matching or
new OCR accuracy has been claimed. Nothing was pushed.

Reproduce with scripts/split_5k_ocr_dataset.py (refuses existing outputs).
archives.lock.json freezes the two ZIPs; notebook.lock.json freezes the notebook
and records loader checks. Keep the 500-test archive out of training.
