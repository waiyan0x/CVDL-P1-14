# EasyOCR recognition-only crop baseline

**Project decision:** collect raw pretrained recognition output before training,
reference matching or scoring. This is a crop diagnostic, not an end-to-end
application benchmark or an assessment requirement.

## Reproduce

Run from the repository root with the installed project environment and cached
English weights. Use a new output directory on every invocation:

```sh
.venv/bin/python -u scripts/run_easyocr_crops.py \
  --device mps --warmup 3 --seed 0 \
  --output evaluation/ocr_runs/easyocr-v4-mps-baseline-03
```

The runner refuses an existing output, unavailable requested GPU or mismatched
recognizer parameter device. It loads cached pretrained `english_g2.pth` with
downloads disabled. CRAFT is disabled; the application OCR adapters, detector,
matching and training paths are not invoked or modified.

Input identities come from the A/P submission templates under
`evaluation/ocr_annotations/v4-reviewed-01/human_review/`. Only IDs, field labels,
source/crop hashes and dimensions are selected. Submitted transcription,
legibility and route-reference data are never used to generate predictions or
choose line boundaries. The existing 157 A and 114 P crops are reported separately.

## Shared line-region method

The frozen, visually reviewed alternative is now documented in
[OCR_LINE_LAYOUT.md](OCR_LINE_LAYOUT.md). Pass `--line-layout` explicitly to use
it; the automatic method and historical runs described below remain unchanged.
Fixed reviewed layout supplies additional upstream information and is reported
as a separate recognition diagnostic, not automatic segmentation performance.

`backend/app/evaluation/ocr_crop_baseline.py::segment_lines` supplies the same
field-independent, deterministic image-only method for both sets. Its versioned
parameters are recorded in each run's `report.json`:

1. Decode RGB and convert to grayscale. Use Otsu thresholding and border-median
   polarity. When sufficient warm/green chromatic support is present, use it to
   suppress gray occluders. White or dark text falls back to grayscale support.
2. Project foreground pixels onto image rows; find active row bands. Bridge short
   gaps, with an adaptive allowance for periodic gaps between LED dot rows.
3. Partition the full crop width at midpoints between retained row bands. Every
   original image row is assigned to a region; there is no external resize,
   padding, spelling correction or character allowlist.
4. Recognize each proposed line independently, top to bottom. Preserve returned
   strings and insert actual newlines between line results. EasyOCR applies its
   own unchanged internal recognizer resize and normalization. Automatic contrast
   retries are disabled (`contrast_ths=0.0`).

**Limit:** row projection is not a verified line detector. Dot texture, glare,
skew, clipping and touching/overlapping lines can yield wrong regions. All region
records have `needs_review=true`; a single band is explicitly labelled
`single_band_unverified`, never confirmed as one true line. No foreground or
excessively fragmented layouts produce a recorded error instead of an unreported
full-crop fallback. Visual QA is mandatory before multiline accuracy scoring.

The first exploratory run exposed LED dot rows mistaken for separate text lines.
Its v1 code/output remain preserved in `easyocr-v4-mps-baseline-01`. The v2
regression fixes were run under a new name, `easyocr-v4-mps-baseline-02`. **V2
still has missed line separations**, including visually inspected A002/A003 and
P002/P003, where clipping/skew makes row support overlap. These predictions are
raw diagnostic evidence, not validated multiline transcriptions. Neither run is
ranked by accuracy; region review remains outstanding.

## Outputs and timing

- `predictions.csv`: all crop IDs/hashes, raw text, aggregate confidence, number
  of proposed lines, preprocessing/recognition/total times, status and errors.
- `predictions.jsonl`: adds actual line boxes, segmentation uncertainty and every
  returned string/score. Failed multiline crops retain partial output but remain
  errors with null aggregate confidence.
- `segmentation_previews/`: native-size visual overlays; image writes occur
  outside the measured interval. Original crops remain unchanged.
- `report.json` and `README.md`: per-field and per-set completion/error/empty
  counts and median/p95 timings, settings and limitations.
- `environment.json`, `environment_requirements.txt`, `command.json` and source
  snapshots: versions, machine/chip/memory, actual parameter device, command and
  exact runner/core code used. `warmup.json` records excluded warmup attempts.
- `input_hashes.json`: hashes of all workspace files, including source crops and
  transcriptions. Workspace and cached-weight hashes are checked again at the end.

Warmup is three repetitions of the first annotation crop for each field. Every
crop then receives one timed pass in fixed A-then-P order. This is not a repeated
latency experiment on each input; unseen shapes can still incur first-use costs.
GPU work is synchronized before/after recognition calls. Preprocessing measures
read/hash/decode/grayscale/segmentation. Recognition includes internal resize,
transfer, forward and decoding. Crop total includes these plus result assembly.
Model initialization, warmups, integrity snapshots, previews and output writes
are excluded. Median/p95 use linear interpolation across successful heterogeneous
crops; failed attempts remain counted and retain their individual times.

The aggregate OCR score is a character-count-weighted mean of EasyOCR's returned
region confidences, excluding inserted newline characters. Native scores are also
retained. Empty output has null confidence. Scores are not calibrated correctness
probabilities and must not be compared directly with other engines' confidence.

## Observed run — Apple M1, `mps:0`

`easyocr-v4-mps-baseline-02` completed all 271 crop attempts with zero execution
errors. A has four empty outputs; P has none. Recognition-only median/p95 are
11.75/54.13 ms for A and 10.38/21.77 ms for P. The report contains the six field
breakdowns and separate preprocessing/total timings. This does not establish
text correctness, segmentation correctness, sustained FPS or pipeline latency.

Ten focused tests cover line partitions, polarity, LED dot-row gaps, occluders,
raw-string preservation, source integrity, failed-line handling and summary
denominators. Run them with:

```sh
.venv/bin/python -m unittest discover -s tests/evaluation -p test_ocr_crop_baseline.py -v
```

Ground-truth resolution, group independence and predicted-crop correspondence
are not asserted. No CER, accuracy or similarity score is calculated. Reference
matching, post-processing, pretrained weights and training remain untouched.
