# Reference matching results

OCR input: Cody's fine-tuned PaddleOCR (`20261117-031848`) readings from the OCR branch (validation layout v2). Reference: `data/reference/bus_information.cleaned.csv`. Destination gold: answer key is a DRAFT: 0 of 37 entries confirmed by a person yet.

## Selected setting (chosen on validation only)

**Scorer `ratio`, cutoff 70, margin 10, conflict policy `keep_number`.** Rule: most correct outputs minus wrong outputs (services + destinations) on validation; ties go to higher precision, then the stricter cutoff and margin. Test was run once with this setting.

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
| Destination: displays with an answer-key entry | 18 | 11 | 17 |
| Destination: raw OCR exact (vs sign text) | 61.1% (11/18) | 36.4% (4/11) | 70.6% (12/17) |
| Destination: shown and correct | 88.9% (16/18) | 63.6% (7/11) | 76.5% (13/17) |
| Destination: shown but wrong | 0 | 0 | 1 |
| Destination: withheld | 2 | 4 | 3 |
| Destination: rescued / harmful | 6 / 0 | 4 / 0 | 3 / 1 |
| Depot / not-in-service caught | 2/2 | 2/2 | 0/0 |

## Your 25 / 50 / 75 cutoffs (validation, same scorer and margin)

| Cutoff | Net correct | Shown precision | Service correct / wrong | Destination correct / wrong / withheld |
| ---: | ---: | ---: | ---: | ---: |
| 25 | 87 | 98.9% | 66 / 1 | 22 / 0 / 7 |
| 50 | 90 | 98.9% | 68 / 1 | 23 / 0 / 6 |
| 75 | 88 | 98.9% | 68 / 1 | 21 / 0 / 8 |

## Best setting per similarity measure (validation)

| Scorer | Cutoff | Margin | Net correct | Shown precision | Destination correct / wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| ratio | 50 | 10 | 90 | 98.9% | 23 / 0 |
| token_sort_ratio | 25 | 10 | 90 | 98.9% | 23 / 0 |
| token_set_ratio | 25 | 10 | 89 | 98.9% | 22 / 0 |
| WRatio | 25 | 10 | 86 | 98.9% | 20 / 0 |

## Conflict policy (validation, best setting of each)

When the destination fits a different service better than the number read: `withhold_both` hides service and destination; `keep_number` keeps the exact service and hides only the destination.

| Policy | Scorer | Cutoff | Margin | Net correct | Shown precision | Service correct / wrong |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| withhold_both | token_set_ratio | 75 | 5 | 84 | 98.8% | 64 / 1 |
| keep_number | ratio | 50 | 10 | 90 | 98.9% | 68 / 1 |

Full grid: `results/validation_grid.csv`. Per-display decisions with raw OCR, matched text, similarity and reasons: `results/per_display_validation.csv`, `results/per_display_test.csv`.

## Limits

- Displays are grouped by box containment (app association code), not Cody's `candidate_display_id`; swap in his `matching_inputs.jsonl` when it arrives.
- Test has annotation-box crops only (no test detector crops).
- Small samples: one display changes a percentage by several points.
- Status counts (selected setting): valid/annotation: conflict 5, destination_only 1, matched 17, not_in_service 2, service_only 22, unable_to_detect 9, unreadable 1, unresolved 7; valid/prediction: conflict 3, matched 13, not_in_service 2, service_only 23, unable_to_detect 3, unreadable 1, unresolved 4; test/annotation: conflict 1, matched 17, service_only 18, unable_to_detect 7, unresolved 10
