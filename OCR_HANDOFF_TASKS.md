# Remaining OCR and matching work

Authority: user instructions, parts 1–3, received 16 November 2026. These are
project decisions, not observed results or coursework rubric requirements.
This checklist supersedes earlier conflicting OCR scoring/handoff proposals.
No task below is marked complete merely because this checklist exists.

## Status and dependencies

- [ ] Complete steps 1–9 below; report blockers directly to the user.
- User clarification: requested visual checks require a human. Codex inspection
  does not satisfy them. Prepare review material and record actual human returns;
  never mark these checks complete from AI inspection.
- [ ] Obtain Brendan's test archive and clarification about the 288 quarantined
  crops. The user authorised asking Brendan; establish the intended contact
  before messaging anyone.
- [ ] Identify team Drive destination for trained weights.
- Preserve actual AI/human provenance even though the user adopts the selected
  AI labels as project ground truth. Prior human-review gates must not silently
  prevent the newly requested scoring.
- Approximate counts and CER values below are expectations to investigate,
  never targets to achieve by changing labels or omitting failures.
- Selecting the OCR winner on TEST follows the user's rule; report that this
  uses TEST for model selection, not as an independent final estimate. Do not
  use TEST to tune settings, train, or choose checkpoints.

## Progress — 16 November 2026

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

- [ ] From training.source.csv retain full-legibility, no-[UNK], non-challenge
  rows. Group by (source_name, label); keep groups with the same Codex text on
  all three augmented copies (expected approximately 345 crops).
- [ ] Prepare 50 randomly sampled crops for human spot-check; record sample seed,
  actual human decisions and percent correct in results, with reviewer provenance.
- [ ] Ask Brendan whether the 288 quarantined crops share photos with v4 TEST.
  If not, apply the same filters and add eligible crops; do not assume clearance.
- [ ] Save evaluation/ocr_training/train_labels_final.csv with crop, field,
  text, source_name.
- [ ] Validation: use the user's 194 typed labels plus 77 Codex labels; visually
  confirm each by human review. Do not use the Codex re-read as the answer key.
- [ ] Remove A042–A048 and P039–P044 from validation for train scene overlap.

## 3. Test set

- [ ] Obtain Brendan's .runtime/ocr_class_dataset/v4-reviewed-01.zip, test/.
- [ ] Use export_ocr_handoff_crops.py from bren-object-detection; add test to
  --split. Export YOLO11s crops with confidence 0.50, IoU 0.70, size 640.
- [ ] Freeze test layouts once with freeze_automatic_ocr_layout.py and reuse
  the exact crops/layout for all models.
- [ ] Label test text crops with Codex, then have a human check every crop
  (approximately 120 expected). Do not prefill labels from EasyOCR, TrOCR or
  Paddle predictions.
- [ ] Detector crops receive the text of the overlapping annotation box at
  IoU >= 0.5. Flag ambiguous overlap cases rather than inventing assignments.
- [ ] Save evaluation/ocr_review/test_labels.csv with review_id, crop, field,
  input_set, text, legibility.
- [ ] Keep TEST out of training and all setting/checkpoint choices.

## 4. Pretrained baselines

- [ ] Run EasyOCR, TrOCR trocr-base-printed and Paddle en_PP-OCRv5_mobile_rec
  on train, validation and test, with annotation and detector crop populations.
- [ ] Use run_easyocr_crops.py (--engine easyocr / trocr) and
  run_paddle_crops.py, supporting --split and --crop-root.
- [ ] Use identical crops and frozen layouts for every model.
- [ ] Commit predictions.jsonl and report.json under
  evaluation/ocr_runs/<model>-pretrained-<split>/, including the existing
  laptop-only Paddle validation run.

## 5. Fine-tune all three models

- [ ] Train on train_labels_final.csv; validate on the step 2 validation set.
- [ ] Match evaluation input format: where inference splits crops into lines,
  train on line images with one text line each.
