# Reference matching

Matches OCR text from one bus display to `bus_information.csv`, and keeps the raw OCR next to every result.

**Settings in use (app and terminal tool):** `ratio` scoring, **cutoff 70**, **margin 10**, conflict policy
`keep_number`, route crop fallback `check`. A destination is shown only if its similarity is at least 70 of
100 and it leads the next distinct reference endpoint by at least 10 points; a service number only if it
exactly equals a reference service. In the app the cutoff is the `similarity` option (default .7 = 70).
Code: `backend/app/services/reference_matching.py` (the app's `RouteMatcher` in `matching.py` calls it).

## How text reaches the fuzzy scorer

```
OCR text  ──► strip display clutter ──► upper case, punctuation to spaces ──► abbreviation table ──► fuzzy score
CSV name  ─────────────────────────────► upper case, punctuation to spaces ──► abbreviation table ──┘
```

- **Display clutter** (OCR side only): leading `>`/arrows, `VIA …` (route text follows it), trailing `-`, `TERMINATE AT`.
- **Abbreviation table** `data/reference/abbreviations.csv`: both sides map every word to one shared
  standard form, e.g. `INTERCHANGE`/`INT` → `INT`, `AVENUE`/`AVE` → `AVE`, `WDL` → `WOODLANDS`.
  `BUS` before `INT`/`TER` and the `(loop)` note are dropped. The short form is the standard because
  long generic words make different places look alike: `WOODLANDS INTERCHANGE` vs `TAMPINES INTERCHANGE`
  scores 73, `WOODLANDS INT` vs `TAMPINES INT` scores 56.
  Added 21 Nov 2026 (short forms seen on Singapore EDS and in the reference's notes): `BUSINESS`→`BIZ`,
  `BUILDING`→`BLDG`, `BEFORE`/`AFTER`→`BEF`/`AFT`, `INTERNATIONAL`→`INTL`, `TECHNOLOGICAL`/`TECHNOLOGY`→`TECH`,
  `POLYTECHNIC`→`POLY`, `UNIVERSITY`→`UNI`, `PRIMARY`/`SECONDARY`/`SCHOOL`→`PRI`/`SEC`/`SCH`, `HOSPITAL`→`HOSP`,
  `BUKIT`/`BKT`→`BT`, `TANJONG`→`TG`, `KAMPONG`→`KG`, `MOUNT`→`MT`, `PLACE`→`PL`, `CLOSE`→`CL`, `LANE`→`LN`,
  `SQUARE`→`SQ`, `JUNCTION`→`JCT`, `ESTATE`→`EST`, `CENTRAL`→`CTRL` (`HOUGANG CTRL INT`); places `CBP`→`CHANGI BIZ PK`, `NTU`→`NANYANG TECH UNI`.
  Re-running the evaluation changed similarity values only: no display changed status on validation or
  test at the cutoff in use (70), and the selected setting is unchanged. (`TERRACE` and `SAINT` are not
  added: their short forms `TER` and `ST` already mean terminal and street.)
- **Service numbers never go through the table**: upper case and space removal only, so `14E`, `70M`,
  `913T` and leading zeros are kept.
- The CSV stays one row per route. The matcher returns the reference spelling (`Toa Payoh Bus Interchange`).

## Decision rules (one display at a time)

| Evidence on the display | Decision |
| --- | --- |
| Number only | Accept if it exactly equals a reference service. Infer the destination only if that service has a single endpoint in the reference (the CSV has no direction, so most services stay "service only"). |
| Destination only | Score every distinct endpoint. Accept the best if it reaches the cutoff **and** leads the next distinct endpoint by the margin. Infer the number only if that endpoint belongs to one service. If tied candidates all share one service, that service is kept. |
| Number and destination | The exact service narrows the search to its endpoints. Below cutoff or tied → destination unresolved. If the destination matches another service's endpoint at least `margin` better, it is a **conflict** (see policy below). |
| Number read but not in the reference | Service = **unable to detect** (e.g. `147E`, `74E`, `350`). A whole-display number is never substituted. |
| Depot / not-in-service text | Not matched (`DEPOT`, `NOT IN SERVICE`, `OFF SERVICE`). |
| Route text only | Kept as read; service unresolved (the CSV has no road names). |
| No usable fields | Reason recorded: no fields detected, OCR returned nothing, or nothing matched. |

**Route crop as destination evidence** (setting `route_as_destination`). The detector sometimes labels the
destination as route. When a display has no destination crop, the route crop and the whole-display text
are both tried. `off`: route crop ignored. `check` (selected): the route crop may only flag a number it
does not fit (e.g. `13` read where the route crop reads Ang Mo Kio Int, an endpoint of 133); it is never
shown as the destination. `use`: it may also be shown. On validation `use` showed one wrong destination
(991: route text `BUKIT BATOK ST 11` matched the opposite endpoint) and gained one; `check` showed none wrong.

**Whole-display (panel) OCR.** Used for a field only when the dedicated crop is missing. Service-number
tokens in the panel text count only if they are reference services and only one is present. If crop and
panel numbers agree, both sources are logged. A panel number that is part of the crop number (`10` vs
`110`) is treated as a partial read, not a disagreement. A real disagreement is settled by the destination;
otherwise the service stays unresolved.

**Conflict policy** (chosen on validation): `keep_number` keeps the exact service and withholds only the
destination; `withhold_both` hides both.

**The app shows accepted or inferred values only.** Below-cutoff, tied, conflicting and not-in-reference
values are withheld; raw OCR is always kept.

## Settings and evaluation

- Similarity: RapidFuzz 0–100. Grid on validation: scorers `ratio`, `token_sort_ratio`, `token_set_ratio`,
  `WRatio` × cutoffs 25, 50, 60, 70, 75, 80, 90 × margins 0, 5, 10 × both conflict policies × route fallback
  `off`/`check`/`use` (`off` excluded from selection by project decision).
- Selection rule (validation only): most correct outputs minus wrong outputs; then higher precision; then
  the stricter cutoff and margin.
- Project decisions on top of that rule (20 Nov 2026):
  - Route crop fallback must be `check` or `use` (`check` was chosen: `use` showed one wrong destination).
  - Cutoff fixed at **70**. Cutoff 50 scored best on validation (24 vs 23 of 27 destinations on 20 Nov; 25 vs 23
    after the 21 Nov abbreviation additions; 0 wrong at both; current figures in `REFERENCE_MATCHING_RESULTS.md`)
    but accepts text that is only half similar and raised about twice as many conflict flags (24 vs 11), so
    70 was chosen for unseen signs. This was decided after test had been inspected at 50 and 70 (test
    destinations 15/16 and 14/16, 0 wrong at both), so the test result is not a single untouched run.
  - Photo check (21 Nov 2026, 18 photos, not labelled independently, not used to choose the cutoff): every
    best destination candidate scoring 47–64% was correct or plausible (42 Kembangan MRT station 63.4%, 20
    Changi Business Park Ave 3 51.3%, 19 Changi Airfreight Centre 48.6%, 10 Tampines Bus Interchange 47.1%);
    wrong candidates scored 35–36% (157, 983, the misread `61` bus). So 70 gives up some correct destinations
    for safety, which matches validation. A clear close-up display scores 75–100% (170X, 145, 359, 151), so
    the cutoff does not change the demo case.
  - Photo benchmark (21 Nov 2026, 40 photos labelled before the run, `evaluation/photo_benchmark/PHOTO_BENCHMARK.md`,
    full chain with the settings in use): at **70**, 20 of 28 destinations correct, 11 of 12 non-endpoint
    signs withheld, **1 shown wrong** (807 side `YISHUN RING RD` → Yishun Bus Interchange, 75%); services
    33 of 40 correct, 0 wrong. Cutoff 60 scored best (22 correct, same 1 wrong); 80 removes that wrong but
    loses 2 correct; below 50 side-display roads are shown as destinations. Cutoff kept at 70. Five misses
    no cutoff fixes: on `destination-above` signs YOLO11s labels the smaller lower line `destination`.
- Destination gold needs the answer key (sign text → reference endpoint), see below.

## Running it

All commands run from the repo root. On Windows use the same commands in a normal terminal.

### Setup (once)

```sh
pip install rapidfuzz                                   # matching only
pip install ultralytics paddlepaddle paddleocr          # photo and crop-image options
```

Local weights and test photos go in `models/local/` (gitignored, never committed):

```
models/local/
├── paddleocr/              Cody's fine-tuned PaddleOCR (inference.pdiparams/.json/.yml): number, destination, route crops
├── paddleocr-pretrained/   public en_PP-OCRv5_mobile_rec: whole-display crops (and field crops if paddleocr/ is empty)
├── yolo/best.pt            Brendan's fine-tuned YOLO11s (4 EDS classes)
└── photos/                 bus photos to try
```

With neither PaddleOCR folder filled, the public model is downloaded on first use.

**Two OCR models (since 21 Nov 2026).** Number, destination and route crops are read by the fine-tuned
model; whole-display crops (the panel fallback) by the pretrained model. The fine-tuned model was trained
on single-field crops only and misreads whole displays (`FERNVALE RD 374` → `KEAMALE "D 374`,
`51` → `AWIRS ST`), which made the panel fallback useless. On Cody's test set the fine-tuned model is
better on field crops (CER 8.2% vs 11.6%, exact match 82.2% vs 64.4%), so field crops keep it. Both models
are loaded once; each crop is read by one of them, so OCR time per crop does not change (about 31 ms).
`--panel-ocr-model-dir same` reads every crop with one model. No labelled whole-display set exists, so the
panel choice rests on the 11 photos below, not on a scored evaluation.

PaddleOCR weights seen so far (SHA-256 of `inference.pdiparams`; `inference.json` and `inference.yml` are
the same for all fine-tuned runs: `35f4f351…`, `27e91d05…`):

| Weights | `inference.pdiparams` | Status |
| --- | --- | --- |
| Round 1 fine-tuned, run `20261117-031848` | `bff74048…` | Cody's **selected** model; all OCR and matching scores in this repo use its readings; **installed in `models/local/paddleocr/` (21 Nov 2026)** |
| Round 2 fine-tuned + synthetic, `20261118-084149` | `6a35875b…` | not selected |
| First upload of 21 Nov 2026, replaced the same day | `d717aa26…` | fine-tuned, but not in Cody's records; most likely the 5k-split run `ocr5k-split-b32-e20-20261120-084105` (validation only, test unopened, not selected); do not use |
| Public pretrained `en_PP-OCRv5_mobile_rec` | `3ec8a97e…` | in `models/local/paddleocr-pretrained/` |

End-to-end check, 21 Nov 2026 (`--photo`, YOLO11s boxes shared by all three setups, 2-core CPU,
median of 3 runs). Pretrained = public model for every crop; fine-tuned = round 1 for every crop;
hybrid = round 1 for field crops, pretrained for whole-display crops (the setting in use).

| Photo | Pretrained | Fine-tuned | Hybrid (in use) |
| --- | --- | --- | --- |
| bus_145 | Toa Payoh Bus Interchange, 85.7% | Toa Payoh Bus Interchange, 92.3% | Toa Payoh Bus Interchange, 92.3% |
| bus_359 | Pasir Ris Bus Interchange, 81.8% | Pasir Ris Bus Interchange, 81.8% | Pasir Ris Bus Interchange, 81.8% |
| bus_170X | JB Sentral Bus Terminal, 83.3% | JB Sentral Bus Terminal, 75.0% | JB Sentral Bus Terminal, 75.0% |
| bus_374 | Fernvale Road, 100% (whole display) | conflict, no destination | Fernvale Road, 100% (whole display) |
| three_buses, distant `51` bus | 51, service only | **61 shown as accepted** (wrong) | 61 disputed by whole display `51`; withheld |
| bus_20 | service only | service only | service only (see note) |
| bus_143 | service only (destination unread) | service only | service only |
| bus_42, bus_157, bus_82, bus_983 | service only | service only | service only |

Matched destinations: pretrained 4 of 11 photos, fine-tuned 3, hybrid 4. Wrong results shown as accepted:
pretrained 0, fine-tuned 1, hybrid 0. On these photos hybrid ties pretrained; its field-crop advantage
comes from Cody's test set, not from these photos. Note on bus_20: the display says `TAMPINES-CHANGI BIZ PK`
(origin-destination of a loop service). Even typed exactly it scored 58.8% against the reference endpoint
`Changi Business Park Avenue 3 (loop)`; with `BUSINESS`→`BIZ` added it scores 63.4%, still below 70,
because the origin `TAMPINES-` is part of the text. `CHANGI BIZ PK` alone with service 20 is accepted.

Second batch, 21 Nov 2026 (hybrid OCR, web photos about 550–710 px wide):

| Photo | Result | Cause |
| --- | --- | --- |
| bus_151 | **151, Hougang Central Bus Interchange, 88.2%** | number crop read `11`; whole display read `151`; destination picked 151 (dispute rule) |
| bus_307 | 307, service only | destination text 9 px high, unreadable |
| bus_19 | 19, service only | destination text 11 px high (`SMMG ARTSSNT CTR`) |
| bus_10 | unable to detect | number crop 20 px high read `1` (shows `10`); the side display is found but ranked second by size |
| neg_sign_orchard, neg_sign_94009 (bus stop signs) | no display found | correctly ignored |
| neg_back_48 (rear of a bus) | no display found | correctly ignored |

All 3 negatives produce no detection, so nothing is matched. The misses come from text 8–14 px high in
low-resolution photos; padding the crops does not fix it consistently (tested 0, 15%, 30% of box height:
`51` became correct, `151` became `161`, destinations got worse), so padding is not used. Use
frames where the display is at least about 30 px high (the photos that matched have 15–68 px digits and
legible destination text).

Latency, per frame (median): detection 125–180 ms; OCR 31 ms per crop for both models, 80–226 ms per frame
(2–7 crops); matching under 3 ms; total about 0.2–0.4 s. Loading the second model adds about 7 MB and
start-up time only.

### Try one display: `scripts/match_reference.py`

Every run prints raw OCR, the matched reference text, the similarity and the decision for each field,
then the overall result and the reason. Add `--json` for the full result.

| Input | Command |
| --- | --- |
| Full chain on a photo (YOLO11s → PaddleOCR → matching) | `python scripts/match_reference.py --photo models/local/photos/bus_374.png --save-dir runs/matching` |
| Every crop saved by `--photo --save-dir`, OCR shown per crop | `python scripts/match_reference.py --crop-dir runs/matching/bus_374` |
| Crop images (PaddleOCR → matching) | `python scripts/match_reference.py --number-crop num.png --destination-crop dest.png` |
| Typed OCR text | `python scripts/match_reference.py --number 14E --destination "> TAMP1NES INT"` |
| Whole-display text only | `python scripts/match_reference.py --panel "65 TAMPINES INT"` |
| Dataset crop (with human label) | `python scripts/match_reference.py --review-id A001` |
| Every display on a dataset photo | `python scripts/match_reference.py --image <source photo file name>` |

Options:

| Option | Meaning |
| --- | --- |
| `--number`, `--destination`, `--route`, `--panel` | OCR text for each field (`--panel` = whole display) |
| `--number-crop`, `--destination-crop`, `--route-crop`, `--panel-crop` | crop images to read with PaddleOCR first |
| `--crop-dir` | folder of `display-N_<number/destination/route/panel>.png` crops; reads all, grouped by display |
| `--photo` | bus photo for the full chain |
| `--save-dir` | with `--photo`: write each crop and an annotated `detections.png` to `<dir>/<photo name>/` |
| `--closest-only` | with `--photo`: report only the largest display (the nearest bus); all displays are still listed by size |
| `--detector` | YOLO11s weights (default `models/local/yolo/best.pt`) |
| `--ocr-model-dir` | PaddleOCR weights for number, destination and route crops (default `models/local/paddleocr/`) |
| `--panel-ocr-model-dir` | PaddleOCR weights for whole-display crops (default `models/local/paddleocr-pretrained/`); `same` = use `--ocr-model-dir` for every crop |
| `--route-as-destination off/check/use` | route crop fallback when there is no destination crop |
| `--cutoff`, `--margin`, `--scorer`, `--conflict` | matching settings (default: chosen on validation, `results/selected_setting.json`) |
| `--reference` | route CSV (default `data/reference/bus_information.cleaned.csv`) |
| `--json` | print the full result as JSON |

Photo mode handles several buses: each display is matched separately and listed largest first, because the
nearest bus's display appears largest. `--closest-only` reports just that one. When YOLO11s draws no display box, a lone line (no display box, no number) is attached to the display it
sits directly above or below (horizontal overlap, gap under one line height), so a bus is not split into
two displays. Photo mode runs YOLO11s at conf 0.50, NMS IoU 0.70, size 640, groups boxes into displays with the app's
association code, and drops a second display box that overlaps a more confident one by IoU ≥ 0.5. Each
crop is read as one line, so two-line signs read worse than in Cody's line-split evaluation.

Photo mode also prints the time per stage for that frame (models loaded and warmed up first, so start-up
is excluded): detection, grouping, OCR (total over all crops), matching and the total.

Measured on a 2-core cloud CPU with no GPU (Brendan's YOLO11s, public pretrained PaddleOCR), 20 Nov 2026:

| Photo | Detection | OCR (crops) | Matching | Total per frame |
| --- | ---: | ---: | ---: | ---: |
| bus_983 (1 display) | 204 ms | 154 ms (2) | 0.3 ms | 359 ms |
| bus_374 (1 display) | 196 ms | 208 ms (3) | 3.5 ms | 408 ms |
| three_buses (3 displays) | 210 ms | 385 ms (7) | 1.4 ms | 596 ms |
| bus_42 (1 display) | 196 ms | 355 ms (4) | 4.3 ms | 555 ms |
| bus_170X (1 display) | 193 ms | 205 ms (3) | 1.3 ms | 399 ms |

OCR grows with the number of crops (about 55–75 ms each here); detection is roughly constant; matching is
under 4 ms. A GPU mainly shortens detection. Cody's OCR runs measured about 65 ms per crop for PaddleOCR on
a Mac CPU (`evaluation/ocr_runs/*/predictions.jsonl` on the OCR branch).

Example cases worth trying:

```sh
python scripts/match_reference.py --number 148 --destination "CLEMENTI INT"        # conflict: 148 vs 14E
python scripts/match_reference.py --destination "WDL INT/MRT"                      # place short form
python scripts/match_reference.py --number 147E                                    # not in reference
python scripts/match_reference.py --number 30 --destination "> BEDOK NTH DEPOT"    # not in service
python scripts/match_reference.py --number 30 --destination "> BOON LAY" --cutoff 50 --margin 5
```

### Rebuild and evaluate

```sh
python scripts/clean_bus_reference.py              # cleaned CSV + cleaning report
python scripts/build_matching_displays.py          # group dataset crops into displays
python scripts/draft_destination_answer_key.py     # automatic draft key (never overwrites answer_key.csv)
python scripts/evaluate_reference_matching.py      # grid on validation, test once, results .md
python -m pytest -q tests/test_reference_matching.py tests/test_matching.py
```

Outputs: `evaluation/reference_matching/REFERENCE_MATCHING_RESULTS.md` and `results/` (grid, selected
setting, per-display decisions).

## Answer key

`evaluation/reference_matching/answer_key.csv` is the confirmed key used for scoring: one row per distinct
(number label, destination label) with the correct reference `endpoint`, `NONE` (not a destination, e.g.
route text, or no fitting endpoint in the reference) or `NOT_IN_SERVICE`, and who confirmed it
(`confirmed_by`). It was confirmed by Claude at the user's request on 20 November 2026: the closest
reference endpoint, or `NONE` where none fits. `answer_key.draft.csv` is the automatic draft it started
from; re-running the draft script never overwrites the confirmed key. To change an entry, edit
`endpoint` and `confirmed_by`, then re-run the evaluation.
