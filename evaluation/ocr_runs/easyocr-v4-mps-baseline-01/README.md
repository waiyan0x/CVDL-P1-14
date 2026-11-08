# EasyOCR recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 60 | 0 | 0 | 4 | 6.99 / 186.66 | 7.59 / 189.84 |
| annotation | front_eds_route | 42 | 0 | 0 | 3 | 14.60 / 69.17 | 15.75 / 69.52 |
| annotation | front_eds_destination | 55 | 0 | 2 | 4 | 11.80 / 171.05 | 12.59 / 172.16 |
| annotation | all | 157 | 0 | 2 | 11 | 10.90 / 178.81 | 11.34 / 179.35 |
| prediction | front_eds_num | 42 | 0 | 0 | 3 | 6.71 / 18.93 | 7.75 / 19.23 |
| prediction | front_eds_route | 37 | 0 | 0 | 1 | 10.75 / 15.08 | 12.22 / 17.70 |
| prediction | front_eds_destination | 35 | 0 | 1 | 7 | 10.77 / 152.60 | 13.17 / 157.07 |
| prediction | all | 114 | 0 | 1 | 11 | 9.93 / 68.75 | 10.69 / 71.43 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

All line regions—including single-band cases—are unverified candidates. No claim of correct segmentation or dataset independence is made.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
