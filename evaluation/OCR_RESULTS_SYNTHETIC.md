# OCR results — synthetic-data benchmark

**Observed evaluation — 18 November 2026:** round 2 is complete. Keep the
round 1 fine-tuned **PaddleOCR**, run `20261117-031848`: test CER **8.2%**,
WER **19.1%**, exact **82.2%**, on 45 human-confirmed annotation crops.
None of the new checkpoints satisfies the agreed replacement rule.

**Project decision:** a synthetic-trained model must beat every other fine-tuned
model on at least two test measures and have CER no worse than its own round 1
version on validation annotation crops and the route hold-out
(`OCR_HANDOFF_TASKS.md`, Round 2). TEST is used for model selection by this rule;
it is not an independent final estimate. Settings and training epochs were not
tuned on TEST. No matching or application integration is included in these scores.

CER/WER are lower-is-better; exact match is higher-is-better. Unicode NFC,
casefold, NFC and whitespace collapse are applied to both reference and OCR;
punctuation is retained. Failed/missing predictions count as empty strings.
Raw OCR is preserved separately. All models use the same crops and frozen
layouts within each population; annotation and detector crops are scored separately.

Validation now uses `v4-lines-v2` for every model/version, fixing the degenerate
A095/P034 regions. Round 1 validation values therefore differ from the earlier
v5 report. TEST and route hold-out layouts are unchanged. Train diagnostics now
apply the four recorded human spot-check overrides; 384 of 387 selected crops
remain eligible. The training labels and model weights are unchanged by rescoring.

## Training dataset composition

**Observed bundle contents:** `ocr_finetune_bundle-20261118-syn.zip`, verified
against its `bundle_manifest.json` and every row of `train.tsv` on 19 November 2026.

| Item | Count |
| --- | ---: |
| Synthetic crops generated | 2,000 |
| Synthetic crops used | 1,988 |
| Synthetic crops skipped | 12 |
| Synthetic line-image/text training pairs | 2,169 |
| Real line-image/text training pairs | 366 |
| Total training pairs | 2,535 |

Synthetic lines account for **85.6%** of training pairs (2,169 / 2,535).
Crops and training lines are different units: a crop can contribute multiple
lines. Nine synthetic crops exceeded PaddleOCR's 40 CTC steps; three had a
region/text-count mismatch. All 12 were skipped for the shared training bundle.
Synthetic data was added to training only; validation, test and route hold-out
remain the existing real-crop evaluation sets. The train diagnostic table also
scores real crops only; it does not include synthetic training images.

These counts describe the prepared bundle. The uploaded TrOCR config records
2,535 effective training pairs, matching it; the supplied configs do not include
an input-bundle hash. Exact training-data identity is therefore not independently
verified from the downloaded weights/logs.

pre = pretrained; fine = fine-tuned on real labels (run 20261117-031848); fine+syn = fine-tuned on real + synthetic lines (`ocr_finetune_bundle-20261118-syn.zip`). Normalised scoring; all values %.

