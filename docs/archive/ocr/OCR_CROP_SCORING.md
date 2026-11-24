# Saved crop scoring and three-model tables

## Train and validation rows populated — 15 November 2026

Latest presentation:
`.cache/ocr-baselines/three-output-tables-20261115-04/tables.html`.
The provisional view now includes Train scores for all three pretrained OCR
models, alongside the previous validation scores. This is recognition/evaluation
on the training split, **not fine-tuning**. Test remains reserved, panel text N/A,
and the human-verified evidence view remains pending.

All 1,917 training crop IDs are retained. In accordance with existing exclusions,
1,395 records are skipped before OCR. The scored subset is 522 full-text AI label
candidates: 381 numbers, 74 destinations and 67 route crops. Each engine successfully
recognised 521 candidates; the same one unresolved layout is retained as an empty
hypothesis in the 522-crop denominator. Do not interpret all 1,396 stored error
statuses as OCR failures: 1,395 are policy/readability skips outside the scored
subset. All 24 training aggregate rows reconcile to per-crop edit/exact totals.

Training inference sources/settings and predictions are retained in
`.cache/ocr_runs/easyocr-train-cpu-20261115-02/`,
`.cache/ocr_runs/trocr-train-mps-20261115-01/`, and
`.cache/ocr_runs/paddle-train-cpu-20261115-01/`.
Sources and pretrained cache weights passed before/after hash checks. Training
geometry is automatically frozen once with `scripts/freeze_automatic_ocr_layout.py`
and reused unchanged across models. It is explicitly unreviewed algorithm output;
validation's earlier AI-reviewed geometry differs. Native devices and CPU
quantisation settings also vary, so these split results are not a controlled
learning/preprocessing ablation or comparable latency ranking.

`scripts/run_easyocr_crops.py` (EasyOCR/public TrOCR) and
`scripts/run_paddle_crops.py` accept `--split train --review-manifest ...
--crop-root ...`. The explicit inventory prevents implicit discovery of test
data. Exact run commands are retained beside each run. The first EasyOCR attempt
failed before inference at a sandbox-restricted optional chip probe; a retry
records unavailable chip metadata rather than failing recognition. The incomplete
CPU TrOCR attempt was superseded by the complete GPU run; its predictions were
not mixed into the final run.

`scripts/score_ocr_training_split.py` verifies all three training runs, checkpoint
identity against validation, candidate denominators and shared training layout;
it produces raw/normalised training diagnostics, a combined scoped configuration,
official pending reports and three-table presentation. Output/evidence:
`.cache/ocr_training/train-split-evaluation-20261115-01/`.
The scorer supports `baseline.runs` for disjoint split/population scopes with
separate device/layout identities; overlapping scopes or duplicate predictions
are rejected. The older single-`run_dir` configuration remains supported.

## Populated provisional cells — 15 November 2026

`.cache/ocr-baselines/three-output-tables-20261115-02/tables.html` is the current
three-table presentation. It defaults to numerical **provisional AI-label
agreement**, with selectable raw/Step 4-normalised and annotation/predicted views.
Validation cells contain the calculated per-field CER/WER/exact match from the
108-crop diagnostic subset (67 annotation, 41 predicted). `Crops (n)` shows actual
compared subset counts, with inventory counts underneath. No train/test/panel
text metrics are invented.

The Evidence selector also provides the separate human-verified benchmark view,
whose metrics remain pending at zero eligible crops. Provisional values do not
change source labels, review gates or verified report cells. CSV exports include
`score_basis` and `candidate_crops` to retain that distinction.

Reproduce using `scripts/prepare_ocr_template_tables.py` with the original
training/validation inventory manifests, current verified `--report`, and
`--diagnostic-summary .cache/ocr_metrics/diagnostic-20261115-01/diagnostic_summary.csv`.
Existing directories are refused. This supersedes the earlier presentation below
as the latest user-facing view. The handoff ZIP includes it under `ocr_tables/`.

## Three-table presentation — 15 November 2026

