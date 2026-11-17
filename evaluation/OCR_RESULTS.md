# OCR results

## Headline result (test, official)

Test annotation crops, all fields, 45 human-confirmed crops. pre = pretrained
public model, fine = fine-tuned. CER and WER: lower is better; Exact: higher is
better. All in %.

| Model | Field | n | CER pre | CER fine | WER pre | WER fine | Exact pre | Exact fine |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | all fields | 45 | 11.6 | **8.2** | 30.9 | **19.1** | 64.4 | **82.2** |
| TrOCR | all fields | 45 | 17.9 | 17.4 | 37.2 | 38.3 | 64.4 | 62.2 |
| EasyOCR | all fields | 45 | 32.7 | 21.6 | 57.4 | 45.7 | 53.3 | 60.0 |

**Selected app model: fine-tuned PaddleOCR**, best on all three rates. Per-field
results, validation and train are in Tables 1–2 below.

**How to read the tables.** Each rate is shown twice, side by side: **pre** =
the untouched public (pretrained) model, **fine** = the same model fine-tuned on
our training labels (Colab run `20261117-031848`). Both columns score exactly
the same crops, so each pair is a like-for-like comparison.

- **CER** (character error rate) and **WER** (word error rate): lower is better.
  **Exact**: share of crops read completely correctly; higher is better. All in %.
- Text is normalised before comparison (Unicode NFC, casefold, whitespace
  collapsed; punctuation kept). A failed or missing prediction counts as empty text.
- Only crops whose label is fully legible (no `[UNK]`) are scored; n is the number scored.
- Models are PaddleOCR (`en_PP-OCRv5_mobile_rec`), TrOCR (`microsoft/trocr-base-printed`)
  and EasyOCR (English generation 2).

### Official vs diagnostic results

| Split | Labels | Status | Use it for |
| --- | --- | --- | --- |
| **Test** | Checked by eye by a human (118 crops; 45 scored) | **Official** | Final comparison and model selection |
| **Validation** | Checked by eye by a human (258 crops; 79 annotation + 51 detector scored) | **Official** | Comparison; was also used to pick each model's best training epoch |
| **Train** | AI-generated (Codex), not human-verified (387 crops) | **Diagnostic only** | Checking that fine-tuning learned the training labels; **not** an accuracy result |
| **Route hold-out** | Typed blind by one human (139 route crops; 27 scored) | **Supplementary** | Comparing models on route text, where test has only 4 crops (Table 4) |

Train results are **diagnostic** for two reasons. (1) The fine-tuned models were
trained on these very crops and labels, so their train scores measure how well
they fit what they were taught, not how well they read unseen signs; a large
pre → fine gain on train is expected and proves little. (2) The labels are AI
readings, and a human spot-check of 50 found the text consistent on 41 but rated
27 of the 50 as not fully legible, so the "correct answer" itself is uncertain.
Step 8 asks for train results to be included, so they are shown in Table 1c,
separately, and must not be quoted as model accuracy or used to choose a model.

## Table 1: annotation crops

Annotation crops are cut from the dataset's hand-labelled boxes, so these
results measure OCR given a correctly drawn box.

### Table 1a: test (official)

| Model | Field | Crops (n) | CER pre | CER fine | WER pre | WER fine | Exact pre | Exact fine |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 24 | 3.0 | 0.0 | 8.3 | 0.0 | 91.7 | 100.0 |
| PaddleOCR | destination | 17 | 8.2 | 5.2 | 26.9 | 15.4 | 41.2 | 70.6 |
| PaddleOCR | route † | 4 | 29.1 | 24.1 | 72.2 | 55.6 | 0.0 | 25.0 |
| PaddleOCR | **all fields** | 45 | **11.6** | **8.2** | **30.9** | **19.1** | **64.4** | **82.2** |
| TrOCR | number | 24 | 3.0 | 4.5 | 4.2 | 8.3 | 95.8 | 91.7 |
| TrOCR | destination | 17 | 15.5 | 15.5 | 40.4 | 44.2 | 29.4 | 29.4 |
| TrOCR | route † | 4 | 38.0 | 34.2 | 72.2 | 61.1 | 25.0 | 25.0 |
| TrOCR | **all fields** | 45 | **17.9** | **17.4** | **37.2** | **38.3** | **64.4** | **62.2** |
| EasyOCR | number | 24 | 7.5 | 3.0 | 16.7 | 8.3 | 83.3 | 91.7 |
| EasyOCR | destination | 17 | 38.6 | 22.7 | 67.3 | 51.9 | 23.5 | 29.4 |
| EasyOCR | route † | 4 | 36.7 | 34.2 | 83.3 | 77.8 | 0.0 | 0.0 |
| EasyOCR | **all fields** | 45 | **32.7** | **21.6** | **57.4** | **45.7** | **53.3** | **60.0** |

