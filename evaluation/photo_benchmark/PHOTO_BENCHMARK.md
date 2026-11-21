# Photo benchmark: similarity cutoff (21 Nov 2026)

**Setting in use: cutoff 70** (unchanged). Every other setting is the one in use: `ratio` scoring,
margin 10, conflict policy `keep_number`, route crop fallback `check`, fine-tuned PaddleOCR (round 1)
for number/destination/route crops and pretrained PaddleOCR for whole-display crops, YOLO11s
(conf 0.5, IoU 0.7, imgsz 640). Only the nearest display of each photo is scored, as the app shows it.

## Data

- 40 photos supplied by JY on 21 Nov 2026 (20 named `NNN_<view>_<layout>_<service>`, 20 named
  `sgbus-20261120-b09_*`); kept in `models/local/photos/benchmark/` (gitignored). The `sgbus-…-b09`
  names indicate a generated batch; if any photos are rendered rather than camera frames, these
  results may be more favourable than real footage.
- None of these photos was used to build or tune the matcher before this run.
- Labels were written **before** the run: `labels.csv` (service on the sign, the sign's destination text,
  and the reference endpoint it denotes). 28 photos have a destination that is an endpoint of the
  service. 12 are **NONE**: the text is a road or a place that is not an endpoint of that service (side
  displays such as `JELAPANG RD`, and signs such as 317 `YIO CHU KANG INT`), so the correct output is to
  withhold the destination.
- Labelled by Claude from the visible sign text and `bus_information.cleaned.csv`.

## Results by cutoff

Correct = the right endpoint is shown, or the destination is withheld on a NONE photo.
Shown wrong = a wrong endpoint is shown, or any endpoint is shown on a NONE photo.

| Cutoff | Destination correct (of 28) | Withheld (of 28) | NONE withheld (of 12) | Shown wrong | Net (correct + NONE withheld − shown wrong) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 23 | 5 | 6 | 6 | 23 |
| 40 | 23 | 5 | 5 | 7 | 21 |
| 50 | 22 | 6 | 10 | 2 | 30 |
| 55 | 22 | 6 | 10 | 2 | 30 |
| 60 | 22 | 6 | 11 | 1 | **32** |
| 65 | 21 | 7 | 11 | 1 | 31 |
| **70 (in use)** | **20** | **8** | **11** | **1** | **30** |
| 75 | 19 | 9 | 11 | 1 | 29 |
| 80 | 18 | 10 | 12 | 0 | 30 |
| 90 | 15 | 13 | 12 | 0 | 27 |

Service number at 70: 33 of 40 correct, 0 wrong, 7 withheld: 3 side views had no display detected (966,
26, 64); 901 had no number crop; OCR misread 3 numbers (`927` for 922, `9128` for 912B, `1004` for 100A),
none of which is shown. Full grid:
`results/cutoff_grid.csv`; per photo at 70: `results/per_photo.csv`; OCR readings: `results/ocr_readings.csv`.

Latency (2-core CPU, detection + OCR, nearest display): median 284 ms per frame, range 104–597 ms.

## What the cutoff changes on these photos

| Photo | Best candidate (score) | Correct? | Shown at 50 / 60 / 70 / 80 |
| --- | --- | --- | --- |
| 807 side `YISHUN RING RD` | Yishun Bus Interchange (75.0) | no (NONE) | yes / yes / **yes** / no |
| 800 `SEMBAWANG RD` | Sembawang Road (Blk 101) (75.0) | yes | yes / yes / yes / no |
| 199 `NANYANG CRES` | Nanyang Crescent (73.7) | yes | yes / yes / yes / no |
| 976 `BUKIT PANJANG INT` (whole display read `976 RUT PANANG`) | Bukit Panjang Bus Interchange (66.7) | yes | yes / yes / no / no |
| 115 `HOUGANG AVE 3` (destination read `HOLGANG`) | Hougang Avenue 3 (loop) (60.0) | yes | yes / yes / no / no |
| 922 side `JELAPANG RD` | (shown below 60) | no (NONE) | yes / no / no / no |

- **60 scored best** (net 32): it keeps 115 and 976, which 70 withholds, with the same single wrong
  result (807). **70 is 2 behind**; 80 removes the 807 error but also loses 199 and 800. Below 50,
  roads on side displays start to be shown as destinations (6–7 wrong).
- The one wrong result at 70 (807) is a road name that shares words with an endpoint
  (`YISHUN RING RD` vs `Yishun Bus Interchange`).
- This agrees with validation (`REFERENCE_MATCHING_RESULTS.md`: 50 best, 70 fixed for safety): the
  correct range is roughly 50–65 and 70 trades a few correct destinations for safety. Choosing a new
  cutoff from this run would tune it on these 40 photos; a change should be confirmed on photos not
  used here.

## Misses that no cutoff fixes (5 of 28)

On five `destination-above` signs (111, 31, 268, 678, 272) YOLO11s labels the **lower, smaller line**
as `destination` and the large top line as `route` (or does not box it), so the matcher scores the
route text: 268 reads destination `ANG MO KIO AVE 3`, route `ANG MO KIO IND PK 2`; 272 reads destination
`LOWER DELTA RD`, route `TELOK BLANGAH RISE`. With `check`, the route line can only flag a conflict, so
these are withheld (not shown wrong). One more miss is OCR: 100A read as `1004` (unable to detect).

## Rerun

```
python scripts/benchmark_photo_threshold.py              # reads every photo, then scores each cutoff
python scripts/benchmark_photo_threshold.py --reuse-ocr  # scores again from results/ocr_readings.csv
```
