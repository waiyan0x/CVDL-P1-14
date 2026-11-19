# Remaining OCR and matching work

Authority: user instructions, parts 1–3, received 16 November 2026. These are
project decisions, not observed results or coursework rubric requirements.
This checklist supersedes earlier conflicting OCR scoring/handoff proposals.
No task below is marked complete merely because this checklist exists.

## Round 2: synthetic training data (evaluated 18 November 2026)

Observed evaluation: run `20261118-084149` configs/logs and all three best/ ZIPs
are registered in `evaluation/ocr_training/round2-20261118-084149/`.
All 15 new inference runs completed; 45 comparison runs share exact crop
identities/layouts within each population. Results/audit:
`evaluation/ocr_scoring/normalised-v7-round2-syn/` and `evaluation/OCR_RESULTS_SYNTHETIC.md`.
Round 1 PaddleOCR remains selected; no synthetic-trained model meets the agreed
replacement rule. TrOCR's 2,535 training pairs match the prepared synthetic
bundle count; the uploaded configs do not contain an input-bundle hash.

Only the training data changes. Test, validation, route hold-out, frozen layouts
and scoring stay as in round 1, so differences come from the synthetic lines.
Decisions confirmed by the user, 18 November 2026 (fixed before any round 2 results):
- Training: full `-syn` bundle, PaddleOCR first, same settings as round 1.
- Validation: fixed layout `v4-lines-v2` for all three columns (pre / fine /
  fine+syn). Round 1 validation figures therefore shift slightly from the
  published v5 tables; the write-up states why. Test is unaffected.
- Selection (strict): the round 1 app model stays unless a synthetic-trained
  model wins 2 of 3 test measures (all fields) against every other fine-tuned
  model AND is no worse in CER on validation and the route hold-out.
- Hand-back: the three `best-*.zip` downloads, the RUN_ID and, ideally, the three
  `epoch_log.csv` files. The weights are needed for test and hold-out scoring.

- [x] Step 2: synthetic labels (`.runtime/synthetic-eds-20261117/labels.csv`, 2,000
  crops; validation/test/hold-out strings excluded). Real labels unchanged.
- [x] Step 3: unchanged (118 test crops, frozen layouts); route hold-out fixed.
- [x] Step 4: unchanged; pretrained runs reused.
- [x] Step 5 prep: bundle `.runtime/ocr_finetune_bundle-20261118-syn.zip`
  (366 real + 2,169 synthetic train pairs; SHA `ca6d3604…`); notebook pins it.
  Replaces the 17 November `-syn` bundle, whose 9 joined synthetic labels exceeded
  PaddleOCR's 40 CTC steps and stopped the dry run; those crops are now skipped.
  A further 3 synthetic crops are skipped for a region/text-count mismatch, so
  12 of 2,000 are skipped in total (1,988 used; `bundle_manifest.json`).
- [x] **Step 5 (user, Colab):** train PaddleOCR, TrOCR, EasyOCR on the `-syn`
  bundle; download each `best/` folder; note the run ID.
- [x] **Disk (user):** free at least ~5 GB. TrOCR needs 3 GB free to load, and the
  synthetic-trained TrOCR adds about 1.3 GB. On 18 November only 2.6 GB was free,
  which blocked `trocr-finetuned-valid-layoutv2`.
- [x] Round 1 completion: run `trocr-finetuned-valid-layoutv2` (pretrained done
  18 November), so all validation runs use layout `v4-lines-v2`.
- [x] Step 6: `scripts/import_synthetic_finetuned.py RUN_ID best-*.zip`, then
  `scripts/run_synthetic_finetuned_ocr.sh RUN_ID` (valid layout v2, test, hold-out
  full + partial, train; never overwrites round 1 runs).
- [x] Steps 6–7: `scripts/build_round2_scoring.py evaluation/ocr_scoring/normalised-v7-round2-syn`
  writes the round 1 v6 snapshot plus `syn/`, `holdout/`, `partial/` and
  `ROUND2_RESULTS.md` (three-way tables and the selection check). Dry-run
  verified 18 November with stand-in runs; missing models show `pending`.
- [x] Step 8: save the three-way tables separately in `evaluation/OCR_RESULTS_SYNTHETIC.md` (linked from `evaluation/OCR_RESULTS.md`) and record
  synthetic provenance and limits.