The requested six-column presentation now has **one visible table per model**:
`.cache/ocr-baselines/three-output-tables-20261115-01/tables.html`. Choose raw or
Step 4-normalised scoring and annotation or predicted crops using the controls;
populations/modes are never pooled. Each inventory count includes its eligible
scoring denominator beneath it. Individual model CSVs retain both modes and
populations as labelled rows. Values in CSV are fractions; HTML shows percentages.
The current matching ZIP includes the same presentation under `ocr_tables/`.
Current eligible count remains zero, so numerical accuracy is Review pending.
Train is not run, test is reserved, whole-panel text is N/A. The separate scorer's
full baseline/fine-tuned comparison report remains available as described below.

Observed implementation, 13 November 2026: `scripts/score_ocr_crops.py` freezes
crop-review eligibility and scores saved raw predictions. It produces separate
raw and normalised HTML tables for EasyOCR, public TrOCR and PaddleOCR, with baseline and fine-tuned columns
side by side. It never imports an OCR engine, opens image pixels, trains a model
or triggers inference. These are project conventions, not rubric requirements.

## Freeze a review snapshot

Use v4 review exports with `review_id` and the full source metadata, such as the
new exports from `scripts/import_ocr_review_decisions.py`. Do not supply the early
ten-column loose-crop CSV directly. Pass each annotation/prediction review file
explicitly; no dataset discovery or reserved-test access happens automatically.

```sh
python3 scripts/score_ocr_crops.py freeze \
  --review /path/to/annotation/review.csv \
  --review /path/to/prediction/review.csv \
  --output /path/to/new-scoring-manifest.json
```

The parent directory must exist. The command refuses an existing output file.
The snapshot retains all rows, review-input SHA-256 hashes, policy, and individual
eligibility blockers. It hashes the snapshot and recomputes review eligibility
when loading it. A hash detects changes; it does not authenticate human review.

The existing human-review gate is reused, with an additional explicit
`field_review_status=reviewed` requirement. Known group, source-image-hash or
crop-hash overlap across splits blocks all affected rows. Source/crop hashes are
validated as metadata and compared with saved predictions; source image bytes
are not verified by this command. Complete the separate source/group audit.

AI-only, incomplete human review, partial, illegible, blank, absent, wrong-field,
unresolved target/group/correspondence, excluded and panel-context rows cannot
enter primary text scoring. Coverage retains their states and overlapping
blocker counts. No training-ready flags are promoted.

## Configure saved runs

Copy `docs/ocr_crop_comparison.example.json` to a local configuration. Include
exactly `easyocr`, `trocr` and `paddleocr`. A null variant means **Not run**.
An explicitly unavailable model uses `{"status": "Unavailable"}`. To score one
variant, replace null with this object:

```json
{
  "run_dir": "../saved-run-directory",
  "splits": ["valid"],
  "input_sets": ["annotation", "prediction"]
}
```

Run directories resolve relative to the configuration file and must contain
`report.json` and `predictions.jsonl` in the current crop runner's format.
`report.json` must explicitly identify its engine (`easyocr`, `trocr` or
`paddleocr`) and declare `reference_matching_used=false`. Older reports without
an engine need an explicit documented conversion, not a guessed model identity.
No Paddle adapter or weights are installed by this workflow.

Declare only populations actually attempted: missing predictions within the
declared scope count as failures, including when an entire prediction file is
empty. Populations outside that scope remain **Not run**. Unknown/duplicate IDs,
changed crop/source hashes, crop paths, classes or input sets fail validation.
Run scopes cannot include predictions outside the declared split/population.

The configuration labels variants; it cannot prove training provenance. Only
place a verified fine-tuned checkpoint in `finetuned`, with its training lineage
recorded alongside the run. The older supplied TrOCR remains unsuitable as
verified fine-tuning evidence until provenance is resolved. Freeze preprocessing
and line layouts for a controlled baseline/fine-tuned comparison; the report
retains each run's declared settings for review, rather than asserting they match.

## Generate the tables

