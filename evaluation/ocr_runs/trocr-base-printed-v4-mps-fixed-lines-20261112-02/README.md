# microsoft/trocr-base-printed (public pretrained) recognition-only crop run

Actual recognizer device: **mps:0**. All 271 crop IDs attempted.

| Set | Field | Completed | Errors | Empty | Multi-line candidates | Recognition median / p95 ms | Crop median / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| annotation | front_eds_num | 58 | 2 | 0 | 0 | 225.90 / 321.64 | 227.62 / 323.14 |
| annotation | front_eds_route | 39 | 3 | 0 | 3 | 361.37 / 562.32 | 362.03 / 563.28 |
| annotation | front_eds_destination | 49 | 6 | 0 | 2 | 346.95 / 602.39 | 347.66 / 603.98 |
| annotation | all | 146 | 11 | 0 | 5 | 270.20 / 551.40 | 270.83 / 552.72 |
| prediction | front_eds_num | 40 | 2 | 0 | 0 | 213.75 / 271.85 | 215.51 / 272.93 |
| prediction | front_eds_route | 35 | 2 | 0 | 10 | 420.74 / 804.72 | 421.89 / 806.97 |
| prediction | front_eds_destination | 29 | 6 | 0 | 14 | 497.40 / 836.38 | 498.15 / 837.39 |
| prediction | all | 104 | 10 | 0 | 24 | 315.40 / 798.96 | 316.15 / 799.58 |

Frozen weights and source/transcription hashes passed before/after checks. No reference matching, training or accuracy scoring was performed.

Inspect `segmentation_previews/` and `predictions.jsonl` before trusting line layout. `predictions.csv` is the compact raw export.
`report.json` contains complete settings/timing boundaries/limitations. `environment.json` records the actual device and versions.

Fixed layouts, when supplied, are AI-reviewed diagnostic geometry; automatic layouts remain unverified candidates. No independent human review or dataset independence is claimed.
Median/p95 describe one pass across successful heterogeneous crops, not repeated measurements of a fixed input or application throughput.
