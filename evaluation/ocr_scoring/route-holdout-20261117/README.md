# Route hold-out scoring — 17 November 2026

Supplementary route-text evaluation. The official test set has only 4 scorable
route crops, too few to compare engines.

## Data

- 139 route crops, one per train photo whose route crop was never labelled
  (Codex 3-copy consensus failed). Built by `scripts/build_route_holdout_batch.py`;
  crops live in `.runtime/route-holdout-20261117/crops/` (not in git, verified by `crop_sha256`).
- Labels: typed blind (no AI/OCR proposal) by one human reviewer (cody), 17 Nov 2026.
  No second review: the user chose to score on single-reviewer labels.
  Sources: `evaluation/ocr_review/route-holdout-20261117/`.
- Legibility: 27 full (scored), 49 partial, 63 illegible.
- Line layout: frozen automatic method, same as test (`evaluation/ocr_layouts/route-holdout-automatic-v1`).
- Runs: `.cache/ocr_runs/*-routeholdout` (same weights and settings as step 6; inventory split is
  `train`, so tables show split "train"). No prediction failures.

## Results (annotation crops, normalised scoring, n = 27)

95% CI: crop-level bootstrap, 5000 resamples, seed 0.

| Model | Version | CER (%) | 95% CI | WER (%) | Exact (%) |
| --- | --- | ---: | --- | ---: | ---: |
| EasyOCR | pretrained | 33.2 | 22.3–44.8 | 80.0 | 3.7 |
| EasyOCR | fine-tuned | 22.5 | 12.9–33.1 | 54.7 | 25.9 |
| TrOCR | pretrained | 24.9 | 13.8–37.0 | 56.0 | 18.5 |
| TrOCR | fine-tuned | 23.9 | 12.6–35.6 | 48.0 | 29.6 |
| PaddleOCR | pretrained | 12.6 | 5.0–21.7 | 34.7 | 48.1 |
| PaddleOCR | fine-tuned | 10.7 | 3.5–19.1 | 25.3 | 59.3 |

Paired CER differences (same crops), 95% CI:

| Comparison | Difference | 95% CI |
| --- | ---: | --- |
| PaddleOCR FT − EasyOCR FT | −11.8 | −17.0 to −7.0 |
| PaddleOCR FT − TrOCR FT | −13.1 | −21.2 to −6.2 |
| PaddleOCR PT − TrOCR PT | −12.3 | −20.6 to −5.5 |
| EasyOCR FT − EasyOCR PT | −10.7 | −15.1 to −6.6 |
| PaddleOCR FT − PaddleOCR PT | −1.9 | −3.6 to −0.3 |
| TrOCR FT − TrOCR PT | −1.1 | −4.5 to +2.1 (not distinguishable) |

## Supplementary: 49 partial crops (readable text only, diagnostic)

Not an official metric: official scoring excludes every crop containing `[UNK]`.
Separate inference runs (`.cache/ocr_runs/*-routeholdout-partial`, layout
`evaluation/ocr_layouts/route-holdout-partial-automatic-v1`) cover the 49 partial crops;
scored by `scripts/score_partial_route.py`, outputs in `partial/`.

Method: each `[UNK]` in the reference is a wildcard matching any hypothesis text (including
none) at zero cost; whitespace beside `[UNK]` is folded into it. Normalised scoring otherwise.
Known-text CER = errors / 578 readable reference characters. "All readable correct" = no errors.

| Model | Version | Known-text CER (%) | 95% CI | All readable correct (%) |
| --- | --- | ---: | --- | ---: |
| EasyOCR | pretrained | 56.7 | 48.2–65.1 | 4.1 |
| EasyOCR | fine-tuned | 45.0 | 36.3–53.5 | 8.2 |
| TrOCR | pretrained | 41.3 | 32.9–50.1 | 12.2 |
| TrOCR | fine-tuned | 38.9 | 30.0–48.1 | 16.3 |
| PaddleOCR | pretrained | 33.0 | 24.0–42.5 | 22.4 |
| PaddleOCR | fine-tuned | 31.3 | 22.8–40.1 | 22.4 |

Paired differences (known-text CER), 95% CI:

| Comparison | Difference | 95% CI |
| --- | ---: | --- |
| PaddleOCR FT − EasyOCR FT | −13.7 | −18.6 to −8.6 |
| PaddleOCR FT − TrOCR FT | −7.6 | −11.6 to −3.6 |
| PaddleOCR PT − EasyOCR PT | −23.7 | −31.1 to −16.2 |
| PaddleOCR PT − TrOCR PT | −8.3 | −13.1 to −3.5 |
| EasyOCR FT − EasyOCR PT | −11.8 | −17.1 to −7.0 |
| TrOCR FT − TrOCR PT | −2.4 | −7.0 to +1.8 (not distinguishable) |
| PaddleOCR FT − PaddleOCR PT | −1.7 | −5.3 to +2.3 (not distinguishable) |

Caveats: the wildcard is lenient, since it can absorb hallucinated text next to an `[UNK]` and
even partly match garbled output (e.g. RH0007), so absolute values flatter every engine. Engines
share the same rule, so the ranking is the useful part. These crops are blurrier than the full
ones, hence higher error. No prediction failures.

## Limitations

- Not the official test set; report it as a separate table beside test.
- Single human reviewer; no inter-annotator check.
- Same photos' number/destination crops were in fine-tuning (route text was not), so fine-tuned
  models have seen these buses.
- Selection bias: these are crops where AI labelling could not agree, likely harder than random.
- One crop per photo; 32 photos had 2+ route boxes and only the largest copy was used.
- Bootstrap CIs treat crops as independent and ignore label noise.
