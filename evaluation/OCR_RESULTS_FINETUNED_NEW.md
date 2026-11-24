# OCR results — fine-tuning on the 5k train/validation/test split

Status, 20 November 2026: training finished for all three engines. **Validation
results only.** The 500-example test set has not been opened, so nothing below
is a final or test accuracy. These results are separate from the earlier
round 1, round 2 and synthetic-v2 tables (`OCR_RESULTS*.md`): the unit, data
and denominators differ, so do not copy numbers between them.

## Data

Source: `evaluation/ocr_dataset/5k-split-20261120/README.md`.

| Split | Line images | Original real | Rendered | Distinct texts |
| --- | ---: | ---: | ---: | ---: |
| Train | 4,000 | 297 | 3,703 | 302 |
| Validation | 500 | 45 | 455 | 28 |
| Test (held out, unused) | 500 | 24 | 476 | 14 |

- The unit is one exported line image with its text reference, not a whole
  field crop.
- Groups sharing normalised text, source crop, source photo or identical PNG
  were kept in one split, so **no validation or test text appears in
  training**.
- Validation is dominated by two texts: `> SIMS PLACE TER` (123 lines) and
  `TIONG BAHRU RD` (102 lines), together 225 of 500. In test, the top three
  texts are 61% of lines.

## Training setup

Project decisions, as configured in `colab/ocr_finetune/ocr_finetune_5k_split.ipynb`:

- Colab T4 GPU, seed 0, start from the original public pretrained weights.
- At most 20 epochs. Early stopping on validation crop CER with patience 3
  (a tie counts as no improvement). The checkpoint with the lowest validation
  CER is kept.
- Scoring normalisation: NFC → casefold → NFC → collapse whitespace;
  punctuation retained.

| Engine | Starting weights | Batch | Run ID |
| --- | --- | ---: | --- |
| PaddleOCR | `en_PP-OCRv5_mobile_rec` | 32 | `ocr5k-split-b32-e20-20261120-084105` |
| EasyOCR | `english_g2` | 32 | `ocr5k-split-b32-e20-20261120-084105` |
| TrOCR | `microsoft/trocr-base-printed` | 16 | `ocr5k-split-b32-e20-20261120-123420` |

Differences to state when comparing the three:

- TrOCR at batch 32 ran out of GPU memory on its first step (fp32, 14.55 of
  14.56 GiB in use), so it was trained at batch 16.
- A Colab runtime restart happened between runs, so TrOCR has a separate
  Run ID and reinstalled environments. The package lists for each run are saved
  under `CVDL-OCR-finetune/environment/<RUN_ID>/` on Drive.
- The `b32` in TrOCR's Run ID is the notebook default, not its actual batch.
  Its `config.json` records batch 16.

## Results (validation, 500 line images)

Observed from each run's `selection.json` and `epoch_log.csv`.

| Engine | Epochs run | Selected epoch | Val CER | Val exact match | Training time | Stop reason |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **PaddleOCR fine-tuned** | 12 | 9 | **0.0097** | **0.972** | 1,138 s | Early stop |
| EasyOCR fine-tuned | 20 | 20 | 0.0263 | 0.918 | Not recorded | 20-epoch maximum |
| TrOCR fine-tuned | 8 | 5 | 0.410 | 0.258 | 7,564 s | Early stop |
| TrOCR pretrained (epoch 0, no training) | — | — | 0.0761 | 0.632 | — | Baseline |

The validation set was also used to choose each selected epoch, so these
scores are optimistic. No pretrained baseline was logged for PaddleOCR or
EasyOCR on this split, so their improvement over pretrained cannot be stated
from these logs.

### PaddleOCR

| Epoch | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | **9** | 10 | 11 | 12 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Val CER | 0.0354 | 0.0177 | 0.0181 | 0.0148 | 0.0121 | 0.0117 | 0.0115 | 0.0113 | **0.0097** | 0.0113 | 0.0107 | 0.0097 |
| Val exact | 0.802 | 0.958 | 0.930 | 0.966 | 0.966 | 0.966 | 0.970 | 0.970 | **0.972** | 0.966 | 0.968 | 0.972 |

- Epoch 12 tied epoch 9. The tie is not an improvement, so early stopping fired
  before epoch 12 was saved. The exported model is epoch 9.
