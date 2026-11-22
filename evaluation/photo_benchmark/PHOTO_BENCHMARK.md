# Photo benchmark: similarity cutoff and line swap (21 Nov 2026)

**Settings in use: cutoff 65** (was 70), margin 10, `ratio` scoring, conflict policy `keep_number`,
route crop fallback `check`, **line swap on** (new). Fine-tuned PaddleOCR (round 1) reads
number/destination/route crops; pretrained PaddleOCR reads whole-display crops; YOLO11s (conf 0.5,
IoU 0.7, imgsz 640). Only the nearest display of each photo is scored, as the app shows it.

## Data

- 40 photos supplied by JY on 21 Nov 2026 (20 named `NNN_<view>_<layout>_<service>`, 20 named
  `sgbus-20261120-b09_*`); kept in `models/local/photos/benchmark/` (gitignored). The `sgbus-…-b09`
  names indicate a generated batch; if any photos are rendered rather than camera frames, these
  results may be more favourable than real footage.
- Labels were written **before** the first run: `labels.csv` (service on the sign, the sign's
  destination text, and the reference endpoint it denotes). 28 photos have a destination that is an
  endpoint of the service. 12 are **NONE**: the text is a road or a place that is not an endpoint of that
  service (side displays such as `JELAPANG RD`; 317 showing `YIO CHU KANG INT`), so the correct output is
  to withhold the destination. Labelled by Claude from the visible sign text and
  `bus_information.cleaned.csv`.
- OCR is run once per photo (`results/ocr_readings.csv`); each cutoff re-runs only the matcher.

## Results by cutoff (settings in use, line swap on)

Correct = the right endpoint is shown, or the destination is withheld on a NONE photo.
Shown wrong = a wrong endpoint is shown, or any endpoint is shown on a NONE photo.

| Cutoff | Destination correct (of 28) | Withheld (of 28) | NONE withheld (of 12) | Shown wrong | Net (correct + NONE withheld − shown wrong) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 27 | 1 | 6 | 6 | 27 |
| 40 | 27 | 1 | 5 | 7 | 25 |
| 50 | 27 | 1 | 8 | 4 | 31 |
| 55 | 27 | 1 | 10 | 2 | 35 |
| 60 | 27 | 1 | 11 | 1 | 37 |
| **65 (in use)** | **27** | **1** | **11** | **1** | **37** |
| 70 | 26 | 2 | 11 | 1 | 36 |
| 75 | 26 | 2 | 11 | 1 | 36 |
| 80 | 25 | 3 | 12 | 0 | 37 |
| 90 | 22 | 6 | 12 | 0 | 34 |

Service number at 65: 33 of 40 correct, 0 wrong, 7 withheld: 3 side views had no display detected (966,
26, 64); 901 had no number crop; OCR misread 3 numbers (`927` for 922, `9128` for 912B, `1004` for 100A),
none of which is shown. Latency (2-core CPU, detection + OCR): median 284 ms per frame, range 104–597 ms.

**Before the change** (cutoff 70, no line swap): 20 of 28 destinations correct, 8 withheld, 11 of 12
NONE withheld, 1 shown wrong (net 30). **After** (cutoff 65, line swap): 27 of 28, 1 withheld, same
11 of 12 and same 1 wrong (net 37).

## Line swap

On `destination-above` signs YOLO11s often labels the smaller lower line `destination` and the large top
line `route` (or boxes only the whole display). New rule (`Settings.line_swap`, on by default): when a
destination crop exists but does not reach the cutoff for the service read, the route crop and the
whole-display text are also scored against that service's endpoints, and an accepted one is shown
(source `route_swapped` or `panel`). If they point to different endpoints, nothing is shown. The rule is
used only when the service number is known; text without a number is never swapped.

| Photo | Destination crop read | Recovered from | Shown |
| --- | --- | --- | --- |
| 111 | `RCHARD RD` (the route line) | whole display `TEMASEK AVE 111` | Temasek Avenue (loop), 100% |
| 31 | `MARINE PARADE RD` (the route line) | whole display `TOA PAYOH INT 31` | Toa Payoh Bus Interchange, 100% |
| 268 | `ANG MO KIO AVE 3` (the route line) | route crop `ANG MO KIO IND PK 2` | Ang Mo Kio Industrial Park 2, 100% |
| 272 | `LOWER DELTA RD` (the route line) | route crop `TELOK BLANGAH RISE` | Telok Blangah Rise, 100% |
| 678 | `EDGEFIELD PLAINS` (the route line) | whole display `SUNTEC TOVER 3 678` | Suntec Tower 3, 84.6% |
| 115 | `HOLGANG` (misread) | whole display `HOUGANG AVE 115` | Hougang Avenue 3 (loop), 91.7% |