- Step 9: no rebuild required; the selected model is unchanged.

## Status and dependencies

Current audit — 17 November 2026: steps 2–8 are complete for the agreed scope
(test annotation crops only). All 18 saved runs have identical crop identities
and layouts within each split; all six model scores reproduce exactly.
Final matching package: `.runtime/ocr-matching-final-20261119.zip` (rebuilt 19 November
2026 with validation layout v4-lines-v3; supersedes `-20261117`, which used v4-lines-v1).
It includes 389 text-field records and 163 whole-display records, separate
validation/test labels, reference data, source photos, selected weights and a
new-crop command. Matching implementation belongs to the user.

- [ ] Complete step 9 display-ownership confirmation where fields will be combined.
  The package is ready for matching development with candidate IDs; human-confirmed
  ownership is not claimed. Prioritise P005/P035/P074/P094 in
  `review/display_ownership.html`; uncertain cases may remain unresolved.
- User clarification: requested visual checks require a human. Codex inspection
  does not satisfy them. Prepare review material and record actual human returns;
  never mark these checks complete from AI inspection.
- [x] Obtain Brendan's archive. Quarantine question dropped by user; no additions.
- [x] Identify team Drive destination: `DRIVE/CVDL-OCR-finetune/`.
  A shareable URL remains unavailable; the final package includes the selected
  weights directly, so downloading them is not a matching dependency.
- Preserve actual AI/human provenance even though the user adopts the selected
  AI labels as project ground truth. Prior human-review gates must not silently
  prevent the newly requested scoring.
- Approximate counts and CER values below are expectations to investigate,
  never targets to achieve by changing labels or omitting failures.
- Selecting the OCR winner on TEST follows the user's rule; report that this
  uses TEST for model selection, not as an independent final estimate. Do not
  use TEST to tune settings, train, or choose checkpoints.

## Historical progress — 16 November 2026 (superseded by current audit above)

- Step 1 implemented: validation sanity-check CER 10.7% TrOCR / 31.5% EasyOCR
  when combining populations for this check; published tables keep them separate.
- Training selection saved: 387 crops / 129 literal-consistency triplets from the
  specified training.source.csv. Human 50-crop spot-check prepared, not returned.
  Another 117 consistent crops remain held from the original 288 quarantine.
- Three existing pretrained validation runs copied to requested run directories.
- Exporter imported from Brendan branch and extended to test; OCR runners and
  automatic layout CLI accept test. Detector test export has not been run.
- Latest Brendan branches fetched and inspected: bren-object-detection 762a93e,
  bren-data-preparation f2e4ef0. Branch docs explicitly say full source ZIP and
  YOLO11s checkpoint are local Windows artifacts, not in Git; no download link
  found in the handoff docs. Local cached test annotation export has 118 text
  crops and 53 panels. No test OCR or fine-tuning is claimed.
- Quarantine comparison against cached v4 test crop metadata finds zero exact
  source-name/hash overlaps; related-photo identity still needs confirmation.

## 1. Scoring

- [x] Remove eligibility requirements for second reviewer, group_review_status,
  correspondence_status, attestation and field_review_status=reviewed.
- [x] Exclude only legibility other than full, [UNK], blank, wrong_field and
  challenge_only (26 mixed-field / OFF SERVICE crops). Also apply the explicit
  validation scene-overlap removal in step 2.
- [x] Score normalised text only: casefold and collapse whitespace. Drop raw
  scoring mode; retain exact raw OCR outputs in saved predictions/handoff.
- [x] Failed or missing predictions count as empty strings.
- [x] Check existing validation runs: expected approximately TrOCR 10% CER and
  EasyOCR 31% CER. Investigate differences; eligible rows must produce numbers,
  not pending cells.

## 2. Labels

- [x] From training.source.csv retain full-legibility, no-[UNK], non-challenge
  rows. Group by (source_name, label); keep groups with the same Codex text on
  all three augmented copies (expected approximately 345 crops).
- [x] Prepare 50 randomly sampled crops for human spot-check; record sample seed,
  actual human decisions and percent correct in results, with reviewer provenance.
  Returned 17 November 2026 (cody, final v3 export): text consistent with label
  on 41/50, 4 conflicts, 27/50 rated partial/illegible although labelled full.
  Train scores are therefore diagnostic only. See
  evaluation/ocr_review/train-spotcheck-20261117/README.md.