## Table 1a: test annotation crops (official)

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 24 | 3.0 | 0.0 | 0.0 | 8.3 | 0.0 | 0.0 | 91.7 | 100.0 | 100.0 |
| PaddleOCR | destination | 17 | 8.2 | 5.2 | 7.7 | 26.9 | 15.4 | 21.2 | 41.2 | 70.6 | 64.7 |
| PaddleOCR | route | 4 | 29.1 | 24.1 | 24.1 | 72.2 | 55.6 | 50.0 | 0.0 | 25.0 | 25.0 |
| PaddleOCR | **all fields** | 45 | 11.6 | 8.2 | 9.8 | 30.9 | 19.1 | 21.3 | 64.4 | 82.2 | 80.0 |
| TrOCR | number | 24 | 3.0 | 4.5 | 14.9 | 4.2 | 8.3 | 29.2 | 95.8 | 91.7 | 70.8 |
| TrOCR | destination | 17 | 15.5 | 15.5 | 35.6 | 40.4 | 44.2 | 78.8 | 29.4 | 29.4 | 5.9 |
| TrOCR | route | 4 | 38.0 | 34.2 | 48.1 | 72.2 | 61.1 | 88.9 | 25.0 | 25.0 | 0.0 |
| TrOCR | **all fields** | 45 | 17.9 | 17.4 | 34.6 | 37.2 | 38.3 | 68.1 | 64.4 | 62.2 | 40.0 |
| EasyOCR | number | 24 | 7.5 | 3.0 | 4.5 | 16.7 | 8.3 | 12.5 | 83.3 | 91.7 | 87.5 |
| EasyOCR | destination | 17 | 38.6 | 22.7 | 21.0 | 67.3 | 51.9 | 51.9 | 23.5 | 29.4 | 23.5 |
| EasyOCR | route | 4 | 36.7 | 34.2 | 27.8 | 83.3 | 77.8 | 55.6 | 0.0 | 0.0 | 0.0 |
| EasyOCR | **all fields** | 45 | 32.7 | 21.6 | 19.5 | 57.4 | 45.7 | 42.6 | 53.3 | 60.0 | 55.6 |

## Table 1b: validation annotation crops (official)

Validation also chose each model's training epoch, so fine-tuned values are optimistic.

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 43 | 2.6 | 2.6 | 3.5 | 2.3 | 2.3 | 4.7 | 97.7 | 97.7 | 95.3 |
| PaddleOCR | destination | 19 | 14.9 | 12.2 | 9.5 | 33.9 | 22.6 | 17.7 | 57.9 | 57.9 | 68.4 |
| PaddleOCR | route | 17 | 17.0 | 11.3 | 11.7 | 54.9 | 25.5 | 31.4 | 29.4 | 52.9 | 52.9 |
| PaddleOCR | **all fields** | 79 | 13.5 | 10.1 | 9.3 | 32.1 | 17.9 | 18.6 | 73.4 | 78.5 | 79.7 |
| TrOCR | number | 43 | 13.2 | 7.0 | 17.5 | 25.6 | 9.3 | 32.6 | 74.4 | 90.7 | 67.4 |
| TrOCR | destination | 19 | 19.1 | 17.9 | 50.4 | 48.4 | 45.2 | 83.9 | 31.6 | 36.8 | 0.0 |
| TrOCR | route | 17 | 15.0 | 15.4 | 49.0 | 41.2 | 39.2 | 98.0 | 29.4 | 35.3 | 5.9 |
| TrOCR | **all fields** | 79 | 16.4 | 14.9 | 43.8 | 39.7 | 33.3 | 74.4 | 54.4 | 65.8 | 38.0 |
| EasyOCR | number | 43 | 23.7 | 10.5 | 7.9 | 39.5 | 18.6 | 11.6 | 60.5 | 81.4 | 88.4 |
| EasyOCR | destination | 19 | 45.4 | 27.5 | 22.1 | 77.4 | 43.5 | 40.3 | 0.0 | 42.1 | 42.1 |
| EasyOCR | route | 17 | 49.0 | 34.0 | 23.5 | 88.2 | 76.5 | 58.8 | 0.0 | 11.8 | 11.8 |
| EasyOCR | **all fields** | 79 | 42.9 | 27.0 | 20.1 | 70.5 | 47.4 | 38.5 | 32.9 | 57.0 | 60.8 |