Effect on the answer-key evaluation (Cody's committed OCR readings): validation destinations 24 of 27 at
65 (23 without the swap), 0 wrong either way; test 15 of 16 at 65, 0 wrong. Six validation displays
without an answer-key entry changed from withheld to shown; their human field labels (`label_text` in
`displays.jsonl`) show the shown endpoint is the sign's destination in each case (e.g. 195: destination
box labelled `MARINA CTR` → Marina Centre Bus Terminal; 51A: `TERMINATE AT` / `PANDAN GARDENS (BLK 407)`
→ Pandan Gardens (Blk 407)).

## Why 65

All rows with the line swap on.

| Cutoff | Validation net (destinations correct / wrong of 27) | Test destinations (correct / wrong of 16) | Photos net (shown wrong) |
| ---: | --- | --- | --- |
| 50 | 93 (26 / 0) | 16 / 0 | 31 (4) |
| 55 | 92 (25 / 0) | 15 / 0 | 35 (2) |
| 60 | 90 (24 / 0), one extra wrong service | 15 / 0 | 37 (1) |
| **65** | **91 (24 / 0)** | **15 / 0** | **37 (1)** |
| 70 | 91 (24 / 0) | 14 / 0 | 36 (1) |
| 80 | 88 (21 / 0) | 14 / 0 | 37 (0) |

65 is the only cutoff that is never worse than 70 on any of the three sets and adds no wrong output on
any of them. 50 and 55 score higher on validation and test but show roads on side displays as
destinations in the photos; 60 adds a wrong service on validation; 80 removes the one photo error (807)
but loses correct destinations on all three sets. The cutoff was chosen after all three sets had been
inspected, so none of them is an untouched held-out result; confirm on new footage.

The one wrong result at 65 and 70: 807's side display `YISHUN RING RD` matches Yishun Bus Interchange
(75.0%), an endpoint of 807. Only a cutoff above 75 removes it.

## Detector-confidence rule for destination/route crops (22 Nov 2026)

Rule tested: read a destination or route crop only if YOLO11s gave its box a confidence of at least T;
otherwise drop it and use the whole-display text (number tokens removed). The number crop is always kept.
T = 0.50 is today's behaviour (the detector's own filter). Same 40 photos, settings in use, one OCR pass
(`results/crop_readings.csv`); script `scripts/benchmark_crop_confidence.py`; grid
`results/crop_confidence_grid.csv`.

| T | Crops dropped (of 51) | Destination correct (of 28) | NONE withheld (of 12) | Shown wrong | Net |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **0.50 (in use)** | 0 | **27** | 11 | 1 | **37** |
| 0.60 | 3 | 27 | 11 | 1 | 37 |
| 0.70 | 7 | 27 | 11 | 1 | 37 |
| 0.75 | 10 | 26 | 11 | 1 | 36 |
| 0.80 | 12 | 26 | 11 | 1 | 36 |
| 0.85 | 14 | 26 | 11 | 1 | 36 |
| 0.90 | 23 | 25 | 11 | 1 | 35 |
| whole display only | 51 | 22 | 12 | 1 (100A → Aljunied Road) | 33 |

No threshold improved the result; from 0.75 up it removed correct readings, and reading only the whole
display was worst (22 of 28; 100A was then shown wrongly as Aljunied Road). The low-confidence
boxes (0.51–0.71) were read correctly by OCR (OCR confidence 0.95–1.00) but had the **wrong class**: e.g.
0.51 `RCHARD RD` labelled destination on a sign whose destination is `TEMASEK AVE`; 0.65 `MARINE PARADE RD`
labelled destination on `TOA PAYOH INT`. Low detector confidence here means "unsure which line this is",
not "unreadable"; the line swap already tries the other line and the whole display in that case. The
whole display reads worse because it is read as one line (`TAPIPIS NS AVE 298` vs the destination crop
`TAMPINES AVE 5`). Decision: keep T = 0.50; `--field-min-conf` in `scripts/match_reference.py` exposes it.

## Remaining miss (1 of 28)

100A: the number crop reads `1004` (not a service), so the destination `ALJUNED MRT` is searched without
a number; Aljunied Road (81.8) and Aljunied MRT station (81.5) tie within the margin, so neither is shown.

## Rerun

```
python scripts/benchmark_photo_threshold.py              # reads every photo, then scores each cutoff
python scripts/benchmark_photo_threshold.py --reuse-ocr  # scores again from results/ocr_readings.csv
```
