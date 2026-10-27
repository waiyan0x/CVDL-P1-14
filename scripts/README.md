# Standalone preparation scripts

Run commands from the repository root, which contains `scripts/`, `src/` and
`requirements.txt`, after installing the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Scripts read files saved by the previous stage; no notebook is required. The
working order is **split -> annotate -> review/export -> audit -> augment**.
Despite its `00` prefix, the audit checks an already labelled dataset.

## New batch: complete command sequence

This example uses `data/raw/2026-10-31/`. Replace `2026-10-31` consistently to
process another batch. These separate paths preserve the existing `2026-10-24`
batch; they do not merge batches or check for duplicates between batches.

### 1. Prepare and split raw images

```powershell
python scripts/01_prepare_and_split.py --cutoff 2026-10-31 --raw "data/raw/2026-10-31" --output "data/raw/2026-10-31/splits" --write
```

The result contains `train/`, `valid/`, `test/` and a frozen split manifest.
Omit `--write` to preview. Skip this step if you already have the intended frozen
splits; never change split membership after annotation.

The explicit output is intentional: the split script otherwise defaults to
`<raw>/splits/torch-v1`, whereas annotation otherwise reads
`data/raw/<cutoff>/splits`. Pass the actual split output to annotation's `--input`.

### 2. Annotate all images and open review

```powershell
python scripts/02_auto_annotate.py --cutoff 2026-10-31 --input "data/raw/2026-10-31/splits" --output "experiments/eds_autodistill/outputs/2026-10-31-run-001" --limit 0 --run --review
```

`--limit 0` selects every image; the default selects only three per split.
`--run` performs inference and downloads model weights if needed. Without it,
the command only plans. `--review` opens the local editor after inference.
Use a new run directory under `experiments/eds_autodistill/outputs/` for each run;
existing annotation runs cannot be overwritten.

Generated files:

```text
experiments/eds_autodistill/outputs/2026-10-31-run-001/
  data/labelled/2026-10-31/{train,val,test}/  # Plain images + draft COCO JSON
  overlays/{train,val,test}/                # Images with boxes and class names
  automatic_review.json                    # Automatic geometry/consistency flags
  review_queue.json
  raw_predictions.json
  run_manifest.json
```

`__draft.png` overlays show filtered annotations; `__raw.png` shows the detector's
original proposals. Neither is a training image. Corrections made later appear
in the editor/exported JSON, not in these initial static overlays.

### 3. Review and export accepted labels

If the editor is not open, or to resume saved progress:

```powershell
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --serve
```

Use the printed local URL if the browser does not open automatically. Keep the
terminal running while using the editor.

1. Check the displayed image and explicit boxes/classes. Add/delete boxes or
   edit their coordinates/classes as needed.
2. Save **Accept positive** for a verified image containing front/side EDS.
   Save **Confirm negative** only after removing all boxes and confirming the
   entire image contains no eligible front/side EDS. Use **Save as unreviewed**
   if a decision is still pending.
3. Use **Next unreviewed** until every image has a positive/negative decision.
4. Click **Export reviewed dataset**, using `data/labelled/2026-10-31` as the
   destination. Alternatively, stop the editor with Ctrl+C and run:

```powershell
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --export "data/labelled/2026-10-31"
```

Choose one export method. Export requires every image to be explicitly accepted
and refuses an existing destination; choose a new version name for a new export.
It writes plain images, corrected accepted COCO JSON and a checksum manifest.
The draft images/JSON remain unchanged; no manual folder copy is required.