- Paddle's training loss includes its auxiliary NRTR branch (flat at about
  0.935 throughout) and is not comparable with the other engines' losses.

### EasyOCR

| Epoch | 1 | 4 | 8 | 12 | 16 | 17 | 18 | 19 | **20** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Val CER | 0.0561 | 0.0426 | 0.0362 | 0.0319 | 0.0296 | 0.0275 | 0.0271 | 0.0275 | **0.0263** |
| Val exact | 0.834 | 0.892 | 0.906 | 0.918 | 0.918 | 0.922 | 0.924 | 0.922 | **0.918** |

Selected epochs only; the full log is in `epoch_log.csv`.

- CER was still falling at epoch 20, so more epochs might have helped. The run
  ended at the fixed maximum.
- Selection is by CER: epoch 20 has the lowest CER, but epoch 18 has the
  highest exact match (0.924).

### TrOCR

| Epoch | 0 (pretrained) | 1 | 2 | 3 | 4 | **5** | 6 | 7 | 8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train loss | — | 1.152 | 0.176 | 0.149 | 0.080 | 0.061 | 0.044 | 0.026 | 0.028 |
| Val CER | 0.0761 | 0.484 | 0.440 | 0.538 | 0.471 | **0.410** | 0.521 | 0.679 | 0.828 |
| Val exact | 0.632 | 0.428 | 0.266 | 0.256 | 0.362 | **0.258** | 0.156 | 0.302 | 0.312 |
| No-EOS failures | 0 | 111 | 0 | 1 | 1 | 0 | 1 | 16 | 80 |

**Fine-tuning failed.** Every fine-tuned epoch is far worse than the
untouched pretrained model, while training loss fell to about 0.03.

**Diagnosis** (observed in `validation_predictions.jsonl` and the label files):
the decoder memorised the 302 training texts and outputs them in place of
unseen validation text.

| Target (not in training) | Fine-tuned output | Output in training? |
| --- | --- | --- |
| `195` | `145` | Yes, 15 lines |
| `33` | `30` | Yes, 3 lines |
| `TIONG BAHRU RD` | `TION BAU RD RD` | Fragments of training text |
| `> SIMS PLACE TER` | `> WANAY TER TER TER TER TER TER M` | Repetition loop |

- By epoch 8, 80 lines looped until the 64-token limit without an
  end-of-sequence token. The trainer scores those as empty, which drives CER
  to 0.83.
- TrOCR generates text token by token, conditioned on its previous output.
  PaddleOCR and EasyOCR are CTC recognisers without an autoregressive text
  decoder, and did not show this failure on the same data.
- Round 2 TrOCR fine-tuning (run `20261118-084149`) showed the same
  degradation and similar garbled predictions.

Do not use the fine-tuned TrOCR `best/` checkpoint (epoch 5,
`checkpoint-1250`).

## Conclusions

- **PaddleOCR fine-tuned is the best of the three 5k models** on validation
  (CER 0.0097, exact 0.972). On the real-photo matching crops, however, it does
  not beat the round 1 PaddleOCR model (test n=45: CER 0.100 vs 0.082). See
  "Files needed for inference matching". It still needs the held-out test
  evaluation before any final claim.
- EasyOCR fine-tuned is second (CER 0.0263).
- TrOCR: the pretrained model (CER 0.0761) beats every fine-tuned epoch.
  Fine-tuning it usefully would need far more distinct training texts. Freezing
  the decoder or training more lightly might reduce memorisation but not fix
  the lack of variety. This is a proposal, not tested.
- With 28 distinct validation texts and 14 distinct test texts, every result
  mainly reflects a few strings. It does not show broad text coverage or
  real-bus performance (only 45 validation and 24 test lines are original real
  photos).

## Pending

1. Freeze the selected checkpoints, then run original pretrained versus
   fine-tuned on the same 500 test lines. Report CER, WER and exact match by
   field and by origin (real vs rendered), and combined.
2. Reload the selected PaddleOCR model and hash its weights against the scored
   checkpoint before producing new matching inputs.
3. The current round 1 PaddleOCR matching delivery is unchanged until a 5k
   model passes the test benchmark.

## Files needed for inference matching