† Test route text has only **4** scorable crops: too few to compare models on
their own. They are still included in "all fields". For route text, see the
27-crop route hold-out in Table 4.

### Table 1b: validation (official)

| Model | Field | Crops (n) | CER pre | CER fine | WER pre | WER fine | Exact pre | Exact fine |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 43 | 2.6 | 2.6 | 2.3 | 2.3 | 97.7 | 97.7 |
| PaddleOCR | destination | 19 | 14.9 | 12.2 | 33.9 | 22.6 | 57.9 | 57.9 |
| PaddleOCR | route | 17 | 17.0 | 11.3 | 54.9 | 25.5 | 29.4 | 52.9 |
| PaddleOCR | **all fields** | 79 | **13.5** | **10.1** | **32.1** | **17.9** | **73.4** | **78.5** |
| TrOCR | number | 43 | 13.2 | 7.0 | 25.6 | 9.3 | 74.4 | 90.7 |
| TrOCR | destination | 19 | 19.1 | 17.9 | 48.4 | 45.2 | 31.6 | 36.8 |
| TrOCR | route | 17 | 23.5 | 21.9 | 49.0 | 41.2 | 29.4 | 35.3 |
| TrOCR | **all fields** | 79 | **19.7** | **17.5** | **42.3** | **34.0** | **54.4** | **65.8** |
| EasyOCR | number | 43 | 23.7 | 10.5 | 39.5 | 18.6 | 60.5 | 81.4 |
| EasyOCR | destination | 19 | 45.4 | 27.5 | 77.4 | 43.5 | 0.0 | 42.1 |
| EasyOCR | route | 17 | 49.4 | 34.4 | 88.2 | 76.5 | 0.0 | 11.8 |
| EasyOCR | **all fields** | 79 | **43.0** | **27.1** | **70.5** | **47.4** | **32.9** | **57.0** |

### Table 1c: train (diagnostic only — see "Official vs diagnostic results")

| Model | Field | Crops (n) | CER pre | CER fine | WER pre | WER fine | Exact pre | Exact fine |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 282 | 12.0 | 8.8 | 16.7 | 9.2 | 84.4 | 93.3 |
| PaddleOCR | destination | 63 | 31.1 | 9.1 | 70.6 | 16.1 | 19.0 | 82.5 |
| PaddleOCR | route | 42 | 23.1 | 12.7 | 59.2 | 20.8 | 31.0 | 83.3 |
| PaddleOCR | **all fields** | 387 | **22.4** | **10.0** | **42.1** | **13.7** | **68.0** | **90.4** |
| TrOCR | number | 282 | 25.8 | 11.0 | 35.5 | 9.9 | 67.4 | 93.3 |
| TrOCR | destination | 63 | 41.1 | 24.7 | 78.3 | 53.3 | 11.1 | 31.7 |
| TrOCR | route | 42 | 30.0 | 20.1 | 63.3 | 37.5 | 28.6 | 64.3 |
| TrOCR | **all fields** | 387 | **32.8** | **18.8** | **54.5** | **29.0** | **54.0** | **80.1** |
| EasyOCR | number | 282 | 34.3 | 10.3 | 47.5 | 11.0 | 56.0 | 92.2 |
| EasyOCR | destination | 63 | 55.6 | 23.8 | 84.4 | 47.2 | 9.5 | 47.6 |
| EasyOCR | route | 42 | 48.6 | 20.4 | 90.0 | 45.0 | 2.4 | 47.6 |
| EasyOCR | **all fields** | 387 | **46.5** | **18.3** | **67.7** | **29.2** | **42.6** | **80.1** |

## Table 2: detector crops (validation, official)