- [ ] TrOCR: HF VisionEncoderDecoderModel + Seq2SeqTrainer from
  trocr-base-printed; start lr 5e-5, batch 8, <=20 epochs, evaluation each epoch,
  metric_for_best_model=cer, greater_is_better=False, patience 3.
- [ ] EasyOCR: repo trainer/ from english_g2; export .pth plus .yaml/.py as a
  custom recog_network.
- [ ] Paddle: PaddleOCR tools/train.py with en_PP-OCRv5_mobile_rec config and
  pretrained weights; labels formatted image_path<TAB>text.
- [ ] Retain lowest-validation-CER checkpoint per model. Save weights, config,
  seed and per-epoch loss/validation CER logs.
- [ ] Upload trained weights to team Drive, not Git; put links in results.

## 6. Fine-tuned evaluation

- [ ] Run all three fine-tuned models on the same train/validation/test crops
  and layouts as their pretrained versions.
- [ ] Save evaluation/ocr_runs/<model>-finetuned-<split>/.
- [ ] Score all six model versions with step 1 scoring.

## 7. App model selection

- [ ] Compare fine-tuned models only, TEST annotation crops, All fields row.
- [ ] Rank CER lower, WER lower, exact match higher. Winning at least two of
  three wins; if all different, use lowest CER.
- [ ] State explicitly if selected fine-tuned model is worse than pretrained.

## 8. Results

- [ ] Write evaluation/OCR_RESULTS.md, not HTML.
- [ ] Table 1: annotation crops. Table 2: detector crops (validation and test).
  Include the requested train results in the applicable annotation table.
- [ ] Columns: Model | Version | Split | Field (number/destination/route/all) |
  Crops (n) | CER (%) | WER (%) | Exact match (%).
- [ ] One decimal place; n is crops actually scored.
- [ ] Below tables state label sources by split, spot-check percentage,
  exclusions with counts and normalised scoring.
- [ ] Identify selected model and Drive link to weights.

## 9. OCR handoff to matching owner (the user)

- [ ] Produce matching_inputs.jsonl using prepare_ocr_matching_handoff.py from
  the selected fine-tuned model, validation/test, annotation/detector crops.
- [ ] Every crop has candidate_display_id identifying its actual display, so
  number and destination can be paired from the same bus.
- [ ] Run raw OCR on whole-display front_eds crops too. Preserve these outputs
  and display links; use field=front_eds, explicitly confirmed by the user.
- [ ] Provide validation/test labels separately as CSV using the same review_id;
  document the review_id/record_id join. Labels never enter matching JSONL.
- [ ] Include the bus_information.csv snapshot, OCR_RESULTS.md, weights link
  and exact command to run the selected model on a new crop.

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

- [ ] Delete segmentation_previews folders (approximately 1,900 PNGs); keep
  latest run per model. Preserve required pretrained/fine-tuned split outputs
  and supporting evidence.
- [ ] Remove /Users/tanyilin/... paths from CSVs.
- [ ] Consolidate the 11 docs/OCR_*.md documents into one short README.

User audit follow-up, 16 November 2026: class-export ZIP received and verified (3,146 PNGs match cache). Full source-photo ZIP and YOLO11s weights remain absent. Current Paddle recommendation withdrawn; unrun metric rows now n=0. Human forms have local draft recovery, distinct filenames and incomplete-row warnings. Spot-check coverage verified as 50 crops / 44 label groups / 41 photos. Human returns remain pending.

Observed human-return update, 16 November 2026: 258 validation returns imported; reviewer cody confirmed by user (original cods export preserved). User explicitly sets P065 wrong_field, with A091 unchanged. Corrected snapshot normalised-v4-valid-human-corrected scores 79 annotation / 51 detector crops. P089/P107 remain suggestions. Train/test human checks remain pending; test Claude AI proposals exist and retain AI provenance.
