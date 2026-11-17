# OCR results

Scoring: normalised (casefold, whitespace collapsed).
Failed/missing predictions count as empty strings.
"pretrained" = untouched public model; "finetuned" = Colab run `20261117-031848`.

## Table 1: annotation crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained (diagnostic) | train | number | 282 | 34.3 | 47.5 | 56.0 |
| EasyOCR | pretrained (diagnostic) | train | destination | 63 | 55.6 | 84.4 | 9.5 |
| EasyOCR | pretrained (diagnostic) | train | route | 42 | 48.6 | 90.0 | 2.4 |
| EasyOCR | pretrained (diagnostic) | train | all | 387 | 46.5 | 67.7 | 42.6 |
| EasyOCR | pretrained | valid | number | 43 | 23.7 | 39.5 | 60.5 |
| EasyOCR | pretrained | valid | destination | 19 | 45.4 | 77.4 | 0.0 |
| EasyOCR | pretrained | valid | route | 17 | 49.4 | 88.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 79 | 43.0 | 70.5 | 32.9 |
| EasyOCR | pretrained | test | number | 24 | 7.5 | 16.7 | 83.3 |
| EasyOCR | pretrained | test | destination | 17 | 38.6 | 67.3 | 23.5 |
| EasyOCR | pretrained | test | route † | 4 | 36.7 | 83.3 | 0.0 |
| EasyOCR | pretrained | test | all | 45 | 32.7 | 57.4 | 53.3 |
| EasyOCR | finetuned (diagnostic) | train | number | 282 | 10.3 | 11.0 | 92.2 |
| EasyOCR | finetuned (diagnostic) | train | destination | 63 | 23.8 | 47.2 | 47.6 |
| EasyOCR | finetuned (diagnostic) | train | route | 42 | 20.4 | 45.0 | 47.6 |
| EasyOCR | finetuned (diagnostic) | train | all | 387 | 18.3 | 29.2 | 80.1 |
| EasyOCR | finetuned | valid | number | 43 | 10.5 | 18.6 | 81.4 |
| EasyOCR | finetuned | valid | destination | 19 | 27.5 | 43.5 | 42.1 |
| EasyOCR | finetuned | valid | route | 17 | 34.4 | 76.5 | 11.8 |
| EasyOCR | finetuned | valid | all | 79 | 27.1 | 47.4 | 57.0 |
| EasyOCR | finetuned | test | number | 24 | 3.0 | 8.3 | 91.7 |
| EasyOCR | finetuned | test | destination | 17 | 22.7 | 51.9 | 29.4 |
| EasyOCR | finetuned | test | route † | 4 | 34.2 | 77.8 | 0.0 |
| EasyOCR | finetuned | test | all | 45 | 21.6 | 45.7 | 60.0 |
| Public TrOCR | pretrained (diagnostic) | train | number | 282 | 25.8 | 35.5 | 67.4 |
| Public TrOCR | pretrained (diagnostic) | train | destination | 63 | 41.1 | 78.3 | 11.1 |
| Public TrOCR | pretrained (diagnostic) | train | route | 42 | 30.0 | 63.3 | 28.6 |
| Public TrOCR | pretrained (diagnostic) | train | all | 387 | 32.8 | 54.5 | 54.0 |
| Public TrOCR | pretrained | valid | number | 43 | 13.2 | 25.6 | 74.4 |
| Public TrOCR | pretrained | valid | destination | 19 | 19.1 | 48.4 | 31.6 |
| Public TrOCR | pretrained | valid | route | 17 | 23.5 | 49.0 | 29.4 |
| Public TrOCR | pretrained | valid | all | 79 | 19.7 | 42.3 | 54.4 |
| Public TrOCR | pretrained | test | number | 24 | 3.0 | 4.2 | 95.8 |
| Public TrOCR | pretrained | test | destination | 17 | 15.5 | 40.4 | 29.4 |
| Public TrOCR | pretrained | test | route † | 4 | 38.0 | 72.2 | 25.0 |
| Public TrOCR | pretrained | test | all | 45 | 17.9 | 37.2 | 64.4 |
| Public TrOCR | finetuned (diagnostic) | train | number | 282 | 11.0 | 9.9 | 93.3 |
| Public TrOCR | finetuned (diagnostic) | train | destination | 63 | 24.7 | 53.3 | 31.7 |
| Public TrOCR | finetuned (diagnostic) | train | route | 42 | 20.1 | 37.5 | 64.3 |
| Public TrOCR | finetuned (diagnostic) | train | all | 387 | 18.8 | 29.0 | 80.1 |
| Public TrOCR | finetuned | valid | number | 43 | 7.0 | 9.3 | 90.7 |
| Public TrOCR | finetuned | valid | destination | 19 | 17.9 | 45.2 | 36.8 |
| Public TrOCR | finetuned | valid | route | 17 | 21.9 | 41.2 | 35.3 |
| Public TrOCR | finetuned | valid | all | 79 | 17.5 | 34.0 | 65.8 |
| Public TrOCR | finetuned | test | number | 24 | 4.5 | 8.3 | 91.7 |
| Public TrOCR | finetuned | test | destination | 17 | 15.5 | 44.2 | 29.4 |
| Public TrOCR | finetuned | test | route † | 4 | 34.2 | 61.1 | 25.0 |
| Public TrOCR | finetuned | test | all | 45 | 17.4 | 38.3 | 62.2 |
| PaddleOCR | pretrained (diagnostic) | train | number | 282 | 12.0 | 16.7 | 84.4 |
| PaddleOCR | pretrained (diagnostic) | train | destination | 63 | 31.1 | 70.6 | 19.0 |
| PaddleOCR | pretrained (diagnostic) | train | route | 42 | 23.1 | 59.2 | 31.0 |
| PaddleOCR | pretrained (diagnostic) | train | all | 387 | 22.4 | 42.1 | 68.0 |
| PaddleOCR | pretrained | valid | number | 43 | 2.6 | 2.3 | 97.7 |
| PaddleOCR | pretrained | valid | destination | 19 | 14.9 | 33.9 | 57.9 |
| PaddleOCR | pretrained | valid | route | 17 | 17.0 | 54.9 | 29.4 |
| PaddleOCR | pretrained | valid | all | 79 | 13.5 | 32.1 | 73.4 |
| PaddleOCR | pretrained | test | number | 24 | 3.0 | 8.3 | 91.7 |
| PaddleOCR | pretrained | test | destination | 17 | 8.2 | 26.9 | 41.2 |
| PaddleOCR | pretrained | test | route † | 4 | 29.1 | 72.2 | 0.0 |
| PaddleOCR | pretrained | test | all | 45 | 11.6 | 30.9 | 64.4 |
| PaddleOCR | finetuned (diagnostic) | train | number | 282 | 8.8 | 9.2 | 93.3 |
| PaddleOCR | finetuned (diagnostic) | train | destination | 63 | 9.1 | 16.1 | 82.5 |
| PaddleOCR | finetuned (diagnostic) | train | route | 42 | 12.7 | 20.8 | 83.3 |
| PaddleOCR | finetuned (diagnostic) | train | all | 387 | 10.0 | 13.7 | 90.4 |
| PaddleOCR | finetuned | valid | number | 43 | 2.6 | 2.3 | 97.7 |
| PaddleOCR | finetuned | valid | destination | 19 | 12.2 | 22.6 | 57.9 |
| PaddleOCR | finetuned | valid | route | 17 | 11.3 | 25.5 | 52.9 |
| PaddleOCR | finetuned | valid | all | 79 | 10.1 | 17.9 | 78.5 |
| PaddleOCR | finetuned | test | number | 24 | 0.0 | 0.0 | 100.0 |
| PaddleOCR | finetuned | test | destination | 17 | 5.2 | 15.4 | 70.6 |
| PaddleOCR | finetuned | test | route † | 4 | 24.1 | 55.6 | 25.0 |
| PaddleOCR | finetuned | test | all | 45 | 8.2 | 19.1 | 82.2 |

