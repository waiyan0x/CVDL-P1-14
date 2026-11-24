# OCR results — synthetic v2 consolidation

**Status — 19 November 2026:** data preparation and existing benchmark consolidation only. The new 10,000-crop dataset has no returned trained checkpoints or OCR predictions. All new-v2 accuracy cells are **Pending training/evaluation**, not zero.

**Selected matching model remains real-only fine-tuned PaddleOCR**, run `20261117-031848`: test CER 8.2%, WER 19.1%, exact 82.2%, n=45. No v2 model has been selected or passed to matching.

## Data and version definitions

| Version | Training data | Evidence/status |
| --- | --- | --- |
| pre | Original public weights | Existing saved inference |
| fine | 366 real training lines; run 20261117-031848 | Existing saved inference |
| syn1 | 366 real + 2,169 synthetic lines; run 20261118-084149 | Existing saved inference; older 2,000-crop generator |
| syn2 | 366 real + 10,196 synthetic lines | New candidate; training/evaluation pending |

Synthetic v2: 10,000 crops, all export-compatible, producing 10,196 lines; 10,562 total training pairs, 96.5% synthetic. There are 4,000 number crops (60 distinct texts), 4,000 destination crops (268), and 2,000 route crops (8). These are rendered training labels, not human-verified OCR evaluation truth.

**Observed checks:** ZIP CRC, every crop hash, held-out text exclusion, all candidate payload hashes, unchanged real training lines, and unchanged validation inputs relative to the real-v3 base passed. Review status: 100-crop human sample confirmed by user chat attestation; remaining crops not individually reviewed. Original v2 producer source remains outstanding. Audit: [audit.json](ocr_training/synthetic-v2-audit-20261119/audit.json).

## Benchmark protocol

Observed references: [reviewed text-label dataset](ocr_dataset/reviewed-20261119/README.md). Validation has 79 eligible annotation + 51 detector crops; test has 45 eligible annotation crops out of 118 reviewed. Train diagnostics use 384 eligible rows of 387, with the recorded human spot-check overrides. Partial/illegible and other excluded rows remain in the label dataset with reasons.

The same real crops, references and frozen geometry apply to all columns. Validation uses v4-lines-v3, so its older-version numbers are re-scored from v3 runs rather than copied from the historical v1/v2 report. Test and hold-out geometry are unchanged. Prior checkpoints retain their historical training-time validation geometry; v2 training will use v3. Report this protocol difference.

Normalisation: NFC, casefold, NFC, whitespace collapse; punctuation retained. CER/WER are micro edit rates (lower is better); exact match is per crop (higher is better). Failed/missing predictions count as empty. All rates below are percentages. Raw OCR is retained separately; bus_information.csv is a matching reference, not the text answer key. No CSV-corrected accuracy is claimed.

## Table 1a: test annotation crops

Route has only four eligible test crops; interpret separately with caution. syn2 has not been run.