## Table 2: validation detector crops (official)

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 33 | 3.4 | 4.6 | 3.4 | 3.0 | 6.1 | 3.0 | 97.0 | 93.9 | 97.0 |
| PaddleOCR | destination | 6 | 29.6 | 21.1 | 14.1 | 68.8 | 43.8 | 37.5 | 33.3 | 50.0 | 50.0 |
| PaddleOCR | route | 12 | 21.2 | 14.5 | 17.6 | 59.5 | 27.0 | 35.1 | 25.0 | 50.0 | 41.7 |
| PaddleOCR | **all fields** | 51 | 18.3 | 13.3 | 13.0 | 39.5 | 22.1 | 23.3 | 72.5 | 78.4 | 78.4 |
| TrOCR | number | 33 | 11.5 | 5.7 | 20.7 | 18.2 | 6.1 | 36.4 | 81.8 | 93.9 | 63.6 |
| TrOCR | destination | 6 | 33.8 | 25.4 | 50.7 | 68.8 | 43.8 | 81.2 | 50.0 | 50.0 | 0.0 |
| TrOCR | route | 12 | 24.8 | 29.1 | 52.1 | 37.8 | 40.5 | 100.0 | 33.3 | 25.0 | 0.0 |
| TrOCR | **all fields** | 51 | 23.2 | 22.0 | 43.3 | 36.0 | 27.9 | 72.1 | 66.7 | 72.5 | 41.2 |
| EasyOCR | number | 33 | 16.1 | 9.2 | 8.0 | 24.2 | 12.1 | 9.1 | 75.8 | 87.9 | 90.9 |
| EasyOCR | destination | 6 | 57.7 | 45.1 | 29.6 | 81.2 | 75.0 | 56.2 | 16.7 | 33.3 | 50.0 |
| EasyOCR | route | 12 | 51.5 | 37.0 | 29.1 | 89.2 | 75.7 | 56.8 | 0.0 | 16.7 | 16.7 |
| EasyOCR | **all fields** | 51 | 43.3 | 31.3 | 23.5 | 62.8 | 51.2 | 38.4 | 51.0 | 64.7 | 68.6 |

## Table 4a: route hold-out, full crops (supplementary)

Single human reviewer; split shows as train because the crops come from train photos.

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | route | 27 | 12.6 | 10.7 | 11.3 | 34.7 | 25.3 | 22.7 | 48.1 | 59.3 | 59.3 |
| PaddleOCR | **all fields** | 27 | 12.6 | 10.7 | 11.3 | 34.7 | 25.3 | 22.7 | 48.1 | 59.3 | 59.3 |
| TrOCR | route | 27 | 24.9 | 23.9 | 54.4 | 56.0 | 48.0 | 104.0 | 18.5 | 29.6 | 0.0 |
| TrOCR | **all fields** | 27 | 24.9 | 23.9 | 54.4 | 56.0 | 48.0 | 104.0 | 18.5 | 29.6 | 0.0 |
| EasyOCR | route | 27 | 33.2 | 22.5 | 19.8 | 80.0 | 54.7 | 50.7 | 3.7 | 25.9 | 25.9 |
| EasyOCR | **all fields** | 27 | 33.2 | 22.5 | 19.8 | 80.0 | 54.7 | 50.7 | 3.7 | 25.9 | 25.9 |

## Table 1c: train (diagnostic only)

AI labels; models were trained on these crops. Not an accuracy result.

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 280 | 11.8 | 8.9 | 11.7 | 16.4 | 9.3 | 11.1 | 84.6 | 93.2 | 92.9 |
| PaddleOCR | destination | 62 | 31.4 | 9.2 | 8.1 | 70.8 | 16.3 | 16.3 | 19.4 | 82.3 | 77.4 |
| PaddleOCR | route | 42 | 23.5 | 13.1 | 13.8 | 59.5 | 22.3 | 31.4 | 31.0 | 81.0 | 71.4 |
| PaddleOCR | **all fields** | 384 | 22.6 | 10.2 | 10.9 | 42.1 | 14.2 | 16.9 | 68.2 | 90.1 | 88.0 |
| TrOCR | number | 280 | 25.6 | 11.0 | 15.3 | 35.0 | 10.0 | 20.4 | 67.9 | 93.2 | 82.5 |
| TrOCR | destination | 62 | 41.1 | 25.1 | 42.6 | 78.1 | 53.9 | 86.5 | 11.3 | 30.6 | 1.6 |
| TrOCR | route | 42 | 30.4 | 20.5 | 49.1 | 63.6 | 38.8 | 91.7 | 28.6 | 64.3 | 7.1 |
| TrOCR | **all fields** | 384 | 32.8 | 19.1 | 35.4 | 54.2 | 29.5 | 55.6 | 54.4 | 79.9 | 61.2 |
| EasyOCR | number | 280 | 33.8 | 10.4 | 10.6 | 46.8 | 11.1 | 10.7 | 56.4 | 92.1 | 92.5 |
| EasyOCR | destination | 62 | 55.6 | 24.1 | 23.2 | 84.3 | 47.8 | 45.5 | 9.7 | 46.8 | 48.4 |
| EasyOCR | route | 42 | 48.8 | 20.8 | 18.6 | 90.1 | 46.3 | 35.5 | 2.4 | 45.2 | 47.6 |
| EasyOCR | **all fields** | 384 | 46.4 | 18.6 | 17.7 | 67.4 | 29.7 | 26.6 | 43.0 | 79.7 | 80.5 |