- [x] ~~Ask Brendan whether the 288 quarantined crops share photos with v4 TEST.~~
  Dropped by the user, 17 November 2026: no question to Brendan needed; training
  uses the 387 selected crops from his package. The 288 quarantined crops are
  not added.
- [x] Save evaluation/ocr_training/train_labels_final.csv with crop, field,
  text, source_name.
- [x] Validation: use the user's 194 typed labels plus 77 Codex labels; visually
  confirm each by human review. Do not use the Codex re-read as the answer key.
  Done 16 November 2026 (258 crops, reviewer cody; P065 correction).
- [x] Remove A042–A048 and P039–P044 from validation for train scene overlap.

## 3. Test set

- [x] Obtain Brendan's .runtime/ocr_class_dataset/v4-reviewed-01.zip, test/.
- [x] ~~Export YOLO11s test detector crops.~~ Not required (user decision,
  17 November 2026). Test uses Brendan's 118 test annotation-box text crops
  only; detector-crop results (Table 2) are validation only. The checkpoint and
  test photos are in the handoff ZIP if this is ever revisited.
- [x] Freeze test layouts once with freeze_automatic_ocr_layout.py and reuse
  the exact crops/layout for all models.
- [x] Label test text crops with Codex, then have a human check every crop
  (approximately 120 expected). Do not prefill labels from EasyOCR, TrOCR or
  Paddle predictions.
- [x] ~~Detector crops receive the text of the overlapping annotation box.~~
  Not required: no test detector crops (see above).
- [x] Save evaluation/ocr_review/test_labels.csv with review_id, crop, field,
  input_set, text, legibility.
- [x] Keep TEST out of training and all setting/checkpoint choices.

## 4. Pretrained baselines

- [x] Run EasyOCR, TrOCR trocr-base-printed and Paddle en_PP-OCRv5_mobile_rec
  on train, validation and test (detector crops: validation only).
- [x] Use run_easyocr_crops.py (--engine easyocr / trocr) and
  run_paddle_crops.py, supporting --split and --crop-root.
- [x] Use identical crops and frozen layouts for every model.
- [x] Commit predictions.jsonl and report.json under
  evaluation/ocr_runs/<model>-pretrained-<split>/, including the existing
  laptop-only Paddle validation run.

## 5. Fine-tune all three models

- [x] Train on train_labels_final.csv; validate on the step 2 validation set.
- [x] Match evaluation input format: where inference splits crops into lines,
  train on line images with one text line each.
- [x] TrOCR: HF VisionEncoderDecoderModel + Seq2SeqTrainer from
  trocr-base-printed; start lr 5e-5, batch 8, <=20 epochs, evaluation each epoch,
  metric_for_best_model=cer, greater_is_better=False, patience 3.
- [x] EasyOCR: repo trainer/ from english_g2; export .pth plus .yaml/.py as a
  custom recog_network.
- [x] Paddle: PaddleOCR tools/train.py with en_PP-OCRv5_mobile_rec config and
  pretrained weights; labels formatted image_path<TAB>text.
- [x] Retain lowest-validation-CER checkpoint per model. Save weights, config,
  seed and per-epoch loss/validation CER logs.
- [x] Upload trained weights to team Drive, not Git; Drive folder paths are in
  evaluation/OCR_RESULTS.md Table 3 (shareable links still to add).

Step 5 record — 17 November 2026 (Colab T4, run 20261117-031848; folders
DRIVE/CVDL-OCR-finetune/<model>/20261117-031848/, each with config.json,
epoch_log.csv, selection.json and populated best/):

| Model | Best val crop CER | Exact | Epoch | Notes |
| --- | ---: | ---: | ---: | --- |
| PaddleOCR | 0.1522 | 0.777 | 19 | Tied with epoch 4; exported epoch 19. Pretrained 0.1501, so no CER gain. |
| TrOCR | 0.2019 | 0.685 | 2 | Pretrained (epoch 0) 0.2125. Reload verified. Warmup 0.1. An earlier run (0.656, no warmup) was overwritten in this folder. |
| EasyOCR | 0.2896 | 0.600 | 10 | Early stop at 13. Pretrained 0.4323. |

Validation figures selected the checkpoints; they are not test results.
Degenerate validation line images: A095_00 (144x4 px), P034_00 (87x3 px).


## 6. Fine-tuned evaluation

