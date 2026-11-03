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
`input_width`, `input_height`, `warmup_runs`, and `timed_runs` are integers.
`device` is `cuda` or `mps`; `gpu_model` is the returned model name and
`timing_method` identifies CUDA events versus synchronized wall clock.
Repeated frame timing on each field row must be described as shared frame-level
timing, not summed as separate field costs.
