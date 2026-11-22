# Reference matching

Matches OCR text from one bus display to `bus_information.csv`, and keeps the raw OCR next to every result.

**Settings in use (app and terminal tool):** `ratio` scoring, **cutoff 65** (70 until 21 Nov 2026), **margin 10**,
conflict policy `keep_number`, route crop fallback `check`, **line swap on**. A destination is shown only if
its similarity is at least 65 of 100 and it leads the next distinct reference endpoint by at least 10
points; a service number only if it exactly equals a reference service. In the app the cutoff is the
`similarity` option (default .65 = 65).
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
| Number and destination | The exact service narrows the search to its endpoints. If the destination crop does not reach the cutoff, the route crop and the whole display are tried against the same endpoints (**line swap**, below). Still below cutoff or tied → destination unresolved. If the destination matches another service's endpoint at least `margin` better, it is a **conflict** (see policy below). |
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

**Line swap** (setting `line_swap`, on; added 21 Nov 2026). On `destination-above` signs YOLO11s often labels
the smaller lower line `destination` and the large top line `route`. When the service number is known, a
destination crop exists and it does not reach the cutoff for that service, the route crop and the
whole-display text are scored against that service's endpoints; an accepted one is shown (source
`route_swapped` or `panel`; the terminal tool prints "from route crop: lines swapped"). If they point to
different endpoints, nothing is shown. Effect: photo benchmark 20 → 27 of 28 destinations with no new wrong
result; validation 23 → 24 of 27, test unchanged, 0 wrong (`evaluation/photo_benchmark/PHOTO_BENCHMARK.md`).

