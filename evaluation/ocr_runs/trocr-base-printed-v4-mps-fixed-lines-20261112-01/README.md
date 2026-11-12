# microsoft/trocr-base-printed (public pretrained) recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 58 | 2 | 0 | 0 | 193.74 / 225.91 | 195.15 / 227.47 |
| annotation | front_eds_route | 39 | 3 | 0 | 3 | 301.07 / 507.70 | 302.17 / 508.73 |
| annotation | front_eds_destination | 49 | 6 | 0 | 2 | 294.67 / 443.88 | 295.52 / 445.60 |
| annotation | all | 146 | 11 | 0 | 5 | 223.05 / 437.84 | 224.61 / 438.68 |
| prediction | front_eds_num | 40 | 2 | 0 | 0 | 190.52 / 543.55 | 191.17 / 545.22 |
| prediction | front_eds_route | 35 | 2 | 0 | 10 | 444.79 / 1295.28 | 448.84 / 1298.07 |
| prediction | front_eds_destination | 29 | 6 | 0 | 14 | 598.75 / 1761.01 | 599.79 / 1763.60 |
| prediction | all | 104 | 10 | 0 | 24 | 349.33 / 1320.77 | 350.33 / 1323.68 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

Fixed layouts, when supplied, are AI-reviewed diagnostic geometry; automatic layouts remain unverified candidates. No independent human review or dataset independence is claimed.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
