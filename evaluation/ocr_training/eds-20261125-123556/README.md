# PaddleOCR fine-tune with EDS lines, run `20261125-123556`

Status, 25 November 2026: training finished and the model was exported. **Validation results only**; the test
set was not used. The model has **not** replaced the app model (`models/paddleocr-finetuned`, round 1 run
`20261117-031848`) and has not been evaluated on test.

## What was run

`notebooks/ocr_finetune_eds_no_drive.ipynb` on a Colab T4. It is a copy of `ocr_finetune_eds.ipynb` that
downloads its inputs from the team's public Drive folder instead of mounting Google Drive, and saves to the
Colab disk. Training code and settings are unchanged, except that `common.py` (on the Colab machine only) also
accepts `/content/CVDL-OCR-finetune` as an output folder. During this run that change was pasted into the
training cell by hand; it is now part of the notebook's first code cell. Full cell output: `colab_output.txt`.

| Setting | Value |
| --- | --- |
| Model | `en_PP-OCRv5_mobile_rec`, from the official pretrained checkpoint (SHA-256 `e25c9536…`, same as round 1) |
| PaddleOCR | v3.3.2, commit `95dc316a8490` |
| Paddle | paddlepaddle-gpu 3.2.0 on a Tesla T4 (`Place(gpu:0)`) |
| Training | batch 8, learning rate 5e-5 (cosine), at most 20 epochs, seed 0, no augmentation |
| Selection | lowest validation crop CER; early stop after 3 validations without improvement |

## Inputs

From [the public Drive folder](https://drive.google.com/drive/folders/1YtOoREt07gMIVToH2yD3kUeXTh7FzUGX), each
checked against its SHA-256 before use.

| File | SHA-256 | Contents |
| --- | --- | --- |
| `ocr_finetune_bundle.zip` | `7db8ff38…` | Round 1 real-only bundle |
| `eds_lines.zip` | `44174ece…` | EDS line images (`scripts/cut_eds_lines.py`) |
| `ocr_finetune_code-eds.zip` | `13341d1a…` | `colab/ocr_finetune`, with `add_eds_to_bundle.py` |

Note: the notebook text names the round 1 bundle `ocr_finetune_bundle-old.zip`; on Drive the matching file is
`ocr_finetune_bundle.zip`.

Merged data (`bundle_manifest.json`): **868 training lines** (366 real + 502 EDS: 190 bus number, 244
destination, 68 route), **124 validation lines** from 130 crops (the round 1 real validation set, unchanged),
**no test files**. No characters were added to the dictionary.

## Results

From `selection.json` and `epoch_log.csv`. Training took 269 s.

| Epoch | Train loss | Val line CER | Val crop CER | Val crop exact |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 3.515 | 0.1126 | 0.1649 | 0.615 |
| 2 | 1.944 | 0.0956 | 0.1596 | 0.715 |
| 3 | 1.626 | 0.0956 | 0.1512 | 0.662 |
| 4 | 1.528 | 0.1775 | 0.2389 | 0.215 |
| 5 | 1.376 | 0.0762 | 0.1448 | 0.762 |
| **6** | **1.304** | **0.0785** | **0.1406** | **0.754** |
| 7 | 1.247 | 0.1149 | 0.1786 | 0.615 |
| 8 | 1.247 | 0.0830 | 0.1448 | 0.769 |
| 9 | 1.193 | 0.0933 | 0.1607 | 0.708 |

Selected: epoch 6. Training stopped after epoch 9 (3 validations without improvement).

Compared with earlier runs on the same 130 validation crops (in-training selection values, which are optimistic
for every row because validation also picks the epoch):

| Run | Training data | Crop CER | Crop exact | Selected epoch |
| --- | --- | ---: | ---: | --- |
| Round 1, `20261117-031848` (app model) | 366 real | 15.2% | 77.7% | 19 of 20 |
| Round 2, `20261118-084149` (not adopted) | real + synthetic | 13.5% | 80.0% | 20 of 20 |
| **This run** | 366 real + 502 EDS | **14.1%** | **75.4%** | 6, stopped at 9 |

Sources: `evaluation/OCR_RESULTS.md` (Table 3) and `evaluation/OCR_RESULTS_SYNTHETIC.md`.

## Observations

- Against the app model, crop CER is 1.1 points lower but 3 fewer crops are read exactly (98 against 101 of
  130). On 130 crops that is too small a difference to call either way.
- Validation is noisy: epoch 4 dropped to 21.5% exact before recovering. Round 1's best epoch was 19; this run
  stopped at 9, so patience 3 may have ended it early. A rerun without early stopping (or with more patience)
  would show whether more epochs help.
- These are validation figures. The comparison that decides adoption is the test evaluation (round 1 on test:
  CER 8.2%, exact 82.2%, n = 45).

## Files

| File | What it is |
| --- | --- |
| `best/` | Exported inference model (`inference.json`, `inference.pdiparams`, `inference.yml`, `provenance.json`) |
| `selection.json`, `epoch_log.csv` | Selected epoch and per-epoch validation |
| `config.json`, `paddle_config.yaml` | Arguments, versions and the effective Paddle config |
| `bundle_manifest.json` | Merged data counts, sources and payload hashes |
| `train.tsv`, `dictionary.txt`, `dictionary_check.json` | Training list and character set as used |
| `eval_io_not_ground_truth.tsv` | Paddle's validation input list (not ground truth) |
| `colab_output.txt` | Output of every notebook cell |

`best/inference.pdiparams` SHA-256: `9c607dc6395f0a2a1bebed2d2e098a974feb36974d9d360eeb8587da4aa39f39`.
`inference.json` and `inference.yml` are byte-identical to the app model's; only the weights differ.