```sh
python3 scripts/score_ocr_crops.py report \
  --manifest /path/to/new-scoring-manifest.json \
  --config /path/to/comparison.json \
  --output /path/to/new-results-directory
```

The output directory must not exist. Results are prepared in a staging directory
and published only when complete:

| File | Contents |
| --- | --- |
| `tables.html` | Six tables: primary raw and secondary normalised for each model, with baseline/fine-tuned CER, WER, exact match, statuses and shared inventory/eligible counts. Expandable details include text rules, identity, coverage, failures and latency. |
| `summary.csv` | Aggregate rows per model, variant, `scoring_mode` (`raw`/`normalised`), split, input set and field. Error/accuracy values are fractions, not percentages; nulls export as empty cells. |
| `report.json` | Schema 2 result including both policies, manifest/config/run-input hashes, model/processor identities, raw `cells`, secondary `normalised_cells`, per-crop scored outcomes and separate `text_records`. Frozen eligibility manifests remain schema 1 and compatible with earlier snapshots. |
| `text_records.csv` | Per-crop raw and normalised OCR/reference strings, scoring hypotheses, eligibility, reference-review provenance and prediction status. Includes pending and failed rows within available run scopes; no invented output for unrun variants. |

All train/valid/test, annotation/prediction and three text classes are represented;
panel-context rows explicitly say **Not applicable**. Missing populations say
**No samples** within a run scope. Available populations without eligible text say
**Review pending**. Unrun or unavailable variants have null metrics, never zeros.
An eligible subset can be scored while other rows remain pending; the denominator
is always shown and should not be presented as full-inventory accuracy.

## Current eligible-example scoring — 13 November 2026

The requested six-column presentation (`Split`, `Crop class`, `Crops (n)`,
`CER (%)`, `WER (%)`, `Exact match (%)`) is available at
`.cache/ocr-baselines/template-tables-20261113-01/tables.html`, with CSV and hashed
source provenance alongside it. It separates models, text modes and crop
populations. Training counts come from the training handoff, not inference runs;
validation counts come from the validation handoff and agree with saved scoring
inventory. Whole-panel `front_eds` counts are context counts with N/A metrics.
Test counts and scores remain reserved. Screenshot example values were not used.
Generate a new copy using `scripts/prepare_ocr_template_tables.py` with explicit
`--training-manifest`, `--validation-manifest`, `--report` and `--output` paths.

**Observed evidence:** the latest challenge-excluded validation working snapshot
has 157 annotation crops and 114 detector-predicted crops, with **zero eligible
rows**. No completed human decisions were found in the review workspace.

| Field | Annotation crops | Detector-predicted crops | Eligible in either population |
| --- | ---: | ---: | ---: |
| Service identifier | 60 | 42 | 0 |
| Destination | 55 | 35 | 0 |
| Route/road text | 42 | 37 | 0 |

Regenerated outputs are at `.cache/ocr-baselines/eligible-scoring-20261113-01/`:
`tables.html`, `summary.csv`, `report.json`, `text_records.csv`, the frozen
`manifest.json` and saved-run `comparison.json`. Each model retains separate
annotation/prediction cells per field for both text modes. CER, WER and field
exact match are null / **Review pending**, rather than zero accuracy. Reference
review, field/group decisions and predicted-crop correspondence remain gates;
normalising a pending label does not pass them. No test images were accessed.

After importing actual review decisions, freeze a new manifest from the resulting
review exports and rerun the report command above with the same compatible saved
predictions. Eligible examples will then receive micro CER/WER and per-field
exact match separately by population and text mode, with failed/missing calls
retained in eligible denominators. A partial eligible subset is labelled by its
count; it does not establish full-inventory or end-to-end accuracy.

## Step 4 text normalisation

For the downstream reference-matching owner, use
[the matching handoff guide](OCR_MATCHING_HANDOFF.md). Its builder exports
OCR-only inputs separately from the evaluation references, with failure/challenge
states preserved and a byte-pinned copy of the route candidate CSV.

Apply the following transformations equally to **predictions and references**,
using the same eligible crop IDs for every model and both scoring modes:

| Mode | Unicode and case | Whitespace | Preserved content |
| --- | --- | --- | --- |
| Primary raw (`eds-crop-raw-v1`) | NFC; case preserved | Collapse word whitespace within each line to one ASCII space; trim line padding; remove empty layout lines; preserve remaining line breaks | Punctuation, abbreviations, symbols and service-identifier leading zeros |
| Secondary normalised (`eds-crop-normalised-v1`) | NFC, Unicode `casefold()`, then NFC | Collapse all Unicode whitespace, including line breaks, to one ASCII space; trim ends | Punctuation, abbreviations, symbols and leading zeros; letter case follows casefold |

For example, synthetic `  Ab.\nRD  ` becomes `Ab.\nRD` for primary scoring and
`ab. rd` for secondary scoring (`\n` here denotes a real line break).
`00B` becomes `00b`, never an integer. `RD.` stays `rd.`, not `road`.
Unicode casefold can change character counts (for example `ß` → `ss`); each mode
calculates edit counts and denominators from its own transformed reference.
Neither mode removes punctuation, expands abbreviations, repairs spelling,
substitutes lookalike characters, invents a character alphabet or uses route data.

Stored annotations and engine `raw_text` are never overwritten. Text records retain:

- `raw_ocr_text` and `raw_reference_text`: exact source strings, including padding,
  case and real line breaks.
- `raw_ocr_scoring_text` and `raw_reference_scoring_text`: primary spacing/NFC
  transformation applied to each side.
- `normalised_ocr_text` and `normalised_reference_text`: secondary transformation.
- `raw_scoring_hypothesis` and `normalised_scoring_hypothesis`: use empty strings
  for error/missing calls, even when saved diagnostics contain partial text.

Pending/AI-only references may appear in text exports for review, with their
reviewer type, legibility and eligibility. Transforming them does not make them
ground truth. `[UNK]` is still annotation syntax and never scored as literal text;
casefolding a pending export to `[unk]` does not change that exclusion.
Missing OCR is JSON null in the source-text fields, with explicit `missing`
status (CSV exports null as an empty cell); a successful empty string remains
distinguishable by `success` status. Unavailable/unrun variants have no text rows.

WER splits on Unicode whitespace in both modes.
CER/WER are micro totals of edit distance divided by reference characters/words,
not means of row percentages. Insertion errors may exceed 100%. A service number
is usually one token, so its WER overlaps substantially with exact correctness.

Every model uses the same frozen eligible IDs. Failed calls, unresolved-layout
errors and missing predictions use an empty hypothesis, even if an error record
retains partial text. Empty successful output is scored as empty. Blank/absent
cases are counted separately but this primary text scorer does not compute
exact-empty/abstention scores; partial-span alignment is also outside this scorer.

Attempted/completed/failed/empty and latency summarize saved inventory predictions;
`missing` counts eligible rows without a prediction. Latency median/p95 use only
successful crops with recorded `crop_total_ms`, including empty successful output.
The run identity carries hardware/warmup/timing boundaries where supplied; absent
metadata stays absent, not inferred. Accuracy outcomes retain their own eligible
denominators. Crop scores do not establish detector recall or end-to-end accuracy.

Generated manifests contain labels and reports contain raw reference/hypothesis
outcomes. Keep them local, outside the implementation commit, even though they
contain no embedded images. No generated files are staged by these commands.

## Verification

```sh
python3 -m unittest tests.evaluation.test_crop_scoring -v
```

Fixtures are entirely synthetic, require no image files or model downloads, and
exercise both CLI commands, review gates, split overlap, missing/error outputs,
hash/ID rejection, micro metrics, case/newline handling, HTML escaping and overwrite
protection. Additional cases check Unicode NFC/casefold, leading zeros,
punctuation, symmetric normalisation, distinct mode denominators, unchanged source
strings/CSV newlines and failure/missing/review gates in normalised scoring.
An all-three-model synthetic check deliberately gives annotation and predicted
crops different edit counts and confirms their eligible denominators stay separate.
These checks validate software behaviour, not real OCR performance.