- Train rows are **diagnostic only**: they score against the 387 AI (Codex)
  training labels that the models were fine-tuned on, and a human spot-check
  rated 27/50 of those labels not fully legible. They show fit to the training
  labels, not accuracy.
- Validation and test rows use human-verified labels only. Test covers 45
  fully legible annotation crops; validation 79.
- † Test route results rest on **4 crops** and cannot separate the models.
  They are still included in the test "all" rows.
- Annotation crops are cut from the dataset's labelled boxes: these rows measure
  OCR given a correctly drawn box, not the full detector-plus-OCR pipeline.

## Table 2: detector crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained | valid | number | 33 | 16.1 | 24.2 | 75.8 |
| EasyOCR | pretrained | valid | destination | 6 | 59.2 | 81.2 | 16.7 |
| EasyOCR | pretrained | valid | route | 12 | 51.5 | 89.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 51 | 43.7 | 62.8 | 51.0 |
| EasyOCR | pretrained | test | number | – | Not required | Not required | Not required |
| EasyOCR | pretrained | test | destination | – | Not required | Not required | Not required |
| EasyOCR | pretrained | test | route | – | Not required | Not required | Not required |
| EasyOCR | pretrained | test | all | – | Not required | Not required | Not required |
| EasyOCR | finetuned | valid | number | 33 | 9.2 | 12.1 | 87.9 |
| EasyOCR | finetuned | valid | destination | 6 | 54.9 | 81.2 | 33.3 |
| EasyOCR | finetuned | valid | route | 12 | 37.0 | 75.7 | 16.7 |
| EasyOCR | finetuned | valid | all | 51 | 33.4 | 52.3 | 64.7 |
| EasyOCR | finetuned | test | number | – | Not required | Not required | Not required |
| EasyOCR | finetuned | test | destination | – | Not required | Not required | Not required |
| EasyOCR | finetuned | test | route | – | Not required | Not required | Not required |
| EasyOCR | finetuned | test | all | – | Not required | Not required | Not required |
| Public TrOCR | pretrained | valid | number | 33 | 11.5 | 18.2 | 81.8 |
| Public TrOCR | pretrained | valid | destination | 6 | 36.6 | 68.8 | 50.0 |
| Public TrOCR | pretrained | valid | route | 12 | 24.8 | 37.8 | 33.3 |
| Public TrOCR | pretrained | valid | all | 51 | 23.8 | 36.0 | 66.7 |
| Public TrOCR | pretrained | test | number | – | Not required | Not required | Not required |
| Public TrOCR | pretrained | test | destination | – | Not required | Not required | Not required |
| Public TrOCR | pretrained | test | route | – | Not required | Not required | Not required |
| Public TrOCR | pretrained | test | all | – | Not required | Not required | Not required |
| Public TrOCR | finetuned | valid | number | 33 | 5.7 | 6.1 | 93.9 |
| Public TrOCR | finetuned | valid | destination | 6 | 45.1 | 50.0 | 50.0 |
| Public TrOCR | finetuned | valid | route | 12 | 29.1 | 40.5 | 25.0 |
| Public TrOCR | finetuned | valid | all | 51 | 26.3 | 29.1 | 72.5 |
| Public TrOCR | finetuned | test | number | – | Not required | Not required | Not required |
| Public TrOCR | finetuned | test | destination | – | Not required | Not required | Not required |
| Public TrOCR | finetuned | test | route | – | Not required | Not required | Not required |
| Public TrOCR | finetuned | test | all | – | Not required | Not required | Not required |
| PaddleOCR | pretrained | valid | number | 33 | 3.4 | 3.0 | 97.0 |
| PaddleOCR | pretrained | valid | destination | 6 | 28.2 | 62.5 | 33.3 |
| PaddleOCR | pretrained | valid | route | 12 | 21.2 | 59.5 | 25.0 |
| PaddleOCR | pretrained | valid | all | 51 | 18.0 | 38.4 | 72.5 |
| PaddleOCR | pretrained | test | number | – | Not required | Not required | Not required |
| PaddleOCR | pretrained | test | destination | – | Not required | Not required | Not required |
| PaddleOCR | pretrained | test | route | – | Not required | Not required | Not required |
| PaddleOCR | pretrained | test | all | – | Not required | Not required | Not required |
| PaddleOCR | finetuned | valid | number | 33 | 4.6 | 6.1 | 93.9 |
| PaddleOCR | finetuned | valid | destination | 6 | 26.8 | 62.5 | 50.0 |
| PaddleOCR | finetuned | valid | route | 12 | 14.5 | 27.0 | 50.0 |
| PaddleOCR | finetuned | valid | all | 51 | 14.6 | 25.6 | 78.4 |
| PaddleOCR | finetuned | test | number | – | Not required | Not required | Not required |
| PaddleOCR | finetuned | test | destination | – | Not required | Not required | Not required |
| PaddleOCR | finetuned | test | route | – | Not required | Not required | Not required |
| PaddleOCR | finetuned | test | all | – | Not required | Not required | Not required |