**Whole display read line by line** (terminal tool, photo mode; added 22 Nov 2026). Read as one image, a
two-line display comes back garbled (`TAPIPIS NS AVE 298` for `TAMPINES AVE 3` / `TAMPINES AVE 5`). The
display crop is therefore also split into its text lines (`backend/app/services/panel_lines.py`: LED text is
bright on a dark panel, so text rows stand out in a row-brightness profile; the number column from the
detector's number box is blanked first and left out of the line crops), and each line is read by the
pretrained model. On EDS signs the destination is the tallest line, so lines are passed to the matcher
tallest first (`panel_lines`). Use in matching: with a destination crop that does not fit the service read,
the tallest line is tried first, then the route crop, then the other lines and the one-image read; with no
destination crop, the tallest line replaces the one-image read (the others are a fallback when the service
is known). With a number but no destination, only the tallest line is used, so a road on the smaller line
cannot be taken as the destination. When the destination came from a line, the other line is the "via"
text of the message. Lines are read only when the field crops leave the destination unconfirmed or give no
route text. Photos with a single-line display (side displays) or lines too close to separate fall back to
the one-image read. Effect on the 40-photo benchmark at cutoff 65: same 27 of 28 destinations and 1 wrong
(the field crops and the line swap already covered these signs); 23 of 37 displays split into lines; the
line reads were far closer to the sign (e.g. 268 `ANG MO KIO IND PK 2` / `ANG MO KIO AVE 3`, 100A
`ALJUNIED MRT`); 3 messages gained a "via" part (678 `via Edgefield Plains`, 800 `via Yishun St 71`, 115).
At cutoff 90, 24 instead of 22 destinations are correct. Latency, same run, 116 frames: median 279 → 277 ms,
p95 391 → 412 ms (lines read only when needed; reading them on every frame cost +33 ms median, +127 ms p95).

**Whole-display (panel) OCR.** Used for a field only when the dedicated crop is missing. Service-number
tokens in the panel text count only if they are reference services and only one is present. If crop and
panel numbers agree, both sources are logged. A panel number that is part of the crop number (`10` vs
`110`) is treated as a partial read, not a disagreement. A real disagreement is settled by the destination;
otherwise the service stays unresolved.

**Conflict policy** (chosen on validation): `keep_number` keeps the exact service and withholds only the
destination; `withhold_both` hides both.

**The app shows accepted or inferred values only.** Below-cutoff, tied, conflicting and not-in-reference
values are withheld; raw OCR is always kept.

## Announcement (message for each display)

Every match result carries `announcement`, a one-line message built only from what was confirmed
(`backend/app/services/announcement.py`). The terminal tool prints it as `Message:`; the app's `RouteMatcher`
returns it as `match.announcement` and the results page shows it in the route card. The app passes the
number, destination and route crops (each only if its OCR confidence passes `ocr_threshold`); it does not
OCR the whole display yet, so the whole-display parts of the line swap apply in the terminal tool only. The service number and destination are stated only when the matcher accepted
them; route text cannot be checked against the reference (it has no road names), so it is added as "via …"
only when it reads like a road name: at least two words, no single-letter word, no number except at the end,
and the last word a road or place ending (`RD`, `AVE`, `ST`, `DR`, `CRES`, `WAY`, `INT`, `MRT`, …) or the
first word `JLN`/`LOR`/`UPP`. With swapped lines (the destination came from the route crop), the destination
crop's text is used as the "via" text.

| What was confirmed | Message |
| --- | --- |
| Service + destination + road-like route | `Bus 174 to Kampong Bahru Bus Terminal, via Corporation Rd.` |
| Service + destination | `Bus 174 to Kampong Bahru Bus Terminal.` |
| Service; destination not read | `Bus 64 is approaching. Destination could not be read.` |
| Service; destination read but withheld (conflict, tie, below cutoff) | `Bus 148 is approaching. Destination could not be confirmed.` |
| Destination; service not confirmed (shared by several services, or number not in the reference) | `A bus to Toa Payoh Bus Interchange is approaching. Bus number could not be confirmed.` |
| Number read but not a service, no destination | `A bus is approaching. Bus number and destination could not be confirmed.` |
| Route text only | `A bus is approaching, via Jln Besar. Bus number and destination could not be read.` |
| Depot / not-in-service text | `Bus not in service.` |
| No display detected | no message |

Destination names are the reference names as written (`Temasek Avenue (loop)`). Route text is tidied for
reading (`UPP SERANGOON RD` → `Upp Serangoon Rd`) but not corrected, so an OCR error that still looks like a
road name (e.g. `RCHARD RD`) can appear. Known risk: a whole-display-only read of a side display such as
`JLN BESAR` scores 72 against `Jalan Loyang Besar`, which is then announced as `Bus 354 to Jalan Loyang Besar.`

## Settings and evaluation

- Similarity: RapidFuzz 0–100. Grid on validation: scorers `ratio`, `token_sort_ratio`, `token_set_ratio`,
  `WRatio` × cutoffs 25, 50, 55, 60, 65, 70, 75, 80, 90 × margins 0, 5, 10 × both conflict policies × route fallback
  `off`/`check`/`use` (`off` excluded from selection by project decision).
- Selection rule (validation only): most correct outputs minus wrong outputs; then higher precision; then
  the stricter cutoff and margin.
- Project decisions on top of that rule (20 Nov 2026):
  - Route crop fallback must be `check` or `use` (`check` was chosen: `use` showed one wrong destination).
  - Cutoff fixed at **65** (21 Nov 2026, with the line swap; see the photo benchmark below). Until then it was
    fixed at **70**: cutoff 50 scored best on validation (24 vs 23 of 27 destinations on 20 Nov; 25 vs 23
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
    loses 2 correct; below 50 side-display roads are shown as destinations. Five misses no cutoff fixed:
    on `destination-above` signs YOLO11s labels the smaller lower line `destination`.
  - Detector-confidence rule for destination/route crops (22 Nov 2026, same 40 photos): dropping boxes below
    0.60–0.70 changed nothing; 0.75 and above lost correct destinations (0.90: 25 of 28; whole display only:
    22 of 28 and 1 wrong). Boxes below about 0.72 were mostly the right text with the wrong class, which the
    line swap already handles. Rule not adopted (every box the detector keeps at 0.50 is read).
  - After adding the line swap (same photos, OCR not re-run): at **65**, 27 of 28 destinations correct, 11 of
    12 withheld, 1 shown wrong (the same 807). 65 is the only cutoff never worse than 70 on validation
    (91 vs 91 net), test (15 vs 14 of 16) and the photos (37 vs 36), with no added wrong output; 50–55 show
    side-display roads as destinations, 60 adds a wrong service on validation, 80 loses correct destinations
    everywhere. **Cutoff set to 65.** Chosen after validation, test and the photos had all been inspected, so
    no untouched held-out result exists; confirm on new footage.
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

Latency: see "Latency per frame" below (median 250 ms, p95 351 ms). Loading the second OCR model adds about
7 MB and start-up time only.

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

**Latency per frame** (22 Nov 2026): 58 photos in `models/local/photos/` × 3 passes = 174 frames; 2-core
Intel Xeon 2.3 GHz cloud CPU, no GPU; batch size 1; models loaded and warmed up first (start-up excluded);
settings in use (YOLO11s 640 px, fine-tuned PaddleOCR for field crops, pretrained for whole-display crops
and their lines, lines read only when needed, matcher at cutoff 65). Median is the typical frame; p95 is the
frame time that 95% of frames stay under.

| Stage | Median | p95 | Mean | Max |
| --- | ---: | ---: | ---: | ---: |
| Detection (YOLO11s) | 154 ms | 217 ms | 155 ms | 270 ms |
| Grouping boxes into displays | 0.1 ms | 0.1 ms | 0.1 ms | 0.3 ms |
| OCR, all crops in the frame | 126 ms | 276 ms | 133 ms | 562 ms |
| — per crop | 33 ms | 55 ms | 37 ms | 101 ms |
| — crops per frame | 4 | 6 | 3.5 | 11 |
| Reference matching, all displays | 0.9 ms | 1.6 ms | 0.9 ms | 2.3 ms |
| **Total** | **282 ms** | **467 ms** | **289 ms** | **735 ms** |

The total's p95 is measured on whole frames, so it is lower than the sum of the stage p95s (a frame is rarely
slow in every stage at once). OCR time grows with the number of crops (about 33 ms each); detection is
roughly constant; matching is negligible. The shared cloud CPU varies between sessions: on 21 Nov the same
photos without line reads measured 250 ms median, 351 ms p95; on 22 Nov, in one run, 279 ms / 391 ms without
line reads and 277 ms / 412 ms with them. At p95 a frame takes under 0.5 s on this CPU, so sampling one frame
every 0.5–1 s leaves headroom. A GPU mainly shortens detection (Brendan measured YOLO11s at 26 ms median,
37 ms p95 on his GPU). Cody's OCR runs measured about 65 ms per crop for PaddleOCR on a Mac CPU
(`evaluation/ocr_runs/*/predictions.jsonl` on the OCR branch).

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