- [x] Import all three Drive `best/` folders to `.cache/finetuned/<model>/`.
  Imported from user-supplied ZIPs on 17 November 2026; 18 files total,
  ZIP CRC checks passed, Paddle provenance hashes verified. Local file hashes
  and source mappings: `.cache/finetuned/import_manifest.json`.
- [x] Add custom EasyOCR network loading and fine-tuned run labels to the runners
  (committed in `bea9837`). All model reloads and split inference runs completed.
- [x] Run all three fine-tuned models on the same train/validation/test crops
  and layouts as their pretrained versions.
- [x] Save evaluation/ocr_runs/<model>-finetuned-<split>/.
- [x] Score all six model versions with step 1 scoring.

## 7. App model selection

- [x] Compare fine-tuned models only, TEST annotation crops, All fields row.
- [x] Rank CER lower, WER lower, exact match higher. Winning at least two of
  three wins; if all different, use lowest CER.
- [x] State explicitly if selected fine-tuned model is worse than pretrained.
  It is not (pretrained Paddle test: 11.6 / 30.9 / 64.4).

## 8. Results

- [x] Write evaluation/OCR_RESULTS.md, not HTML.
- [x] Table 1: annotation crops. Table 2: detector crops (validation only;
  test detector crops dropped by the user).
  Include the requested train results in the applicable annotation table.
- [x] Columns: Model | Version | Split | Field (number/destination/route/all) |
  Crops (n) | CER (%) | WER (%) | Exact match (%).
  User change, 17 November 2026: pretrained and fine-tuned shown side by side
  per rate (CER/WER/Exact pre | fine); Table 1 split into test, validation and
  train (diagnostic) sub-tables.
- [x] One decimal place; n is crops actually scored.
- [x] Below tables state label sources by split, spot-check percentage,
  exclusions with counts and normalised scoring.
- [x] Identify selected model and provide weights. Selected: fine-tuned
  PaddleOCR (test All fields CER 8.2 / WER 19.1 / exact 82.2, n=45; best of the
  fine-tuned models on all three and better than pretrained). Drive folder recorded;
  weights included directly in the final ZIP. Shareable URL is an optional follow-up.

## 9. OCR handoff to matching owner (the user)

- [x] Produce matching_inputs.jsonl using prepare_ocr_matching_handoff.py --selected from
  the selected fine-tuned model, validation/test, annotation/detector crops.
- [ ] Every crop has candidate_display_id identifying its actual display, so
  number and destination can be paired from the same bus.
  Candidate IDs are present for all 552 records. Geometry proposes 385 text-field
  assignments; 3 have no covering panel and 1 has competing panels. Ownership
  review is separate from completed text labels. No AI check is called human review.
- [x] Run raw OCR on whole-display front_eds crops too. Preserve these outputs
  and display links; use field=front_eds, explicitly confirmed by the user.
  Completed 163 panels (64 validation annotation, 46 validation detector, 53 test
  annotation); automatic pixel-only segmentation, no panel accuracy claim.
- [x] Provide validation/test labels separately as CSV using the same review_id;
  document the review_id/record_id join. Labels never enter matching JSONL.
- [x] Include the bus_information.csv snapshot, OCR_RESULTS.md, weights files
  and exact command to run the selected model on a new crop.
  ZIP includes `weights/paddleocr/`, provenance, portable inference source and
  successful-run environment versions. No matching implementation is included.

### Matching input contract

One JSON line per crop per model; no labels inside. Fields:

- record_id: join key for matching results.
- split: valid/test; input_set: annotation/prediction.
- field: bus_number/destination/route_text/front_eds.
- source_image, crop, box_xyxy, candidate_display_id.
- raw_ocr_text: exact output; normalised_ocr_text.
- prediction_status: success/error/missing.
- ocr_confidence, detector_confidence: preserve provenance and missing values;
  do not invent confidence for engines that do not supply it.

### User-owned matching implementation

1. Keep success records and group crops by display.
2. Normalise for matching while preserving raw OCR.
3. Match service numbers exactly against the CSV: 97E differs from 97 and
   leading zeros are retained.
4. Fuzzy-score reference destinations, accepting or rejecting the best match.
5. Output per display: matched number/destination, score, status and reason.

Decision rules:

- Number only: accept a valid exact service; infer destination only when
  reference and direction identify one destination.