## Table 4b: route hold-out, partial crops — readable text only (diagnostic)

| Model | Version | n | Readable-text CER | 95% range | All readable correct |
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

## App model selection (step 7)

| Fine-tuned model | Test CER | Test WER | Test exact |
| --- | ---: | ---: | ---: |
| PaddleOCR fine | 8.2 | 19.1 | 82.2 |
| PaddleOCR fine+syn | 9.8 | 21.3 | 80.0 |
| TrOCR fine | 17.4 | 38.3 | 62.2 |
| TrOCR fine+syn | 34.6 | 68.1 | 40.0 |
| EasyOCR fine | 21.6 | 45.7 | 60.0 |
| EasyOCR fine+syn | 19.5 | 42.6 | 55.6 |

- PaddleOCR fine+syn: beats every other fine-tuned model on test (2 of 3): no; validation CER no worse than its round 1 version: yes; route hold-out CER no worse: no → **does not replace**
- TrOCR fine+syn: beats every other fine-tuned model on test (2 of 3): no; validation CER no worse than its round 1 version: no; route hold-out CER no worse: no → **does not replace**
- EasyOCR fine+syn: beats every other fine-tuned model on test (2 of 3): no; validation CER no worse than its round 1 version: yes; route hold-out CER no worse: yes → **does not replace**

With 45 test crops one crop moves exact match by 2.2 points; choosing among more candidates on the same test set makes the winner look better than it is.

## Validation layout v4-lines-v3 (19 November 2026, after round 2 selection)

**Observed:** v2 left four scored validation crops without any line layout, so
every model returned empty text for them: A052 and P046 (both `14E`, same
display), A094 (`choa chu kang int`) and P087 (`marina ctr -`). Each image shows
one main text row. In `v4-lines-v3` each of the four is one full-height line, as in
the automatic proposal and the v2 fix for A095/P034; the other 267 entries are
unchanged (`scripts/make_layout_v4_lines_v3.py`, AI visual review, no human
review). All nine model versions were re-run (`scripts/run_valid_layoutv3.sh`).
In every run only these four predictions changed.

Validation, all fields, normalised scoring (%), v2 → v3:

| Model | Annotation CER fine | Annotation CER fine+syn | Detector CER fine | Detector CER fine+syn | Exact fine (annot. / det.) |
| --- | --- | --- | --- | --- | --- |
| PaddleOCR | 10.1 → 7.2 | 9.3 → 6.4 | 13.3 → 9.6 | 13.0 → 9.3 | 78.5 / 78.4, unchanged |
| TrOCR | 14.9 → 12.0 | 43.8 → 41.9 | 22.0 → 19.5 | 43.3 → 41.8 | 65.8 / 72.5, unchanged |
| EasyOCR | 27.0 → 25.4 | 20.1 → 18.3 | 31.3 → 28.2 | 23.5 → 19.8 | 57.0 / 64.7, unchanged |

Empty output counted as 100% CER for these crops; they now get partial credit.
Fine-tuned PaddleOCR reads none of the four exactly: `148` for `14E` (twice),
`CHOR CHU KANG INT`, `MARINA CTR`. `148` is a different real service in
`data/bus_information.csv`, so number-only matching would accept a wrong bus.
Test, route hold-out and train are unaffected. The step 7 selection check gives
the same outcome under v3 (round 1 PaddleOCR stays). The tables above remain the
v2 values on which round 2 selection was decided.

