# EasyOCR recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 58 | 2 | 1 | 0 | 9.02 / 20.33 | 9.81 / 21.97 |
| annotation | front_eds_route | 39 | 3 | 1 | 3 | 16.32 / 68.19 | 16.86 / 69.67 |
| annotation | front_eds_destination | 49 | 6 | 1 | 2 | 15.53 / 71.63 | 16.31 / 73.01 |
| annotation | all | 146 | 11 | 3 | 5 | 12.73 / 50.22 | 13.39 / 54.15 |
| prediction | front_eds_num | 40 | 2 | 0 | 0 | 9.82 / 30.39 | 10.44 / 31.17 |
| prediction | front_eds_route | 35 | 2 | 0 | 10 | 20.39 / 179.86 | 21.24 / 181.82 |
| prediction | front_eds_destination | 30 | 5 | 0 | 14 | 29.53 / 176.40 | 30.65 / 177.11 |
| prediction | all | 105 | 9 | 0 | 24 | 16.22 / 174.73 | 16.81 / 175.35 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

Fixed layouts, when supplied, are AI-reviewed diagnostic geometry; automatic layouts remain unverified candidates. No independent human review or dataset independence is claimed.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