| Model | Field | n | CER pre | CER fine | CER syn1 | CER syn2 | WER pre | WER fine | WER syn1 | WER syn2 | Exact pre | Exact fine | Exact syn1 | Exact syn2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 24 | 3.0 | 0.0 | 0.0 | Pending | 8.3 | 0.0 | 0.0 | Pending | 91.7 | 100.0 | 100.0 | Pending |
| PaddleOCR | destination | 17 | 8.2 | 5.2 | 7.7 | Pending | 26.9 | 15.4 | 21.2 | Pending | 41.2 | 70.6 | 64.7 | Pending |
| PaddleOCR | route | 4 | 29.1 | 24.1 | 24.1 | Pending | 72.2 | 55.6 | 50.0 | Pending | 0.0 | 25.0 | 25.0 | Pending |
| PaddleOCR | **all fields** | 45 | 11.6 | 8.2 | 9.8 | Pending | 30.9 | 19.1 | 21.3 | Pending | 64.4 | 82.2 | 80.0 | Pending |
| TrOCR | number | 24 | 3.0 | 4.5 | 14.9 | Pending | 4.2 | 8.3 | 29.2 | Pending | 95.8 | 91.7 | 70.8 | Pending |
| TrOCR | destination | 17 | 15.5 | 15.5 | 35.6 | Pending | 40.4 | 44.2 | 78.8 | Pending | 29.4 | 29.4 | 5.9 | Pending |
| TrOCR | route | 4 | 38.0 | 34.2 | 48.1 | Pending | 72.2 | 61.1 | 88.9 | Pending | 25.0 | 25.0 | 0.0 | Pending |
| TrOCR | **all fields** | 45 | 17.9 | 17.4 | 34.6 | Pending | 37.2 | 38.3 | 68.1 | Pending | 64.4 | 62.2 | 40.0 | Pending |
| EasyOCR | number | 24 | 7.5 | 3.0 | 4.5 | Pending | 16.7 | 8.3 | 12.5 | Pending | 83.3 | 91.7 | 87.5 | Pending |
| EasyOCR | destination | 17 | 38.6 | 22.7 | 21.0 | Pending | 67.3 | 51.9 | 51.9 | Pending | 23.5 | 29.4 | 23.5 | Pending |
| EasyOCR | route | 4 | 36.7 | 34.2 | 27.8 | Pending | 83.3 | 77.8 | 55.6 | Pending | 0.0 | 0.0 | 0.0 | Pending |
| EasyOCR | **all fields** | 45 | 32.7 | 21.6 | 19.5 | Pending | 57.4 | 45.7 | 42.6 | Pending | 53.3 | 60.0 | 55.6 | Pending |

## Table 1b: validation annotation crops

Validation also selects training epochs; fine-tuned validation results are optimistic.

| Model | Field | n | CER pre | CER fine | CER syn1 | CER syn2 | WER pre | WER fine | WER syn1 | WER syn2 | Exact pre | Exact fine | Exact syn1 | Exact syn2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 43 | 0.9 | 0.9 | 1.8 | Pending | 2.3 | 2.3 | 4.7 | Pending | 97.7 | 97.7 | 95.3 | Pending |
| PaddleOCR | destination | 19 | 8.8 | 6.1 | 3.4 | Pending | 29.0 | 17.7 | 12.9 | Pending | 57.9 | 57.9 | 68.4 | Pending |
| PaddleOCR | route | 17 | 17.0 | 11.3 | 11.7 | Pending | 54.9 | 25.5 | 31.4 | Pending | 29.4 | 52.9 | 52.9 | Pending |
| PaddleOCR | **all fields** | 79 | 10.6 | 7.2 | 6.4 | Pending | 30.1 | 16.0 | 16.7 | Pending | 73.4 | 78.5 | 79.7 | Pending |
| TrOCR | number | 43 | 11.4 | 5.3 | 15.8 | Pending | 25.6 | 9.3 | 32.6 | Pending | 74.4 | 90.7 | 67.4 | Pending |
| TrOCR | destination | 19 | 13.7 | 11.8 | 46.6 | Pending | 46.8 | 40.3 | 83.9 | Pending | 31.6 | 36.8 | 0.0 | Pending |
| TrOCR | route | 17 | 15.0 | 15.4 | 49.0 | Pending | 41.2 | 39.2 | 98.0 | Pending | 29.4 | 35.3 | 5.9 | Pending |
| TrOCR | **all fields** | 79 | 13.8 | 12.0 | 41.9 | Pending | 39.1 | 31.4 | 74.4 | Pending | 54.4 | 65.8 | 38.0 | Pending |
| EasyOCR | number | 43 | 23.7 | 10.5 | 7.9 | Pending | 39.5 | 18.6 | 11.6 | Pending | 60.5 | 81.4 | 88.4 | Pending |
| EasyOCR | destination | 19 | 42.7 | 23.7 | 17.9 | Pending | 77.4 | 43.5 | 38.7 | Pending | 0.0 | 42.1 | 42.1 | Pending |
| EasyOCR | route | 17 | 49.0 | 34.0 | 23.5 | Pending | 88.2 | 76.5 | 58.8 | Pending | 0.0 | 11.8 | 11.8 | Pending |
| EasyOCR | **all fields** | 79 | 41.7 | 25.4 | 18.3 | Pending | 70.5 | 47.4 | 37.8 | Pending | 32.9 | 57.0 | 60.8 | Pending |

## Table 1c: train annotation crops — diagnostic only

