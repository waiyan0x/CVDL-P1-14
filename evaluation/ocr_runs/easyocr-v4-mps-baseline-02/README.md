# EasyOCR recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 60 | 0 | 1 | 1 | 8.08 / 26.54 | 8.70 / 27.12 |
| annotation | front_eds_route | 42 | 0 | 1 | 1 | 15.78 / 61.24 | 16.39 / 61.73 |
| annotation | front_eds_destination | 55 | 0 | 2 | 0 | 13.51 / 56.63 | 14.08 / 58.26 |
| annotation | all | 157 | 0 | 4 | 2 | 11.75 / 54.13 | 12.43 / 54.79 |
| prediction | front_eds_num | 42 | 0 | 0 | 0 | 6.99 / 11.58 | 7.69 / 12.39 |
| prediction | front_eds_route | 37 | 0 | 0 | 0 | 12.21 / 17.71 | 13.01 / 18.69 |
| prediction | front_eds_destination | 35 | 0 | 0 | 4 | 11.73 / 189.89 | 12.57 / 191.89 |
| prediction | all | 114 | 0 | 0 | 4 | 10.38 / 21.77 | 11.21 / 25.02 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

All line regions—including single-band cases—are unverified candidates. No claim of correct segmentation or dataset independence is made.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
