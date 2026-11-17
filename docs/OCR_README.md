# OCR stage: README

Reads the text on a bus's front electronic destination sign (EDS): service
number, destination and route text, from crops of the sign. Current status
(17 November 2026): steps 1–8 of `OCR_HANDOFF_TASKS.md` are complete; the
selected model is **fine-tuned PaddleOCR**. Reference matching (step 9) belongs
to the matching owner. The detailed earlier documents are in
[`docs/archive/ocr/`](archive/ocr/) (index at the end).

## Pipeline

1. **Crops.** Brendan's reviewed-v4 package: text-field crops cut from the
   dataset's labelled boxes (`front_eds_num`, `front_eds_destination`,
   `front_eds_route`) plus whole-display `front_eds` crops, and 160 YOLO11s
   validation detector crops. Test has annotation-box crops only (user decision).
2. **Line layout.** Each crop is split into text lines using a frozen layout
   (`evaluation/ocr_layouts/`), identical for every model. Crops with an
   unresolved layout get no prediction and count as empty.
3. **Recognition.** `scripts/run_easyocr_crops.py` (EasyOCR, TrOCR) and
   `scripts/run_paddle_crops.py` (PaddleOCR) write `predictions.jsonl` and
   `report.json` to `evaluation/ocr_runs/<model>-<pretrained|finetuned>-<split>/`.
   Fine-tuned weights load with `--finetuned-from` (and `--recog-network
   eds_english_g2` for EasyOCR); `scripts/run_finetuned_ocr.sh` runs all splits.
4. **Scoring.** `scripts/build_step6_scoring.py` freezes the labels and scores
   all six model versions with `backend/app/evaluation/crop_scoring.py`.
5. **Handoff.** `scripts/prepare_ocr_matching_handoff.py --selected` builds the
   matching package (`.runtime/ocr-matching-final-20261117.zip`).

## Labels

| Split | Source | Status |
| --- | --- | --- |
| Train | 387 AI (Codex) labels, 3-copy consensus, `.runtime/ocr-text-dataset-20261116/labels.csv` | Used for fine-tuning; scores **diagnostic only** (spot-check: text consistent on 41/50, 27/50 not fully legible to a human) |
| Validation | 258 crops checked by eye (cody, 16 Nov), `evaluation/ocr_review/human-verification-20261116/` | Official; 79 annotation + 51 detector crops scored |
| Test | 118 crops confirmed by eye (cody, 17 Nov), `evaluation/ocr_review/test_labels.csv` | Official; 45 annotation crops scored |

Transcription rules (full version: `archive/ocr/OCR_TRANSCRIPTION_RULES.md`):
transcribe only visible text, never from route data or other frames; keep case,
punctuation and abbreviations; one space between words; real newlines between
lines; `[UNK]` for each unreadable or cut-off span. Legibility is `full` (no
`[UNK]`), `partial` (some `[UNK]`) or `illegible` (exactly `[UNK]`).

## Scoring rules

- Only `full`-legibility crops without `[UNK]` are scored. Also excluded: blank,
  wrong-field, challenge-only and validation crops sharing a scene with training.
- Text is normalised before comparison: Unicode NFC, casefold, whitespace
  collapsed. Punctuation and abbreviations are kept.
- CER and WER are micro-averaged edit rates; exact match is per crop.
- Failed or missing predictions count as empty text.
- Annotation-crop scores measure OCR given a correctly drawn box, not the full
  detector-plus-OCR pipeline.

## Fine-tuning

Colab T4, run `20261117-031848`; code in `colab/ocr_finetune/` (see its README).
366 training line images, seed 0, batch 8, learning rate 5e-5, at most 20 epochs,
no augmentation; best checkpoint by validation crop CER. Weights: team Drive
`DRIVE/CVDL-OCR-finetune/<model>/20261117-031848/best/`; local copies in
`.cache/finetuned/` (not in Git). Paddle's in-training validation figure (15.2%)
differs from its runner-scored figure (11.6%); use runner scores.

## Results and selection

Full tables: `evaluation/OCR_RESULTS.md`. Test annotation crops, All fields, n=45:

| Model | Pretrained CER / WER / exact (%) | Fine-tuned CER / WER / exact (%) |
| --- | --- | --- |
| PaddleOCR | 11.6 / 30.9 / 64.4 | **8.2 / 19.1 / 82.2** |
| TrOCR | 17.9 / 37.2 / 64.4 | 17.4 / 38.3 / 62.2 |
| EasyOCR | 32.7 / 57.4 / 53.3 | 21.6 / 45.7 / 60.0 |

Selection rule: fine-tuned models only, test annotation crops, All fields; best
on at least two of CER, WER and exact match. Fine-tuned PaddleOCR wins on all
three and beats every pretrained model.

## Limits

- Small test set: 45 scored crops, only 4 of them route text.
- Training labels are AI-generated; train scores are diagnostic only.
- No end-to-end (detector + OCR + matching) accuracy or latency claim.
- Display ownership for pairing fields from one bus still needs the human check
  in the matching package (`review/display_ownership.html`).

## Archive index (`docs/archive/ocr/`)

| Document | Covers |
| --- | --- |
| OCR_TRANSCRIPTION_RULES.md | Full transcription conventions and examples |
| OCR_CROP_SCORING.md | Scorer usage, snapshots, normalisation details |
| OCR_LINE_LAYOUT.md | Frozen line-layout method and contract |
| OCR_CROP_BASELINE.md | Runner method, outputs and timing boundaries |
| OCR_MATCHING_HANDOFF.md | Matching package schema and next-owner rules |
| OCR_HUMAN_VERIFICATION.md | Preparing and importing human review forms |
| OCR_REVIEW_DECISIONS.md | Importing review decisions; recorded checks |
| OCR_ANNOTATION_PACKAGE.md | V4 annotation workspace |
| OCR_REVIEW_SCORING_PRD.md | Original review and scoring proposal (12 Nov) |
| OCR_PRETRAINING_DELIVERABLE.md | Three-model pretrained baseline audit (13 Nov) |
| OCR_MODEL_SELECTION.md | Early model-candidate register (superseded) |
| OCR_MODEL_HANDOFF.md | Historical pretrained-weights handoff (superseded) |

Tidy-up, 17 November 2026: the 12 documents above were moved here unchanged;
links elsewhere in the repository point to their new location.