- Detector crops are the YOLO11s validation crops from Brendan's package.
  Test detector crops were not produced (user decision, 17 November 2026), so
  test rows are marked *Not required*.

## App model selection (step 7)

Rule (OCR_HANDOFF_TASKS.md step 7, user-confirmed 17 November 2026): compare
**fine-tuned models only** on the **test annotation crops, All fields row**; the
model better on at least two of CER (lower), WER (lower) and exact match
(higher) wins.

| Fine-tuned model | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | ---: | ---: | ---: | ---: |
| **PaddleOCR** | 45 | **8.2** | **19.1** | **82.2** |
| Public TrOCR | 45 | 17.4 | 38.3 | 62.2 |
| EasyOCR | 45 | 21.6 | 45.7 | 60.0 |

**Selected app model: fine-tuned PaddleOCR (`en_PP-OCRv5_mobile_rec`, run
`20261117-031848`)**, best on all three measures. It is also better than its own
pretrained version on test (11.6 / 30.9 / 64.4) and than every pretrained model,
so no "worse than pretrained" caveat applies. Weights: team Drive
`DRIVE/CVDL-OCR-finetune/paddleocr/20261117-031848/best/` (shareable link still
to add); local copy `.cache/finetuned/paddleocr/` (not in Git). Its test lead is
mainly destinations (exact 70.6% vs 41.2% pretrained, n=17) and bus numbers
(24/24 exact).