Detector crops are the YOLO11s validation crops from Brendan's package: the
boxes the detector actually produced, so these results include the effect of
imperfect boxes. Test detector crops were not produced (user decision,
17 November 2026), so there is no test row.

| Model | Field | Crops (n) | CER pre | CER fine | WER pre | WER fine | Exact pre | Exact fine |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 33 | 3.4 | 4.6 | 3.0 | 6.1 | 97.0 | 93.9 |
| PaddleOCR | destination | 6 | 28.2 | 26.8 | 62.5 | 62.5 | 33.3 | 50.0 |
| PaddleOCR | route | 12 | 21.2 | 14.5 | 59.5 | 27.0 | 25.0 | 50.0 |
| PaddleOCR | **all fields** | 51 | **18.0** | **14.6** | **38.4** | **25.6** | **72.5** | **78.4** |
| TrOCR | number | 33 | 11.5 | 5.7 | 18.2 | 6.1 | 81.8 | 93.9 |
| TrOCR | destination | 6 | 36.6 | 45.1 | 68.8 | 50.0 | 50.0 | 50.0 |
| TrOCR | route | 12 | 24.8 | 29.1 | 37.8 | 40.5 | 33.3 | 25.0 |
| TrOCR | **all fields** | 51 | **23.8** | **26.3** | **36.0** | **29.1** | **66.7** | **72.5** |
| EasyOCR | number | 33 | 16.1 | 9.2 | 24.2 | 12.1 | 75.8 | 87.9 |
| EasyOCR | destination | 6 | 59.2 | 54.9 | 81.2 | 81.2 | 16.7 | 33.3 |
| EasyOCR | route | 12 | 51.5 | 37.0 | 89.2 | 75.7 | 0.0 | 16.7 |
| EasyOCR | **all fields** | 51 | **43.7** | **33.4** | **62.8** | **52.3** | **51.0** | **64.7** |

## Table 4: route hold-out (supplementary)

Test has only 4 scorable route crops, so a separate route set was labelled. It
is **not** the official test set and does not change the step 7 selection; it
confirms it for route text.

- **Crops:** 139 route crops, one per train photo whose route crop was never
  labelled (the AI labelling could not agree on it). Their route text never
  entered fine-tuning.
- **Labels:** typed blind (no AI or OCR suggestion) by one human reviewer (cody),
  17 November 2026, with no second review. Legibility: 27 full, 49 partial, 63 illegible.
- **Runs:** same weights, settings and frozen automatic line layout as the test
  runs, with no prediction failures.
- **95% range:** crop-level bootstrap, 5,000 resamples, seed 0.

### Table 4a: full-legibility crops (normalised scoring, n = 27)

| Model | CER pre | CER fine | WER pre | WER fine | Exact pre | Exact fine |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | 12.6 | **10.7** | 34.7 | **25.3** | 48.1 | **59.3** |
| TrOCR | 24.9 | 23.9 | 56.0 | 48.0 | 18.5 | 29.6 |
| EasyOCR | 33.2 | 22.5 | 80.0 | 54.7 | 3.7 | 25.9 |

95% ranges for CER: PaddleOCR 5.0–21.7 (pre), 3.5–19.1 (fine); TrOCR 13.8–37.0,
12.6–35.6; EasyOCR 22.3–44.8, 12.9–33.1.

Paired CER differences on the same crops (95% range):

| Comparison | Difference (pts) | 95% range | Distinguishable? |
| --- | ---: | --- | --- |
| PaddleOCR fine − EasyOCR fine | −11.8 | −17.0 to −7.0 | Yes |
| PaddleOCR fine − TrOCR fine | −13.1 | −21.2 to −6.2 | Yes |
| PaddleOCR pre − TrOCR pre | −12.3 | −20.6 to −5.5 | Yes |
| EasyOCR fine − EasyOCR pre | −10.7 | −15.1 to −6.6 | Yes |
| PaddleOCR fine − PaddleOCR pre | −1.9 | −3.6 to −0.3 | Yes (small) |
| TrOCR fine − TrOCR pre | −1.1 | −4.5 to +2.1 | No |

### Table 4b: partial-legibility crops, readable text only (diagnostic, n = 49)

