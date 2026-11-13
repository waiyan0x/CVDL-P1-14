# Three-model pre-training baseline deliverable

Status, 13 November 2026: implementation and diagnostic inference are complete
for the current validation crop inventory. **Numerical text accuracy is pending
human review.** This is a project deliverable, not a claim about rubric compliance.

## Paired baseline audit — 13 November 2026

The [refreshed baseline tables](../evaluation/ocr_baselines/three-model-audit-20261113/tables/baseline_tables.html)
use the latest validation working snapshot and its user-approved challenge
exclusions. All accuracy cells remain pending (zero eligible rows).
The [paired audit](../evaluation/ocr_baselines/three-model-audit-20261113/audit.json)
checks all three runs against the 271-ID frozen inventory: source/crop hashes,
field/population, dimensions, quadrilaterals, line regions, line output order and
sizes, explicit unresolved-layout failures, and saved summary counts.
Shared crop-processing and layout source snapshots are byte-identical across
the three runs. This verifies saved input/geometry evidence; historical in-memory
line pixel buffers were not independently hashed.

`paired_status.csv` keeps all 271 rows, including failures and empty successes.
`failures.jsonl` preserves all 61 model-failure records (20 shared layout failures
per engine, plus TrOCR P051). `failed_engine_history.json` retains TrOCR's failed
generation trace, including P051 reaching its 64-token cap without EOS; this
trace is diagnostic evidence, not a successful OCR hypothesis. Original run files
remain unchanged and their report/prediction hashes are recorded in the audit.
An empty successful output means empty or whitespace-only: Paddle A108 contains
a literal space. Saved raw text is preserved.

Reproduce into a new directory without running OCR or accessing test images:

```sh
.venv/bin/python scripts/audit_ocr_baseline_runs.py \
  --review evaluation/ocr_review/human-verification-20261113/validation.source.csv \
  --config evaluation/ocr_baselines/three-model-audit-20261113/tables/comparison.json \
  --line-layout evaluation/ocr_layouts/v4-lines-v1/manifest.json \
  --output /path/to/new-paired-audit
```

The saved configuration points to this machine's original run directories;
update those paths when moving the saved evidence to another machine. Model-native
recognition preprocessing remains distinct. This audit selects no model winner,
does no fine-tuning or matching, and provides no CPU-versus-MPS latency ranking.

## Comparison contract

| Item | Decision or evidence |
| --- | --- |
| Models | Public pretrained EasyOCR English generation-2, `microsoft/trocr-base-printed`, and `PaddlePaddle/en_PP-OCRv5_mobile_rec`. No fine-tuned weights are used. |
| Scope | The supplied v4 validation package: 157 annotation crops and 114 detector-predicted crops. It is not automatically equivalent to the earlier Roboflow v2 or 142-image held-out collection. |
| Fields | `front_eds_num`, `front_eds_destination`, `front_eds_route`; keep annotation/prediction populations separate. |
| Inputs | Same 271 IDs, crop hashes and fixed line geometry for all three models. Each model retains its native recognition resize/normalization. |
| Layout | `v4-lines-v1`, hash `218b06343d85a241e8eb2eb08076736c5b9afe5e52b17ee5e22263b9c73907fd`. AI-reviewed diagnostic geometry; 251 accepted and 20 unresolved. Human attestation remains pending. |
| Accuracy | Reviewed full, present, single-field text only, with field/group/correspondence gates. Primary raw CER/WER/exact match, before reference matching. Current eligible count is zero. |
| Timing | EasyOCR/TrOCR saved MPS runs and a separate Paddle CPU run. Show device and boundaries; no direct CPU-versus-MPS latency ranking. |
| Training/test | No training or reserved-test evaluation in this preparation. Fine-tuned columns remain unrun. |

Observed inference coverage:

| Model | Attempted crops | Completed | Failed | Empty successful outputs |
| --- | ---: | ---: | ---: | ---: |
| EasyOCR | 271 | 251 | 20 | 3 |
| Public TrOCR | 271 | 250 | 21 | 0 |
| PaddleOCR, CPU | 271 | 251 | 20 | 3 |

These are execution counts, **not recognition accuracy**. The 20 shared unresolved
layouts remain explicit failures. Each eligible failed crop will later count as
an empty hypothesis. TrOCR's additional saved failure remains in its run evidence.

Evidence: local `report.json` and `predictions.jsonl` under
`evaluation/ocr_runs/easyocr-v4-mps-fixed-lines-20261112-01/`,
`evaluation/ocr_runs/trocr-base-printed-v4-mps-fixed-lines-20261112-01/`, and
`.cache/ocr-baselines/paddle-en-v5-cpu-20261113-01/`. Current model-cache files
were checked against the run hashes before assembling the deliverable. Fifteen
weight/config/provenance artifacts matched during the earlier assembly. The
original inference/model caches remain local; the refreshed audit exports above
are available under `evaluation/ocr_baselines/`.

