# Saved crop scoring and three-model tables

Observed implementation, 13 November 2026: `scripts/score_ocr_crops.py` freezes
crop-review eligibility and scores saved raw predictions. It produces three HTML
tables (EasyOCR, public TrOCR and PaddleOCR), with baseline and fine-tuned columns
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
| `tables.html` | Three standalone tables with baseline/fine-tuned CER, WER, exact match, statuses and shared inventory/eligible counts. Expandable details include identity, coverage, failures and latency. |
| `summary.csv` | Aggregate rows per model, variant, split, input set and field. Error/accuracy values are fractions, not percentages; nulls export as empty cells. |
| `report.json` | Canonical result including policy, manifest/config/run-input hashes, recorded model/processor identities, edit counts and per-crop scored outcomes. |

All train/valid/test, annotation/prediction and three text classes are represented;
panel-context rows explicitly say **Not applicable**. Missing populations say
**No samples** within a run scope. Available populations without eligible text say
**Review pending**. Unrun or unavailable variants have null metrics, never zeros.
An eligible subset can be scored while other rows remain pending; the denominator
is always shown and should not be presented as full-inventory accuracy.

Primary metrics preserve case, punctuation and real line breaks. Prediction text
uses NFC, one word space, trimmed per-line padding and removal of empty layout
lines; raw saved predictions remain unchanged. WER splits on Unicode whitespace.
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
protection. These checks validate software behaviour, not real OCR performance.