Other test observations: fine-tuning clearly helped EasyOCR (CER 32.7 → 21.6).
Fine-tuned TrOCR is not better than pretrained TrOCR on test (CER 17.4 vs 17.9,
but WER 38.3 vs 37.2 and exact 62.2 vs 64.4). With 45 test crops, one crop
changes exact match by 2.2 points; Paddle's margin over the other fine-tuned
models is far larger than that.

Scoring snapshot: `ocr_scoring/normalised-v5-step6-20261117/` (built by
`scripts/build_step6_scoring.py`; manifest, config, per-crop `text_records.csv`).
Pretrained validation cells reproduce the earlier `normalised-v4` snapshot exactly.

## Table 3: fine-tuning checkpoint selection, validation (step 5)

Historical step 5 comparison, kept for the record; Tables 1–2 and the step 7
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

## Label sources and work remaining

Validation source: all 258 validation crops were checked by eye by a human reviewer on 16 November 2026 (`ocr_review/human-verification-20261116/`, applied to `validation.source.corrected-P065.csv` with `scripts/apply_validation_human_review.py`). Of the 111 crops that were full and present under the earlier labels, the reviewer gave identical text for 109; 7 of the 111 were reclassified `wrong_field` and A090 was downgraded to partial. 38 crops became newly full and present. Earlier scores used the pre-review labels (`ocr_scoring/normalised-v2-valid`); the tables above replace them.

Training: 387 selected Codex-labelled crops in 129 consistent three-copy groups, saved in `ocr_training/train_labels_final.csv`. Human spot-check of 50 random training labels (cody, 17 November 2026, final export): the human reading agrees with the label text on 41/50 (82%, Wilson 95% 69–90%) when cut-off parts marked [UNK] are ignored (exact agreement 22/50); 4 readings conflict (S018, S041, S046, S050). All 387 training labels are marked full legibility, but the human rated 27/50 (54%, 95% CI 40–67%) partial or illegible. Training labels are unchanged; **train-split scores are diagnostic only**. Details: `ocr_review/train-spotcheck-20261117/` (final: `summary.v3.final.json`). The 117 consistent crops from the original 288-crop quarantine are not used (user decision, 17 November 2026).

Test: all 118 annotation text crops were checked by eye by a human reviewer (cody) on 17 November 2026, starting from Claude AI proposals; the reviewer corrected the proposal on 19 of 118 (16.1%), mostly adding [UNK] and downgrading legibility. One of those 19 (TEST_A0084) differs only by a trailing space. Raw return: `ocr_review/test-confirmation-20261117/test_confirm.cody.2026-11-17.csv`; labels: `ocr_review/test_labels.csv`; scoring source: `ocr_review/test-confirmation-20261117/test.source.confirmed.csv` (built by `scripts/merge_test_labels.py`). Legibility: 45 full, 28 partial, 45 illegible. Scored: 45 crops (24 number, 17 destination, 4 route); route results on 4 crops are not meaningful on their own. Test detector crops are not produced (user decision, 17 November 2026): test results cover annotation-box crops only, i.e. OCR accuracy given a correctly drawn box. Detector-crop results (Table 2) are validation only. Test scores: Table 1 and the step 7 section.

Validation exclusions (counts overlap): `challenge_only`: 26, `legibility_not_full`: 112, `unknown_text`: 112, `validation_train_scene_overlap`: 13, `wrong_field`: 20. Unique excluded crops: 141. Scored: 79 annotation + 51 detector crops. Four scored crops (A052, A094, P046, P087) have an unresolved validation line layout, so no model ran on them; they count as empty predictions for all three models.

Fine-tuning (step 5), fine-tuned runs and scoring (step 6) and model selection (step 7) are complete: the selected app model is fine-tuned PaddleOCR. Still to do: shareable Drive link to its weights and the step 9 matching handoff.

User correction: A091 remains wrong_field; P065 (302) is now wrong_field too. The original human export is preserved; the corrected scoring snapshot is `ocr_scoring/normalised-v4-valid-human-corrected/`. Reviewer identity is cody, explicitly confirmed in chat; the original cods export is preserved. P089/P107 suggestions were not applied. Annotation scores are unchanged; detector scored n decreases from 52 to 51.

Training preparation: fine-tuning runs on Colab from `colab/ocr_finetune/` on 366 frozen-layout training line pairs (24 of 387 crops skipped and logged). Each model keeps its lowest validation crop-CER checkpoint; test is not used. Fine-tuned checkpoints now exist (Table 3). Test results cover annotation crops only (no test detector crops, by decision). Test labels are confirmed and the training spot-check is returned.