Not an official metric: official scoring excludes every crop containing `[UNK]`.
Each `[UNK]` is treated as a wildcard that matches any text at no cost, so only
the 578 readable characters are scored. "All readable" = every readable
character correct.

| Model | Readable-text CER pre | Readable-text CER fine | All readable pre | All readable fine |
| --- | ---: | ---: | ---: | ---: |
| PaddleOCR | 33.0 | **31.3** | 22.4 | **22.4** |
| TrOCR | 41.3 | 38.9 | 12.2 | 16.3 |
| EasyOCR | 56.7 | 45.0 | 4.1 | 8.2 |

Paired differences: PaddleOCR fine is lower than TrOCR fine by 7.6 points
(95% range −11.6 to −3.6) and EasyOCR fine by 13.7 (−18.6 to −8.6). Fine-tuning
helps EasyOCR (−11.8, −17.1 to −7.0). For TrOCR (−2.4) and PaddleOCR (−1.7) the
fine-tuning effect cannot be told apart from zero here. The wildcard can absorb
made-up text next to an `[UNK]`, so these values flatter every model; only the
ranking is meaningful.

**Reading Table 4:** PaddleOCR is clearly the best on route text, consistent with
validation (Table 1b). The 4-crop test route row had EasyOCR roughly level with
the others; on 27 crops it is clearly worse than PaddleOCR.

**Limitations:** single reviewer; these buses' number and destination crops were
in fine-tuning (route text was not); likely harder than average because they are
crops the AI labelling could not agree on; one crop per photo, so 32 photos with
two or more route boxes contribute only their largest. Scores, method and
per-crop outputs: `ocr_scoring/route-holdout-20261117/` (README, `scores/`,
`partial/`); labels: `ocr_review/route-holdout-20261117/`.

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
`DRIVE/CVDL-OCR-finetune/paddleocr/20261117-031848/best/`; local copy
`.cache/finetuned/paddleocr/` (not in Git). The final matching handoff ZIP
`.runtime/ocr-matching-final-20261117.zip` includes these weights directly;
a shareable Drive URL remains an optional follow-up. Its test lead is
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

Fine-tuning (step 5), fine-tuned runs and scoring (step 6) and model selection (step 7) are complete: the selected app model is fine-tuned PaddleOCR. Matching handoff prepared in `.runtime/ocr-matching-final-20261117.zip`, including weights and whole-display OCR. Display ownership remains a geometry proposal pending confirmation before combining fields; prioritise P005/P035/P074/P094.

User correction: A091 remains wrong_field; P065 (302) is now wrong_field too. The original human export is preserved; the corrected scoring snapshot is `ocr_scoring/normalised-v4-valid-human-corrected/`. Reviewer identity is cody, explicitly confirmed in chat; the original cods export is preserved. P089/P107 suggestions were not applied. Annotation scores are unchanged; detector scored n decreases from 52 to 51.

Route hold-out (Table 4): 139 route crops from train photos never route-labelled (`scripts/build_route_holdout_batch.py`), typed blind by cody on 17 November 2026 and scored without a second review (user decision). Runs: `.cache/ocr_runs/*-routeholdout` and `*-routeholdout-partial` (not in Git). The two crop runners now skip warm-up for fields absent from an inventory, which these route-only runs needed.

Synthetic training data (not yet trained): 2,000 rendered dot-matrix crops with ground truth in `labels.csv` format (`scripts/generate_synthetic_eds_crops.py`, `.runtime/synthetic-eds-20261117/`). Text comes from train labels plus combinations of train-only words, excluding every validation, test and route hold-out string. `scripts/add_synthetic_to_bundle.py` adds them to `.runtime/ocr_finetune_bundle-20261117-syn.zip` (366 real + 2,178 synthetic train line pairs; validation unchanged), which the Colab notebook now expects. No model has been trained on it yet, so no table reports synthetic-data results. Once trained, score on the same test and route hold-out sets for comparison with the run above.

Training preparation: fine-tuning runs on Colab from `colab/ocr_finetune/` on 366 frozen-layout training line pairs (24 of 387 crops skipped and logged). Each model keeps its lowest validation crop-CER checkpoint; test is not used. Fine-tuned checkpoints now exist (Table 3). Test results cover annotation crops only (no test detector crops, by decision). Test labels are confirmed and the training spot-check is returned.