- Destination only: accept the closest reference only above cutoff and clearly
  ahead of the next distinct candidate; infer number only for a unique service.
- Number plus destination: narrow destinations by number. Below cutoff is
  unresolved; strong evidence for another service gets a conflict flag.
- Route text only: retain OCR; service unresolved because CSV lacks road names.
- No usable fields: record no crops / unreadable / matching failed reason.
- Whole display only: parse number plus destination when present, for example
  97E + Tamp1nes Int.
- Crop and whole-display agreement: retain one value and log both evidence
  sources. Disagreement: resolve using other field plus reference, otherwise
  unresolved.
- Ties: use same-display evidence; retain any field value shared by tied
  candidates.
- App shows accepted matches only. Below-cutoff, tied or conflicting guesses
  are withheld as unresolved.

### User-owned matching evaluation

- Tune fuzzy cutoffs 25/50/75 and margin rule on validation only; freeze them
  before running matching on TEST once.
- Report per field, annotation/detector crops separately: raw versus matched
  exact match against labels; accepted rate; accepted-output accuracy; rescued
  wrong-to-correct; harmful correct-to-wrong; valid-but-wrong numbers (97 on a
  97E display); unresolved count.

## Nonblocking tidy-up before submission

- [x] Delete segmentation_previews folders (approximately 1,900 PNGs); keep
  latest run per model. Preserve required pretrained/fine-tuned split outputs
  and supporting evidence.
- [x] Remove /Users/tanyilin/... paths from CSVs.
- [x] Consolidate the 11 docs/OCR_*.md documents into one short README.
  Done 17 November 2026: docs/OCR_README.md; details in evaluation/tidyup-20261117/.

Historical audit follow-up (superseded above), 16 November 2026: class-export ZIP received and verified (3,146 PNGs match cache). Full source-photo ZIP and YOLO11s weights remain absent. Current Paddle recommendation withdrawn; unrun metric rows now n=0. Human forms have local draft recovery, distinct filenames and incomplete-row warnings. Spot-check coverage verified as 50 crops / 44 label groups / 41 photos. Human returns remain pending.

Historical human-return update (superseded above), 16 November 2026: 258 validation returns imported; reviewer cody confirmed by user (original cods export preserved). User explicitly sets P065 wrong_field, with A091 unchanged. Corrected snapshot normalised-v4-valid-human-corrected scores 79 annotation / 51 detector crops. P089/P107 remain suggestions. Train/test human checks remain pending; test Claude AI proposals exist and retain AI provenance.

Historical training preparation — 17 November 2026 (later runs/reviews complete above)
Validation merge committed as 0e8b3d6; cody confirmed; A091/P065 wrong_field.
Fine-tuning code: colab/ocr_finetune/ (TrOCR, EasyOCR and PaddleOCR trainers plus
Colab notebook). Bundle: scripts/export_ocr_finetune_bundle.py ->
.runtime/ocr_finetune_bundle-20261117.zip (SHA-256 7db8ff38...).
Inputs are frozen-layout grayscale line images, as in evaluation: 366 training
line pairs from 387 crops. 24 crops are skipped and listed in skipped.csv
(16 with no layout region, 8 with two regions but one label line); 9
one-region/two-line labels are joined with a space. Validation: 124 line pairs,
130 crops in crop CER. Each model keeps its lowest validation crop-CER checkpoint.
TEST is not used. TrOCR per-epoch checkpoints stay on Colab local disk
(save_only_model); only best/ goes to Drive.
Status update, 17 November 2026: all three Colab runs completed (step 5).
Their `best/` exports are now imported under `.cache/finetuned/` (step 6).
An earlier parallel attempt (scripts/train_*.py, notebooks/OCR_Finetuning.ipynb,
evaluation/ocr_training/line-inputs-20261116/) was superseded and moved out of
the repository to .cache/superseded-training-20261116/.
Pretrained runs added: easyocr-pretrained-test (118 crops) and
easyocr-pretrained-train (1,917 crops; 521 inferred), both on MPS. TrOCR and
PaddleOCR train/test runs are packaged for Colab
(.runtime/ocr_pretrained_test_runs.zip, .runtime/ocr_pretrained_train_runs.zip).
Later update: all 118 test labels and the 50-crop spot-check have human returns.
All six model variants are scored in normalised-v5-step6-20261117.
Test detector crops are deferred: test results cover annotation crops only.
