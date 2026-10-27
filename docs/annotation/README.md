# EDS annotation with Autodistill

Code only: no model inference has been run and no annotations have been generated.
Use `python scripts/02_auto_annotate.py` from the repository root.
The implementation lives alongside the other preparation modules in
`src/data_preparation/annotation.py` and `annotation_cli.py`. The single launcher
is `scripts/02_auto_annotate.py`. Install dependencies from the root `requirements.txt`.
`experiments/eds_autodistill/` is only for local environment, cache and draft
outputs; it contains no separate annotation code or dependency list.

The [annotation guide](guide.md) defines target scope, the four classes and review rules.
The local Grounding DINO adapter implements Autodistill's `DetectionBaseModel`.
It uses positive visual captions and the guide's four canonical class IDs.
The guide's Gemini-specific job settings do not configure this backend.

Default inputs: `data/raw/2026-10-24/splits/{train,valid,test}`.
Outputs after an explicit run:

```text
experiments/eds_autodistill/outputs/trial-001/
  data/labelled/2026-10-24/
    train/   # Plain images + _annotations.coco.json
    val/     # Same split as input valid/
    test/
  overlays/  # Raw proposals and filtered draft boxes
  review_queue.json
  raw_predictions.json
  run_manifest.json
  automatic_review.json  # Geometry/consistency flags; never automatic acceptance
```

Images retain their source resolution; COCO boxes use `[x, y, width, height]`.
Nested panel/content boxes are supported. No fixed vertical-layout rules are used.
All generated labels require review for small side displays, rear-display exclusion,
text-line grouping, destination symbols, and route/destination meaning. A zero-box
prediction is not automatically an approved Null image. Explicitly declared negatives
receive an image record with zero annotation records.

The exporter rejects writes outside this experiment and never overwrites a run.
Existing labels and split assignments are not modified. The exporter checks that
source files and the annotation guide remain unchanged during inference.
No notebook is required or accessed.
COCO category 0 is a foreground panel class here; training frameworks reserving 0
for background require a separate training-time mapping.

```powershell
# Plan only; no model download or inference.
python scripts/02_auto_annotate.py

# When ready: 3 images per split. Use a new output name for each run.
python scripts/02_auto_annotate.py --run --limit 3
```

References: [Autodistill](https://github.com/autodistill/autodistill),
[Grounding DINO in Transformers](https://huggingface.co/docs/transformers/model_doc/grounding-dino).

## Accepting a draft

New runs automatically write `automatic_review.json`. These checks flag invalid
boxes, missing enclosing panels, possible duplicates, large panel candidates,
low confidence, overlapping route/destination boxes, and empty predictions.
They do not visually classify front/side versus rear signs or confirm true
negatives. Every image starts unreviewed, even when the checks find no issues.

### Local box editor (no additional dependencies)

Add `--review` to `02_auto_annotate.py --run` to open the editor immediately after
inference. For an existing run, use:

```powershell
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --serve
```

The command opens a local browser page; if it does not open automatically, use
the URL printed in the terminal. Keep the terminal running while reviewing.
The editor displays the original image with explicit coloured bounding boxes
and class names. Drag on the image to add a box; edit the class and x/y/width/height
in the table, or delete an incorrect box. Review all visible front/side panels,
including small side displays, and the meaning of route versus destination text.

- **Accept positive:** saves the current boxes and explicitly accepts this image.
- **Confirm negative:** requires zero boxes and your confirmation that there is
  no eligible front/side EDS anywhere in the image. An empty detection alone
  does not establish this.
- **Save as unreviewed:** saves corrections/notes without accepting the image.
- **Next unreviewed:** advances through images that still need a decision.
- **Export reviewed dataset:** after every image has a decision, writes plain
  images and corrected COCO JSON to a new version under `data/labelled/`.
  The default destination uses the run's batch date. Existing exports cannot
  be overwritten; select a new version name when necessary.

Progress lives in `review_decisions.json` beside the report. Reopening the same
run restores it. Decisions are bound to hashes of the draft COCO and images;
editing those source files invalidates the saved review. The original draft
COCO and images remain unchanged. Exported annotations carry accepted status,
and a checksum manifest records the review decisions and files. Run
`00_audit_dataset.py --input <reviewed-export>` before augmentation; visual
acceptance does not override leakage or other readiness checks.

To generate the automatic report only, omit `--serve`. To export saved decisions
without opening the editor:

```powershell
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --export "data/labelled/2026-10-31"
```

Skip that export command if you already exported through the editor. Then audit
the accepted dataset and continue to augmentation only if the audit reports
`automated_checks_passed: true`:

```powershell
python scripts/00_audit_dataset.py --input "data/labelled/2026-10-31" --report ".runtime/labelled-audit-2026-10-31.json"
# Run only after the audit passes.
python scripts/03_augment_dataset.py --cutoff 2026-10-31 --input "data/labelled/2026-10-31" --output "data/training/2026-10-31" --write
```

The final dataset is `data/training/2026-10-31/{train,valid,test}/`, with plain
images and `_annotations.coco.json` in each split. Use the exact reviewed version
path if you chose a different export name. There is no need to submit overlay
paths as proof of review; the editor's saved decisions record acceptance.

### Existing overlay images and manual editing

The experiment's `overlays/{train,val,test}/` folders already contain images with
explicit boxes and class labels: `__raw.png` shows detector proposals and
`__draft.png` shows filtered draft boxes. These are inspection copies, not
training images. They show the initial predictions; editor corrections are
shown in the editor and exported COCO, not repainted into these static overlays.
Plain images and COCO live in the run's `data/labelled/<batch>/` directory.

Review every image, including zero-box predictions, against the annotation guide.
Correct panel/content boxes and mark each reviewed image's COCO `review_status`
as `accepted`. Explicitly declared negatives have no annotation records; unknown
empty predictions require review first. If using an external editor instead of
the local editor above, manually copy the reviewed plain images and COCO JSON to
`data/labelled/<cutoff>/{train,val,test}` without changing membership.
The augmentation CLI rejects images explicitly marked as unreviewed drafts.
The canonical draft IDs 0–3 differ from some older exports; preserve one verified
mapping across all splits. Never merge IDs based only on list position.