Scoring: `ocr_scoring/normalised-v8-layoutv3/` (built with
`OCR_VALID_RUN_SUFFIX=-valid-layoutv3 scripts/build_round2_scoring.py`); runs:
`ocr_runs/*-valid-layoutv3/`. Neither is in Git. The app uses automatic
segmentation on new images, not this frozen layout, so v3 changes the
benchmark only, not app behaviour. 16 validation entries remain unresolved.

## Round 2 checkpoint selection (step 5, training validation only)

Observed uploaded configs/logs, run `20261118-084149`:

| Model | Selected epoch | Training validation crop CER (%) | Training validation exact (%) |
| --- | ---: | ---: | ---: |
| EasyOCR | 7 of 10 | 22.8 | 64.6 |
| PaddleOCR | 20 of 20 | 13.5 | 80.0 |
| TrOCR | 1 of 4 | 44.6 | 39.2 |

These are in-training checkpoint-selection values, not the exported-model
scores above. TrOCR's epoch-0 CER was 21.2%; fine-tuning regressed on this run.
Paddle selection.json identifies `best_accuracy`; epoch 20 has the lowest logged
crop CER. No alternative checkpoint was selected after inspecting TEST.

Provenance: configs, selection files and epoch logs are preserved under
`ocr_training/round2-20261118-084149/`, with original filenames and SHA-256 hashes
in `import_manifest.json`. The supplied best/ archives passed CRC; Paddle's
inference files match its provenance hashes. TrOCR reports 2,535 training pairs,
consistent with the prepared 366 real + 2,169 synthetic line pairs. This identifies
the synthetic run by matching metadata; the uploaded configs do not contain an
input-bundle hash, so exact training-data identity is not cryptographically verified.

All 15 new inference runs completed. Two TrOCR train outputs did not emit EOS
within 64 tokens and count as empty predictions; other failed records are frozen
unresolved-layout cases. All 45 comparison runs have identical crop identities
and layouts within their population. Source files and weights were unchanged.
Audit: `ocr_scoring/normalised-v7-round2-syn/run_integrity_audit.json`.
The existing scorer's 17 unit checks passed.

Machine/runtime/timing settings are recorded in each run's `report.json` and
cached `environment.json`. TrOCR and EasyOCR used Mac MPS; PaddleOCR used CPU.
This comparison makes no FPS, end-to-end latency or cross-engine speed claim.

The selected weights remain `.cache/finetuned/paddleocr/`, from
`DRIVE/CVDL-OCR-finetune/paddleocr/20261117-031848/best/`. The existing matching
ZIP `.runtime/ocr-matching-final-20261117.zip` remains the handoff; replacement
weights are unnecessary because the selected model is unchanged.

Scoring evidence: `ocr_scoring/normalised-v7-round2-syn/` contains the shared
manifest, comparisons, per-crop outcomes, partial-crop diagnostics and selection
check. New validation/test predictions are in `ocr_runs/*-finetunedsyn-*`;
train and route hold-out runs are in `.cache/ocr_runs/`.

## Table 3: historical round 1 checkpoint selection (step 5)

Historical training-time geometry and scores, kept for the record; Tables 1–2 and the step 7
section supersede it. Both
columns use the same 130 scored validation crops (79 annotation + 51 detector,
combined), frozen line layouts and normalised scoring. Pretrained values are
recomputed from `ocr_scoring/normalised-v4-valid-human-corrected/scores/text_records.csv`.
Fine-tuned values are the selected checkpoint's validation score from the
Colab training logs, run `20261117-031848`.

