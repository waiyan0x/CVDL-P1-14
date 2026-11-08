# EasyOCR English generation-2 pretrained recognizer recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 58 | 2 | 1 | 0 | 6.70 / 18.63 | 7.33 / 20.36 |
| annotation | front_eds_route | 39 | 3 | 1 | 3 | 13.41 / 111.74 | 14.26 / 112.47 |
| annotation | front_eds_destination | 49 | 6 | 1 | 2 | 11.93 / 45.79 | 12.71 / 46.42 |
| annotation | all | 146 | 11 | 3 | 5 | 10.55 / 46.06 | 11.13 / 46.57 |
| prediction | front_eds_num | 40 | 2 | 0 | 0 | 6.31 / 8.10 | 6.76 / 9.51 |
| prediction | front_eds_route | 35 | 2 | 0 | 10 | 11.31 / 86.94 | 11.90 / 87.96 |
| prediction | front_eds_destination | 30 | 5 | 0 | 14 | 12.69 / 85.15 | 13.15 / 85.95 |
| prediction | all | 105 | 9 | 0 | 24 | 9.63 / 82.65 | 10.09 / 83.74 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

Fixed layouts, when supplied, are AI-reviewed diagnostic geometry; automatic layouts remain unverified candidates. No independent human review or dataset independence is claimed.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