Your decisions and edits are saved in the run's `review_decisions.json` and
restored when you reopen it. Viewing overlay files alone does not record
acceptance, and you do not need to send their paths to anyone. Automatic checks
cannot confirm missed panels, front/side versus rear signs, or true negatives.
See the [detailed review instructions](../docs/annotation/README.md#local-box-editor-no-additional-dependencies).

### 4. Audit the reviewed dataset

```powershell
python scripts/00_audit_dataset.py --input "data/labelled/2026-10-31" --report ".runtime/labelled-audit-2026-10-31.json"
```

Proceed only when `automated_checks_passed` is `true`. The audit returns exit
code 1 on failed automated readiness checks. Resolve reported failures before
augmentation; visual acceptance does not override leakage or other checks.
The report must be outside the input/output datasets.

The audit has **no `--cutoff` argument**. Always specify `--input` for another
batch; its default remains `data/labelled/2026-10-24/`.

### 5. Build the final augmented training dataset

```powershell
python scripts/03_augment_dataset.py --cutoff 2026-10-31 --input "data/labelled/2026-10-31" --output "data/training/2026-10-31" --multiplier 3 --write
```

The final `data/training/2026-10-31/{train,valid,test}/` contains images and
`_annotations.coco.json` in each split. Multiplier 3 means one original plus two
variants per training image. The script transforms boxes along with images and
writes their final COCO annotations. Validation/test images and JSON are copied
unchanged. Omit `--write` to validate without generating the export.

New augmented exports must be under `data/training/`. Repeating an identical
frozen export verifies it; changed sources/settings require a new version path.
If you exported labels to a different version, use that exact `--input` here.
Models must explicitly load the new final dataset root; the default
`config.TRAINING_DATASET` remains `data/training/2026-10-24/`.

## Arguments and defaults

Use `python scripts/<script>.py --help` for full help.

| Script | Path arguments and defaults | Action and optional arguments |
| --- | --- | --- |
| `01_prepare_and_split.py` | `--raw`: `data/raw/<cutoff>`; `--output`: `<raw>/splits/torch-v1` | `--write` exports; `--cutoff` defaults to `2026-10-24`; `--seed` defaults to 42; optional `--groups` CSV with `source,group` columns (otherwise uses `data/groups/<cutoff>.csv` if present) |
| `02_auto_annotate.py` | `--input`: `data/raw/<cutoff>/splits`; `--output`: `experiments/eds_autodistill/outputs/trial-001` | `--run` infers; `--review` opens editor afterward; `--limit` defaults to 3 per split, 0 means all; `--cutoff` defaults to `2026-10-24`; optional `--negatives` JSON |
| `review_annotations.py` | Required `--run-dir`: annotation experiment run; `--export`: new reviewed version under `data/labelled/` | No action flag writes an automatic report; `--serve` opens editor; `--export` exports saved accepted decisions; optional `--port` (default 8765) |
| `00_audit_dataset.py` | `--input`: `data/labelled/2026-10-24`; optional `--report` | Audits without an action flag; optional exclusion-export mode requires `--write`, `--exclusions` and a separate `--output` |
| `03_augment_dataset.py` | `--input`: `data/labelled/<cutoff>`; `--output`: `data/training/<cutoff>` | `--write` exports; `--cutoff` defaults to `2026-10-24`; `--seed` defaults to 42; `--multiplier` defaults to 3 including originals |

`--cutoff` selects a batch name and default paths; it does not filter images by
capture date. Paths with spaces must be quoted. Annotation's `--negatives` accepts
a JSON list of reviewed input-relative paths such as `train/example.jpg`;
a missing prediction alone does not establish a negative.

## Existing accepted dataset

If the desired batch is already accepted, skip splitting, annotation and editor
export. For the current accepted source:

```powershell
python scripts/00_audit_dataset.py --input "data/labelled/2026-10-24" --report ".runtime/labelled-audit-2026-10-24.json"
# Continue only after the audit passes.
python scripts/03_augment_dataset.py --cutoff 2026-10-24 --write
```

The accepted source is already cleaned; the audit does not reapply historical
exclusions. For a future batch requiring reviewed training exclusions, audit's
`--write` requires explicit `--exclusions` and a separate `--output`. Past
exclusion evidence remains in the accepted source's `preparation_manifest.json`.

See the [phase context and augmentation recipe](../docs/data_preparation/README.md)
and [training handoff](../docs/data_preparation/TRAINING_READINESS.md).
