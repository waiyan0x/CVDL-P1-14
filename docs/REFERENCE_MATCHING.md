# Reference matching

Matches OCR text from one bus display to `bus_information.csv`, and keeps the raw OCR next to every result.
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
  `WRatio` × cutoffs 25, 50, 60, 70, 75, 80, 90 × margins 0, 5, 10 × both conflict policies.
- Selection rule (validation only): most correct outputs minus wrong outputs; then higher precision; then
  the stricter cutoff and margin. Test runs once with the chosen setting.
- Destination gold needs the answer key (sign text → reference endpoint), see below.

## Running it

```sh
python scripts/clean_bus_reference.py              # cleaned CSV + cleaning report
python scripts/build_matching_displays.py          # group crops into displays
python scripts/draft_destination_answer_key.py     # draft answer key (needs a human check)
python scripts/evaluate_reference_matching.py      # grid on validation, test once, results .md
python scripts/match_reference.py --number 14E --destination "> TAMP1NES INT"   # try one display
python scripts/match_reference.py --review-id A001                             # dataset crop
```

## Answer key: how to check it

`evaluation/reference_matching/answer_key.draft.csv` has one row per distinct (number label, destination
label). For each row, put the correct reference name in `confirmed_endpoint`: copy `proposed_endpoint`
if it is right, type the right CSV name if not, or write `NONE` (not a destination, e.g. route text) or
`NOT_IN_SERVICE`. Rows marked `check` need the closest look. Then re-run the evaluation; the results
file reports how many entries a person confirmed.