AI-assisted references and training examples: not a held-out accuracy estimate.

| Model | Field | n | CER pre | CER fine | CER syn1 | CER syn2 | WER pre | WER fine | WER syn1 | WER syn2 | Exact pre | Exact fine | Exact syn1 | Exact syn2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 280 | 11.8 | 8.9 | 11.7 | Pending | 16.4 | 9.3 | 11.1 | Pending | 84.6 | 93.2 | 92.9 | Pending |
| PaddleOCR | destination | 62 | 31.4 | 9.2 | 8.1 | Pending | 70.8 | 16.3 | 16.3 | Pending | 19.4 | 82.3 | 77.4 | Pending |
| PaddleOCR | route | 42 | 23.5 | 13.1 | 13.8 | Pending | 59.5 | 22.3 | 31.4 | Pending | 31.0 | 81.0 | 71.4 | Pending |
| PaddleOCR | **all fields** | 384 | 22.6 | 10.2 | 10.9 | Pending | 42.1 | 14.2 | 16.9 | Pending | 68.2 | 90.1 | 88.0 | Pending |
| TrOCR | number | 280 | 25.6 | 11.0 | 15.3 | Pending | 35.0 | 10.0 | 20.4 | Pending | 67.9 | 93.2 | 82.5 | Pending |
| TrOCR | destination | 62 | 41.1 | 25.1 | 42.6 | Pending | 78.1 | 53.9 | 86.5 | Pending | 11.3 | 30.6 | 1.6 | Pending |
| TrOCR | route | 42 | 30.4 | 20.5 | 49.1 | Pending | 63.6 | 38.8 | 91.7 | Pending | 28.6 | 64.3 | 7.1 | Pending |
| TrOCR | **all fields** | 384 | 32.8 | 19.1 | 35.4 | Pending | 54.2 | 29.5 | 55.6 | Pending | 54.4 | 79.9 | 61.2 | Pending |
| EasyOCR | number | 280 | 33.8 | 10.4 | 10.6 | Pending | 46.8 | 11.1 | 10.7 | Pending | 56.4 | 92.1 | 92.5 | Pending |
| EasyOCR | destination | 62 | 55.6 | 24.1 | 23.2 | Pending | 84.3 | 47.8 | 45.5 | Pending | 9.7 | 46.8 | 48.4 | Pending |
| EasyOCR | route | 42 | 48.8 | 20.8 | 18.6 | Pending | 90.1 | 46.3 | 35.5 | Pending | 2.4 | 45.2 | 47.6 | Pending |
| EasyOCR | **all fields** | 384 | 46.4 | 18.6 | 17.7 | Pending | 67.4 | 29.7 | 26.6 | Pending | 43.0 | 79.7 | 80.5 | Pending |

## Table 2: detector crops — validation only

No test detector-crop benchmark was requested. This does not measure missed detections or whole-screen detection.

| Model | Field | n | CER pre | CER fine | CER syn1 | CER syn2 | WER pre | WER fine | WER syn1 | WER syn2 | Exact pre | Exact fine | Exact syn1 | Exact syn2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 33 | 0.0 | 2.3 | 1.1 | Pending | 0.0 | 6.1 | 3.0 | Pending | 100.0 | 93.9 | 97.0 | Pending |
| PaddleOCR | destination | 6 | 29.6 | 21.1 | 14.1 | Pending | 68.8 | 43.8 | 37.5 | Pending | 33.3 | 50.0 | 50.0 | Pending |
| PaddleOCR | route | 12 | 15.2 | 8.5 | 11.5 | Pending | 54.1 | 21.6 | 29.7 | Pending | 25.0 | 50.0 | 41.7 | Pending |
| PaddleOCR | **all fields** | 51 | 14.2 | 9.6 | 9.3 | Pending | 36.0 | 19.8 | 20.9 | Pending | 74.5 | 78.4 | 78.4 | Pending |
| TrOCR | number | 33 | 9.2 | 3.4 | 18.4 | Pending | 18.2 | 6.1 | 36.4 | Pending | 81.8 | 93.9 | 63.6 | Pending |
| TrOCR | destination | 6 | 33.8 | 25.4 | 50.7 | Pending | 68.8 | 43.8 | 81.2 | Pending | 50.0 | 50.0 | 0.0 | Pending |
| TrOCR | route | 12 | 19.4 | 25.5 | 50.3 | Pending | 35.1 | 40.5 | 100.0 | Pending | 33.3 | 25.0 | 0.0 | Pending |
| TrOCR | **all fields** | 51 | 19.8 | 19.5 | 41.8 | Pending | 34.9 | 27.9 | 72.1 | Pending | 66.7 | 72.5 | 41.2 | Pending |
| EasyOCR | number | 33 | 14.9 | 9.2 | 8.0 | Pending | 24.2 | 12.1 | 9.1 | Pending | 75.8 | 87.9 | 90.9 | Pending |
| EasyOCR | destination | 6 | 57.7 | 45.1 | 29.6 | Pending | 81.2 | 75.0 | 56.2 | Pending | 16.7 | 33.3 | 50.0 | Pending |
| EasyOCR | route | 12 | 49.1 | 30.9 | 21.8 | Pending | 89.2 | 70.3 | 48.6 | Pending | 0.0 | 16.7 | 25.0 | Pending |
| EasyOCR | **all fields** | 51 | 41.8 | 28.2 | 19.8 | Pending | 62.8 | 48.8 | 34.9 | Pending | 51.0 | 64.7 | 70.6 | Pending |

