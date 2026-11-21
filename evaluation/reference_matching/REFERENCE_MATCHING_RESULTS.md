# Reference matching results

OCR input: Cody's fine-tuned PaddleOCR (`20261117-031848`) readings from the OCR branch (validation layout v2). Reference: `data/reference/bus_information.cleaned.csv`. Destination gold: `evaluation/reference_matching/answer_key.csv`, 37 entries; reviewed by: Claude (at user request, 20 Nov 2026) (37).

## Selected setting (chosen on validation only)

**Scorer `ratio`, cutoff 70, margin 10, conflict policy `keep_number`, route crop fallback `check`.** Project decisions: the route crop fallback is required (`check` or `use`, never `off`; `check` wins ties) and the cutoff is fixed at 70. Cutoff 50 scored best on validation (24 vs 23 of 27 destinations, both 0 wrong) but was judged too loose for unseen signs and raised about twice as many conflict flags. The change was made after test had been inspected at both cutoffs (test at 50: 15/16 destinations, at 70: 14/16, 0 wrong at both), so test is no longer a single untouched run. Other settings: most correct outputs minus wrong outputs (services + destinations) on validation; ties go to higher precision, then the stricter cutoff and margin. Test was run once with this setting.

## Results with the selected setting

Raw OCR exact = OCR text equals the human label. Shown = the matcher outputs a value (the app would display it). Rescued = raw OCR wrong but matched output correct. Harmful = raw OCR right but matched output wrong.

| Measure | valid/annotation | valid/prediction | test/annotation |
| --- | ---: | ---: | ---: |
| Displays | 64 | 49 | 53 |
| Service: displays with a readable label | 43 | 33 | 24 |
| Service: raw OCR exact | 97.7% (42/43) | 93.9% (31/33) | 100.0% (24/24) |
| Service: shown and correct | 90.7% (39/43) | 87.9% (29/33) | 91.7% (22/24) |
| Service: shown but wrong | 0 | 1 | 0 |
| Service: withheld | 4 | 3 | 2 |
| Service: label not in reference (withheld = correct) | 1/1 | 0/0 | 2/2 |
| Service: misread as another real service | 0 | 1 | 0 |
| Service: rescued / harmful | 0 / 0 | 0 / 0 | 0 / 0 |
| Destination: displays with an answer-key entry | 17 | 10 | 16 |
| Destination: raw OCR exact (vs sign text) | 58.8% (10/17) | 40.0% (4/10) | 68.8% (11/16) |
| Destination: shown and correct | 94.1% (16/17) | 70.0% (7/10) | 87.5% (14/16) |
| Destination: shown but wrong | 0 | 0 | 0 |
| Destination: withheld | 1 | 3 | 2 |
| Destination: rescued / harmful | 6 / 0 | 4 / 0 | 3 / 0 |
| Depot / not-in-service caught | 2/2 | 2/2 | 0/0 |

## Your 25 / 50 / 75 cutoffs (validation, same scorer and margin)

| Cutoff | Net correct | Shown precision | Service correct / wrong | Destination correct / wrong / withheld |
| ---: | ---: | ---: | ---: | ---: |
| 25 | 89 | 98.9% | 66 / 1 | 24 / 0 / 3 |
| 50 | 92 | 98.9% | 68 / 1 | 25 / 0 / 2 |
| 75 | 88 | 98.9% | 68 / 1 | 21 / 0 / 6 |

## Best setting per similarity measure (validation)

| Scorer | Cutoff | Margin | Net correct | Shown precision | Destination correct / wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| ratio | 50 | 10 | 92 | 98.9% | 25 / 0 |
| token_sort_ratio | 25 | 10 | 91 | 98.9% | 24 / 0 |
| token_set_ratio | 25 | 10 | 90 | 98.9% | 23 / 0 |
| WRatio | 25 | 10 | 90 | 98.9% | 24 / 0 |

## Conflict policy (validation, best setting of each)

When the destination fits a different service better than the number read: `withhold_both` hides service and destination; `keep_number` keeps the exact service and hides only the destination.

| Policy | Scorer | Cutoff | Margin | Net correct | Shown precision | Service correct / wrong |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| withhold_both | ratio | 25 | 0 | 86 | 98.9% | 63 / 1 |
| keep_number | ratio | 50 | 10 | 92 | 98.9% | 68 / 1 |

## Route crop as destination fallback (validation, best setting of each)

When a display has no destination crop: `off` ignores the route crop; `check` uses it only to flag a service number it does not fit (never shown); `use` may also show it as the destination.

| Fallback | Scorer | Cutoff | Margin | Net correct | Shown precision | Service correct / wrong | Destination correct / wrong |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| off | ratio | 50 | 10 | 92 | 98.9% | 68 / 1 | 25 / 0 |
| check | ratio | 50 | 10 | 92 | 98.9% | 68 / 1 | 25 / 0 |
| use | ratio | 50 | 0 | 91 | 97.9% | 68 / 1 | 25 / 1 |

Full grid: `results/validation_grid.csv`. Per-display decisions with raw OCR, matched text, similarity and reasons: `results/per_display_validation.csv`, `results/per_display_test.csv`.

## Limits

- Displays are grouped by box containment (app association code), not Cody's `candidate_display_id`; swap in his `matching_inputs.jsonl` when it arrives.
- Test has annotation-box crops only (no test detector crops).
- Small samples: one display changes a percentage by several points.
- Status counts (selected setting): valid/annotation: conflict 5, destination_only 1, matched 17, not_in_service 2, service_only 22, unable_to_detect 9, unreadable 1, unresolved 7; valid/prediction: conflict 6, matched 13, not_in_service 2, service_only 20, unable_to_detect 3, unreadable 1, unresolved 4; test/annotation: conflict 1, matched 17, service_only 18, unable_to_detect 7, unresolved 10