| Model | Pretrained crop CER (%) | Fine-tuned crop CER (%) | Change (pts) | Pretrained exact (%) | Fine-tuned exact (%) | Selected epoch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EasyOCR | 43.2 | 29.0 | −14.3 | 40.0 | 60.0 | 10 of 13 (early stop) |
| Public TrOCR | 21.1 | 20.2 | −1.0 | 59.2 | 68.5 | 2 of 5 (early stop) |
| PaddleOCR | 15.0 | 15.2 ‡ | +0.2 | 73.1 | 77.7 | 19 of 20 (tied with epoch 4) |

Notes:

- These validation scores also chose each checkpoint, so the fine-tuned
  figures are optimistic. They are not test results and do not select the app
  model; step 7 uses test annotation crops.
- ‡ **Correction (step 6):** the Paddle figure comes from Paddle's in-training
  evaluation, whose image handling differs from the exported inference model.
  Scored through the evaluation runner on the same 130 crops, fine-tuned
  PaddleOCR gives **11.6%** CER / 78.5% exact (pretrained 15.0% / 73.1%), so
  fine-tuning did improve Paddle. The earlier statement that it did not was a
  measurement artefact. EasyOCR and TrOCR runner scores agree with their logs
  (29.3% vs 29.0%; 20.5% vs 20.2%).
- TrOCR's validation gain was about one point; validation CER rose again after
  epoch 2 while training loss kept falling.
- Check of comparability: the TrOCR training script's epoch-0 pass on the
  untouched model gave 21.25% CER / 59.2% exact versus 21.14% / 59.2% here. The
  0.1-point gap is consistent with one 3 px-tall line image (`P034_00`) being
  read channels-first in training but channels-last by the evaluation runner.
- Validation crops `A095_00` (4 px) and `P034_00` (3 px) are degenerate layout
  regions and count against every model.
- Fine-tuned weights (team Drive, not Git): `DRIVE/CVDL-OCR-finetune/<model>/20261117-031848/best/`
  for `paddleocr`, `trocr` and `easyocr`. An earlier TrOCR run in the same
  folder (no warmup, 65.6% validation CER) was overwritten by this run; only
  its console log survives.
- Training on Colab T4: 366 frozen-layout training line pairs, seed 0, batch 8,
  learning rate 5e-5, at most 20 epochs, no augmentation. TrOCR used 10% warmup.

## Label sources, exclusions and evaluation limits

Validation source: all 258 validation crops were checked by eye by a human reviewer on 16 November 2026 (`ocr_review/human-verification-20261116/`, applied to `validation.source.corrected-P065.csv` with `scripts/apply_validation_human_review.py`). Of the 111 crops that were full and present under the earlier labels, the reviewer gave identical text for 109; 7 of the 111 were reclassified `wrong_field` and A090 was downgraded to partial. 38 crops became newly full and present. Earlier scores used the pre-review labels (`ocr_scoring/normalised-v2-valid`); the tables above replace them.

Training: 387 selected Codex-labelled crops in 129 consistent three-copy groups, saved in `ocr_training/train_labels_final.csv`. Human spot-check of 50 random training labels (cody, 17 November 2026, final export): the human reading agrees with the label text on 41/50 (82%, Wilson 95% 69–90%) when cut-off parts marked [UNK] are ignored (exact agreement 22/50); 4 readings conflict (S018, S041, S046, S050). All 387 training labels are marked full legibility, but the human rated 27/50 (54%, 95% CI 40–67%) partial or illegible. Training labels are unchanged; **train-split scores are diagnostic only**. Details: `ocr_review/train-spotcheck-20261117/` (final: `summary.v3.final.json`). The 117 consistent crops from the original 288-crop quarantine are not used (user decision, 17 November 2026).