## Table 4a: route hold-out, full crops — supplementary

One human reviewer, 27 full crops from train photos. Their route text was withheld, but other fields from the photos may have been trained on; this is not unseen-scene independence.

| Model | Field | n | CER pre | CER fine | CER syn1 | CER syn2 | WER pre | WER fine | WER syn1 | WER syn2 | Exact pre | Exact fine | Exact syn1 | Exact syn2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | route | 27 | 12.6 | 10.7 | 11.3 | Pending | 34.7 | 25.3 | 22.7 | Pending | 48.1 | 59.3 | 59.3 | Pending |
| PaddleOCR | **all fields** | 27 | 12.6 | 10.7 | 11.3 | Pending | 34.7 | 25.3 | 22.7 | Pending | 48.1 | 59.3 | 59.3 | Pending |
| TrOCR | route | 27 | 24.9 | 23.9 | 54.4 | Pending | 56.0 | 48.0 | 104.0 | Pending | 18.5 | 29.6 | 0.0 | Pending |
| TrOCR | **all fields** | 27 | 24.9 | 23.9 | 54.4 | Pending | 56.0 | 48.0 | 104.0 | Pending | 18.5 | 29.6 | 0.0 | Pending |
| EasyOCR | route | 27 | 33.2 | 22.5 | 19.8 | Pending | 80.0 | 54.7 | 50.7 | Pending | 3.7 | 25.9 | 25.9 | Pending |
| EasyOCR | **all fields** | 27 | 33.2 | 22.5 | 19.8 | Pending | 80.0 | 54.7 | 50.7 | Pending | 3.7 | 25.9 | 25.9 | Pending |

## Table 4b: route hold-out, partial crops — diagnostic only

Only readable text is scored; [UNK] spans are wildcards. These are not ordinary full-text OCR scores. Ranges are seeded crop-bootstrap 95% intervals.

| Model | Version | n | Readable CER | 95% range | All readable correct |
| --- | --- | ---: | ---: | --- | ---: |
| EasyOCR | pretrained | 49 | 56.7 | 48.2–65.1 | 4.1 |
| EasyOCR | fine-tuned | 49 | 45.0 | 36.3–53.5 | 8.2 |
| EasyOCR | fine-tuned+syn | 49 | 40.1 | 31.7–48.9 | 6.1 |
| TrOCR | pretrained | 49 | 41.3 | 32.9–50.1 | 12.2 |
| TrOCR | fine-tuned | 49 | 38.9 | 30.0–48.1 | 16.3 |
| TrOCR | fine-tuned+syn | 49 | 59.9 | 54.2–65.1 | 2.0 |
| PaddleOCR | pretrained | 49 | 33.0 | 24.0–42.5 | 22.4 |
| PaddleOCR | fine-tuned | 49 | 31.3 | 22.8–40.1 | 22.4 |
| PaddleOCR | fine-tuned+syn | 49 | 28.5 | 20.7–36.5 | 24.5 |
| PaddleOCR | syn2 | 49 planned | Pending | Pending | Pending |
| TrOCR | syn2 | 49 planned | Pending | Pending | Pending |
| EasyOCR | syn2 | 49 planned | Pending | Pending | Pending |