The current matching delivery is `.runtime/ocr-verified-selected-model-20261120.zip`
(round 1 PaddleOCR, run `20261117-031848`). It is unchanged and remains the
version to use until a 5k model replaces it. A matching package has two parts.

**Part A: shared inputs, unchanged by a new model.** Use them from
`.runtime/ocr-matching-final-20261119.zip`:

| File | Purpose |
| --- | --- |
| `reference/bus_information.csv` | Reference services and endpoints to match against |
| `crops/` (valid and test annotation crops) | The images OCR is run on |
| `validation_labels.csv`, `test_labels.csv` | Reviewed text for those crops |
| `inference/panel_inventory.json`, `inference/run_selected_panel_ocr.py`, `inference/environment.json` | Whole-panel crop list, the command that runs OCR on it, and its environment |
| `backend/app/evaluation/ocr_line_layout.py`, `ocr_crop_baseline.py`, `paddle_crop_reader.py` | Line splitting and Paddle reading code used for every crop |
| `review/display_ownership.csv`, `.html`, `review/photos/` | Proposed same-bus grouping; P005/P035/P074/P094 still need human review |
| `matching_outputs.template.csv` | Template for the matcher's results |
| `verify_handoff.py`, `handoff_manifest.json` | Package integrity check |

**Part B: model-specific files.** These must be replaced for the 5k PaddleOCR
model.

**Update, 20 November 2026:** Part B has been generated as a **candidate**
package, `.runtime/ocr-matching-5k-paddle-20261120.zip`, with 552 records. It
does not replace the round 1 delivery. On the same real-photo matching crops,
scored against reviewed labels (scoring-eligible only), the 5k model is not
better than round 1:

| Crops | Round 1 CER | 5k CER | Round 1 exact | 5k exact |
| --- | ---: | ---: | ---: | ---: |
| Validation, n=130 | 0.080 | 0.081 | 0.785 | 0.800 |
| Test, n=45 | 0.082 | 0.100 | 0.822 | 0.756 |

The samples are small, and the test crops were already used to select round 1.
The 5k model's 0.0097 split-validation CER does not carry over to these real
photos. The table below shows the status before generation.

| File | Status for the 5k PaddleOCR model |
| --- | --- |
| `weights/paddleocr/inference.json`, `inference.pdiparams`, `inference.yml`, `provenance.json` | Exist on Drive only, in `paddleocr/ocr5k-split-b32-e20-20261120-084105/best/`. Download all four; Paddle cannot load the model without `inference.json`. |
| `matching_inputs.jsonl` | **Not yet generated.** One record per crop (552 in the current delivery): `record_id`, field, crop, raw and normalised OCR text, `prediction_status`, OCR confidence. It must be produced by running the new weights on the same crop inventory, with the frozen line layout `v4-lines-v3`. |
| `inference/panel_predictions.jsonl` | **Not yet generated.** The new model's whole-panel OCR output, from `run_selected_panel_ocr.py`. |
| `models.lock.json` | **Not yet generated.** SHA-256 hashes of the weights and of `matching_inputs.jsonl`, the training run, and the record count. |
| `README.md` | **Not yet generated.** States which model the package contains. |

Before generating Part B:

1. Reload the downloaded weights and check their SHA-256 hashes against
   `best/provenance.json`.
2. Confirm that none of the matching crops were used to train the 5k model.
   This has not been checked yet.
3. Only replace the delivered model after the 5k model passes the held-out test
   comparison.

## Artefacts (Google Drive, `My Drive/DRIVE/CVDL-OCR-finetune/`)

| Engine | Folder | Model files |
| --- | --- | --- |
| PaddleOCR | `paddleocr/ocr5k-split-b32-e20-20261120-084105/` | `best/inference.json`, `inference.pdiparams`, `inference.yml`, `provenance.json` |
| EasyOCR | `easyocr/ocr5k-split-b32-e20-20261120-084105/` | `best/eds_english_g2.pth`, `.py`, `.yaml`, `README.txt` |
| TrOCR | `trocr/ocr5k-split-b32-e20-20261120-123420/` | `best/` Hugging Face folder (not for use) |

Each folder also has `config.json`, `epoch_log.csv`, `selection.json` and
`validation_events.jsonl`. TrOCR's folder also has `validation_predictions.jsonl`.
The model files are on Drive only and are not in this repository.
