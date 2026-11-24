# EasyOCR English generation-2 pretrained recognizer recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 58 | 2 | 1 | 0 | 7.02 / 20.35 | 7.52 / 20.54 |
| annotation | front_eds_route | 39 | 3 | 1 | 3 | 12.51 / 70.29 | 12.96 / 70.74 |
| annotation | front_eds_destination | 49 | 6 | 1 | 2 | 11.66 / 66.69 | 12.31 / 67.40 |
| annotation | all | 146 | 11 | 3 | 5 | 10.53 / 65.68 | 11.02 / 65.91 |
| prediction | front_eds_num | 40 | 2 | 0 | 0 | 6.67 / 7.67 | 8.27 / 9.80 |
| prediction | front_eds_route | 35 | 2 | 0 | 10 | 11.22 / 79.50 | 13.34 / 80.88 |
| prediction | front_eds_destination | 30 | 5 | 0 | 14 | 12.93 / 86.92 | 14.40 / 87.97 |
| prediction | all | 105 | 9 | 0 | 24 | 9.47 / 80.44 | 10.48 / 83.78 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

Fixed layouts, when supplied, are AI-reviewed diagnostic geometry; automatic layouts remain unverified candidates. No independent human review or dataset independence is claimed.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