## Table 3: v2 checkpoint selection — step 5

| Model | Run ID | Best epoch | Validation crop CER | Reload/runner check |
| --- | --- | --- | --- | --- |
| PaddleOCR | Pending | Pending | Pending | Pending |
| TrOCR | Pending | Pending | Pending | Pending |
| EasyOCR | Pending | Pending | Pending | Pending |

## Improvement and selection — step 7

Planned v2 batch size is now 32 by user request on 20 November 2026, rather than historical 8. This configuration has not been tested on the T4 at full batch size; CPU smoke checks do not establish memory fit. There are 331 batches per epoch, at most 6,620 across 20 epochs. A changed batch size can alter optimisation and does not guarantee faster training.

Maximum epochs remain 20. All three trainers now implement validation crop-CER early stopping with patience 3 and retain the best checkpoint. Use the updated `ocr_finetune_code-20261120-earlystop.zip` with the current notebook. Paddle early-stop/export integration is locally checked but not yet verified in Colab.

Observed syn1 versus fine: EasyOCR test CER improves 21.6 → 19.5 and WER 45.7 → 42.6, but exact falls 60.0 → 55.6. PaddleOCR regresses on all three test metrics (CER 8.2 → 9.8); TrOCR also regresses (CER 17.4 → 34.6). No v2 improvement can be measured until new checkpoints are trained and evaluated.

**Project decision:** preserve the agreed replacement rule: a new model must beat every other fine-tuned version on at least two of test CER/WER/exact and have validation/route hold-out CER no worse than its own real-only version. TEST was already used for selection and is not an independent final estimate. Do not tune training settings or matching cutoffs on TEST.

The full candidate changes synthetic ratio and optimiser-step budget as well as image rendering. Any gain is a combined experiment result, not proof that v2 rendering alone improved OCR. A matched-data/update-budget control is a proposed follow-up, not a completed run.

## Steps 2–8 and handoff

| Step | Current status |
| --- | --- |
| 2: text labels | Reviewed real references consolidated; synthetic automated checks pass; 100-crop human sample confirmed by user chat attestation; remaining crops not individually reviewed |
| 3: test set | Existing real test/hold-out labels and layouts preserved; no test files in candidate training bundle |
| 4: pretrained baseline | Existing scores reproduced exactly; current v3 validation runs used |
| 5: fine-tuning | Candidate data/code and new Colab notebook prepared; no Colab smoke check, training or reload yet |
| 6: evaluation | New weights/predictions pending; use separate synv2 run directories and fixed real references |
| 7: selection | Pending v2 results; existing real-only PaddleOCR remains selected |
| 8: results | This document consolidates existing measured scores and explicitly pending v2 cells |

Upload instructions, notebook, data/code ZIP hashes and review material: [v2 preparation audit](ocr_training/synthetic-v2-audit-20261119/README.md). The notebook is `colab/ocr_finetune/ocr_finetune_synthetic_v2.ipynb`. Return each best/ ZIP, config, epoch log, selection, RUN_ID and input receipt. The historical synthetic runners hard-code old run names; do not run them unchanged against v2 weights and overwrite/reuse old outputs.

Current matching package: `.runtime/ocr-matching-final-20261119.zip`. Keep its weights and raw/normalised OCR until step 7 selects a replacement. Text labels remain separate from matching inputs. Display ownership still needs human confirmation before fields are combined. No end-to-end pipeline accuracy, latency, FPS or matched-output result is claimed.

## Evidence and reproducibility

Measured cells come from `ocr_scoring/normalised-v8-layoutv3/`: `scores/report.json`, `syn/scores/report.json`, both hold-out reports and `partial/summary.csv`. Dataset/candidate evidence is in `ocr_training/synthetic-v2-audit-20261119/`. Source hashes are recorded in `results_manifest.json` there. Regenerate into a new destination after new inference/scoring; do not relabel pending cells with estimates.