Test: all 118 annotation text crops were checked by eye by a human reviewer (cody) on 17 November 2026, starting from Claude AI proposals; the reviewer corrected the proposal on 19 of 118 (16.1%), mostly adding [UNK] and downgrading legibility. One of those 19 (TEST_A0084) differs only by a trailing space. Raw return: `ocr_review/test-confirmation-20261117/test_confirm.cody.2026-11-17.csv`; labels: `ocr_review/test_labels.csv`; scoring source: `ocr_review/test-confirmation-20261117/test.source.confirmed.csv` (built by `scripts/merge_test_labels.py`). Legibility: 45 full, 28 partial, 45 illegible. Scored: 45 crops (24 number, 17 destination, 4 route); route results on 4 crops are not meaningful on their own. Test detector crops are not produced (user decision, 17 November 2026): test results cover annotation-box crops only, i.e. OCR accuracy given a correctly drawn box. Detector-crop results (Table 2) are validation only. Test scores: Table 1 and the step 7 section.

Validation exclusions (counts overlap): `challenge_only`: 26, `legibility_not_full`: 112, `unknown_text`: 112, `validation_train_scene_overlap`: 13, `wrong_field`: 20. Unique excluded crops: 141. Scored: 79 annotation + 51 detector crops. Four scored crops (A052, A094, P046, P087) have an unresolved validation line layout, so no model ran on them; they count as empty predictions for all three models.

Fine-tuning (step 5), fine-tuned runs and scoring (step 6) and model selection (step 7) are complete: the selected app model is fine-tuned PaddleOCR. Matching handoff prepared in `.runtime/ocr-matching-final-20261117.zip`, including weights and whole-display OCR. Display ownership remains a geometry proposal pending confirmation before combining fields; prioritise P005/P035/P074/P094.

User correction: A091 remains wrong_field; P065 (302) is now wrong_field too. The original human export is preserved; the corrected scoring snapshot is `ocr_scoring/normalised-v4-valid-human-corrected/`. Reviewer identity is cody, explicitly confirmed in chat; the original cods export is preserved. P089/P107 suggestions were not applied. Annotation scores are unchanged; detector scored n decreases from 52 to 51.

Route hold-out (Table 4): 139 route crops from train photos never route-labelled (`scripts/build_route_holdout_batch.py`), typed blind by cody on 17 November 2026 and scored without a second review (user decision). Runs: `.cache/ocr_runs/*-routeholdout` and `*-routeholdout-partial` (not in Git). The two crop runners now skip warm-up for fields absent from an inventory, which these route-only runs needed.

Synthetic-data preparation: `scripts/generate_synthetic_eds_crops.py` rendered
2,000 dot-matrix crops from train-label words/combinations, excluding validation,
test and route hold-out strings. `scripts/add_synthetic_to_bundle.py` produced
`ocr_finetune_bundle-20261118-syn.zip` (366 real + 2,169 synthetic training lines
from 1,988 of the 2,000 synthetic crops; 12 skipped: 9 whose joined labels exceed
PaddleOCR's 40 CTC steps and 3 with a region/text-count mismatch). These checkpoints are evaluated
once under the previously fixed rules; improvements or regressions cannot alone
establish a general effect of synthetic data.

Text-overlap check (19 November 2026, after evaluation): round 2 excluded
held-out strings by whole label after NFC, casefold and whitespace collapse.
Under the stricter key in `scripts/synthetic_heldout.py` (letters/digits only,
per line, partial-label fragments of 4+ characters), 61 of the 2,000 synthetic
labels match held-out text as whole labels and 132 match on at least one line or
fragment (113 destination, 19 route). This is shared text, not shared images, but
it may slightly flatter fine+syn validation and hold-out scores. Selection is
unaffected because no synthetic-trained model met the replacement rule. Future
batches use the stricter check (`scripts/intake_synthetic_batch.py`).

Partial-crop diagnostics treat `[UNK]` as a wildcard and score readable text only;
the wildcard can absorb extra text. The 95% ranges use seeded crop bootstrap
resampling. Full hold-out has 27 crops; test route text has only 4. The hold-out
comes from train photos whose number/destination crops may have been used for
training, so it is supplementary, not an independent unseen-scene test. Historical
round 1 confidence intervals remain in `ocr_scoring/route-holdout-20261117/`.
These crop results do not measure missed detections, whole-screen detection,
whole-display OCR accuracy or complete pipeline accuracy. Matching remains
user-owned; display-ownership review remains separate from text review.