## Paddle preparation

Observed local environment: separate Python 3.12 environment with PaddlePaddle
3.2.2, PaddleOCR 3.3.2 and PaddleX 3.3.13. The main application environment is
unchanged. The official inference artifact was pinned to upstream revision
`267c36e24c331595590fe7bd72bde2436fd286f2`; its graph, weights and configuration
have local SHA-256 records. Setup downloads are separate from inference.

The [official recognition guide](https://www.paddleocr.ai/v3.3.0/en/version3.x/module_usage/text_recognition.html)
describes the recognition-only interface; the
[official model repository](https://huggingface.co/PaddlePaddle/en_PP-OCRv5_mobile_rec/tree/267c36e24c331595590fe7bd72bde2436fd286f2)
identifies the model artifact. Published model benchmark numbers are not copied
into these EDS tables.

```sh
python3.12 -m venv .cache/paddle-baseline-env
.cache/paddle-baseline-env/bin/python -m pip install paddlepaddle==3.2.2 paddleocr==3.3.2 paddlex==3.3.13
.cache/paddle-baseline-env/bin/python scripts/fetch_paddle_baseline.py \
  --revision 267c36e24c331595590fe7bd72bde2436fd286f2 \
  --output /path/to/new-local-model-directory
.cache/paddle-baseline-env/bin/python scripts/run_paddle_crops.py \
  --workspace evaluation/ocr_annotations/v4-reviewed-01 \
  --model-dir /path/to/new-local-model-directory \
  --line-layout evaluation/ocr_layouts/v4-lines-v1/manifest.json \
  --output /path/to/new-paddle-run
```

All model/output directories must be new. The actual environment package list,
commands, source snapshots, warmups and run hashes are retained locally. This
native CPU runner has no detector, reference matcher, training or test discovery.
Paddle confidence is not a calibrated probability or comparable model accuracy.

## Assemble the deliverable

Use the configuration format from [OCR_CROP_SCORING.md](OCR_CROP_SCORING.md),
pointing the three baseline entries to compatible saved run directories.
Keep `finetuned` null. Then:

```sh
.venv/bin/python scripts/prepare_ocr_baseline_deliverable.py \
  --review /path/to/annotation_ai.review.csv \
  --review /path/to/prediction_ai.review.csv \
  --config /path/to/comparison.json \
  --line-layout evaluation/ocr_layouts/v4-lines-v1/manifest.json \
  --source-root evaluation/ocr_annotations/v4-reviewed-01/source \
  --output /path/to/new-deliverable
```

The command verifies validation-only scope, actual crop hashes/dimensions, layout
checksum, saved-run population/geometry and model/source-integrity declarations.
The scorer separately checks all prediction-to-review identities/hashes. The
command writes three concise baseline tables, the full comparison tables,
canonical JSON, aggregate CSV, a crop-size/coverage audit, crop inventory, blank
human decision forms and source-group/burst-pair review worksheets. Existing
outputs are refused. No source file is edited, and test images are not opened.

Local assembled deliverable:
`.cache/ocr-baselines/pretraining-20261113-01/deliverable-02/`.
Read `baseline_tables.html` first, then `audit.json`. Full comparison tables retain
the unrun fine-tuned columns for future use.

## Remaining manual decisions

Human text/field decisions use the importer in
[OCR_REVIEW_DECISIONS.md](OCR_REVIEW_DECISIONS.md). The generated decision forms
are hash-bound to their source exports. Inspect visible crop text before accepting
or correcting proposals. Keep all uncertain cases unresolved.

Source groups are proposed from identical parent-image hashes. Temporal pairs
are proposed from filename timestamps within five seconds. Neither establishes
the same bus, capture timezone, original-versus-augmentation lineage or split
independence. Review full source context before assigning final groups.
The group worksheet is a proposal sheet, not an accepted import format; human
grouping and correspondence still require a separately validated metadata import.

View and lighting remain unknown where absent from the handoff. The inventory
records existing issue codes as review proposals; it does not claim a new visual
quality review. Mixed-field crops stay outside primary scoring. Operational
messages and ambiguous route/destination roles need a documented human field
decision; wording alone must not relabel a supplied class. Existing punctuation,
line-break and unknown-character rules remain in force.

Until those decisions are supplied, the three tables are **diagnostic baseline
tables with pending accuracy**, not a completed accuracy comparison or a model
selection result. Once eligible labels are frozen, rerun the scorer against these
same compatible predictions; no OCR rerun is required merely because review
metadata changed.
