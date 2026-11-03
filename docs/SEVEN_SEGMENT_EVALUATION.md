# Seven-segment OCR evaluation foundation

This is a standalone protocol. The current bus EDS dataset has no seven-segment
ground truth, so the rules below are proposals until the team confirms the display
format and supplies reviewed labels.

## Reading and normalization policy

One crop represents **one reading**. Valid normalized syntax is an optional `+`
or `-`, digits, and at most one decimal point. A leading-decimal form such as
`.5` becomes `0.5`. Normalize Unicode width forms and the Unicode minus sign,
remove whitespace inside the single reading (including spaces between digits), and remove integer leading zeros
while retaining one zero. Preserve explicit `+`/`-`, the decimal point, and every
fractional digit: `12`, `12.0`, and `12.00` remain distinct. Do not map visually
ambiguous glyphs such as `O` to `0` automatically. Two readings must be split
into separate field crops before scoring; whitespace alone cannot distinguish them.

| Truth | OCR output | Strict match | Normalized match | Reason |
| --- | --- | --- | --- | --- |
| `0012` | `12` | No | Yes | Integer leading zeros are ignored. |
| `− 00.50` | `-0.50` | No | Yes | Minus glyph, spacing, and integer zeros normalize. |
| `+07.0` | `7.0` | No | No | Explicit positive sign is retained. |

Strict comparison uses the reviewed raw strings, character for character.
Normalized comparison uses `normalize_reading` on both. CER is Levenshtein
substitutions + insertions + deletions divided by truth length; report raw and
normalized CER separately. A missing OCR output scores as empty; an absent or
unreadable truth uses `null` and is excluded under a declared policy.

## Split plan and leakage gate

Start with **70% train, 15% validation, 15% test by physical display groups**, not
by individual frames. Keep every recording and augmentation derived from a display
in that display's split. If different physical displays share a recording, assign
the entire recording to one split. Stratify groups to preserve sign, decimal,
digit length, display type, lighting and viewpoint, then report actual counts;
do not force exact percentages at the cost of leakage. Freeze test before any
model or normalization tuning. Use validation for checkpoint and threshold choice.

Every sample record needs a stable `display_group_id`, `recording_id`, and
`frame_index`. Run `check_split_leakage` before training and before reporting:
it flags a display or recording reused across splits and frames within the declared
adjacency gap crossing splits. Also audit crop hashes, source-image hashes,
near-duplicates, and augmentation parent IDs; the function cannot infer identity
from pixels or recover IDs that were never recorded. Resolve all flagged groups
in the manifest before measuring validation or test accuracy.

### Build the reviewed crop inventory

Use the header in `evaluation/seven_segment_input.schema.csv` and add one row per
single-reading image. `crop_path` is relative to the inventory CSV (or absolute);
`sample_id`, `display_group_id`, and `recording_id` are stable, nonempty IDs.
`frame_index` is a nonnegative source-frame number. Use the same
`display_group_id` for the same physical display across recordings. Set
`augmented_from` to the source `sample_id` for a derived crop, or leave it blank.

`label_status` is `readable`, `unreadable`, `blank`, or `error`. Only a readable
row has `truth_raw`; transcribe the visible characters exactly. Every row needs
a `primary_reviewer`. Validation and test rows need a different
`secondary_reviewer`, including unreadable/blank/error cases. The current
normalizer accepts digits, optional leading sign and one decimal point; if the
real displays include units or other symbols, revise the agreed alphabet before
creating final truth. Do not populate `truth_raw` from a model prediction.

From the repository root, create an **audited draft** manifest:

```sh
python3 scripts/seven_segment_manifest.py \
  --inventory /absolute/path/to/crops/inventory.csv \
  --dataset-id seven-segment-readings --version v1 \
  --output evaluation/seven_segment_manifest.v1.json
```

The command exits with code 2 when any evaluation gate fails and prints the
issues. Its manifest records crop hashes, dimensions, format, group-safe draft
splits and split feature counts. Review the split balance before freezing it;
the percentages are approximate because whole displays/recordings stay together.
The builder checks exact crop hashes and declared identities. The team must also
review near-duplicate imagery and source provenance, which metadata alone cannot
prove. Keep the reviewed test split untouched after approval.

### Run the first baselines

After the review gate passes, run one engine at a time on the **same** reviewed
validation crops. The template method needs PNG glyph exemplars cut from train
crops only, plus `templates.json` in the template directory:

```json
[
  {"glyph": "1", "file": "1.png", "source_sample_id": "train-sample-001"},
  {"glyph": ".", "file": "dot.png", "source_sample_id": "train-sample-002"}
]
```

`source_sample_id` must identify a train row in the manifest. Add templates for
every symbol that the confirmed display alphabet uses. The simple projection
splitter is a reference method and may fail on tightly touching glyphs or glare;
record its failures rather than manually correcting predictions.

```sh
python3 scripts/seven_segment_baseline.py --manifest evaluation/seven_segment_manifest.v1.json \
  --engine template --templates /absolute/path/to/train-glyph-templates \
  --split val --device cpu --run-id template-v1 \
  --output evaluation/seven_segment_template_val.csv
```

Replace `template` with `tesseract` or `easyocr` and use a distinct run ID/output
file. EasyOCR accepts `--device cuda` on a compatible Colab GPU or `--device mps`
on a supported Mac. Tesseract and the template reference use `--device cpu`.
The runner refuses an unreviewed manifest, changed crop bytes, or a template
whose source sample is outside the train split. Its CSV stores raw and normalized
scores, engine-specific confidence, and timing per crop. After selecting settings
on validation, run the unchanged configuration once on `--split test`.

## GPU timing protocol

`time_gpu_inference` accepts an **already loaded** inference callable and runs warm-up
passes outside the timed sample. CUDA uses synchronized GPU events; Apple MPS uses
synchronized wall-clock timing and reads the model from macOS `system_profiler`.
The returned timing method, GPU model, warm-up and timed counts, each sample,
median, and interpolated p95 latency are recorded. Declare batch size, input
shape, precision, and whether host-to-device transfer or preprocessing is inside
the callable. Run on an idle device. This is inference latency, not end-to-end
camera/display latency or sustained throughput. CUDA event timing and MPS wall
time have different boundaries and should not be ranked as if identical.

## Results CSV schema

The header-only schema is `evaluation/seven_segment_results.schema.csv`.
Write **one row per scored field per source frame**. Empty numeric cells mean
not measured, never zero. Required identity/provenance columns are `run_id`,
`dataset_version`, `split`, `display_group_id`, `recording_id`, `frame_index`,
`field_name`, `model_id`, `checkpoint_sha256`, `crop_source`, and `crop_sha256`.
`truth_raw`, `prediction_raw`, `truth_normalized`, and `prediction_normalized`
are UTF-8 strings; `strict_match` and `normalized_match` are `true`/`false`;
`cer`, `normalized_cer`, and `latency_ms_*` are nonnegative decimal numbers.
`ocr_confidence` retains an engine-specific score with its `confidence_method`;
do not rank confidence values across engines. `checkpoint_sha256` is blank only
when the external engine's model artifact cannot yet be identified, and this
must be disclosed with the result.
`input_width`, `input_height`, `warmup_runs`, and `timed_runs` are integers.
`device` is `cuda` or `mps`; `gpu_model` is the returned model name and
`timing_method` identifies CUDA events versus synchronized wall clock.
Repeated frame timing on each field row must be described as shared frame-level
timing, not summed as separate field costs.
