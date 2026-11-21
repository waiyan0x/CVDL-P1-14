# Whole-display fallback: fine-tuned vs pretrained PaddleOCR — 21 November 2026

**Question:** when a display has no usable number or destination crop, which
PaddleOCR model should read the whole-display (`front_eds`) crop?

**Decision (user, 21 November 2026):** the fine-tuned model reads field crops,
and the public pretrained model reads whole-display crops as a fallback. The
evidence below supports this for destinations. For service numbers the two
models are equal.

## Setup

- **Crops:** the 163 whole-display crops in `ocr-matching-final-20261119`
  (64 validation annotation, 46 validation detector, 53 test annotation).
- **Models:** `models/paddleocr-finetuned` (round 1, run `20261117-031848`) and
  `models/paddleocr-pretrained` (public `en_PP-OCRv5_mobile_rec`). Both are
  hash-checked, CPU only.
- **Reading:** the app's worker (`backend/app/services/ocr/paddle_worker.py`):
  automatic line segmentation, top to bottom.
- **Splitting the reading:** `RouteMatcher.split_display` takes the first token
  shaped like a service ID (preferring one in the reference list) as the
  number; the rest is the destination.
- **Scoring:** there are no whole-display labels. A display is scored only when
  its candidate display has full-legibility number and destination labels that
  the matcher can match. It counts as correct when the whole-display reading
  matches the same service and endpoint. The number is scored against the
  number label alone.

## Results

| Split | Model | Number correct | Service and endpoint matched correctly | Wrong match accepted | No text |
|---|---|---:|---:|---:|---:|
| Validation | fine-tuned | 40 / 76 | 3 / 28 | 0 | 2 / 110 |
| Validation | pretrained | 39 / 76 | **7 / 28** | 0 | 1 / 110 |
| Test | fine-tuned | 16 / 24 | 2 / 13 | 0 | 0 / 53 |
| Test | pretrained | 16 / 24 | **4 / 13** | 0 | 8 / 53 |
| **Both** | fine-tuned | 56 / 100 | 5 / 41 | 0 | 2 / 163 |
| **Both** | pretrained | 55 / 100 | **11 / 41** | 0 | 9 / 163 |

## Findings

- **Destinations:** the pretrained model gets more complete matches on both
  splits.
- **Numbers:** the two models are equal.
- **Separate field crops are much better.** On validation they matched 17 of
  18 displays. The fallback should only be used when field crops can't be.
- **Empty readings:** the pretrained model returns empty text more often (9
  against 2).

## Limits

- The samples are small (41 matchable displays). The direction of the result
  is consistent, but the size of the gap is not reliable.
- Display grouping is an unreviewed geometry proposal (P005, P035, P074 and
  P094 are flagged).
- Test crops were looked at when making this decision, so these test numbers
  are not an independent estimate.
- The matcher is used to define the correct answer, so this measures how well
  the whole-display reading supports matching, not raw OCR accuracy.

## Files and rerunning

- `results/summary.json`: counts per model and split
- `results/readings.jsonl`: each reading, its split and its scoring

```sh
.venv/bin/python -I evaluation/ocr_scoring/whole-display-fallback-20261121/compare_whole_display.py NEW_OUT_DIR
```
