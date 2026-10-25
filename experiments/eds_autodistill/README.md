# EDS Autodistill experiment

Code only: no model inference has been run and no annotations have been generated.
Use `python scripts/02_auto_annotate.py` from the repository root.
The implementation lives in `src/data_preparation/annotation.py`; the local CLI
is a compatibility entry point. Install dependencies from the root requirements.txt.

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
experiments/eds_autodistill/.venv/Scripts/python.exe experiments/eds_autodistill/eds_autodistill.py

# When ready: 3 images per split. Use a new output name for each run.
experiments/eds_autodistill/.venv/Scripts/python.exe experiments/eds_autodistill/eds_autodistill.py --run --limit 3
```

References: [Autodistill](https://github.com/autodistill/autodistill),
[Grounding DINO in Transformers](https://huggingface.co/docs/transformers/model_doc/grounding-dino).

## Accepting a draft

Review every image, including zero-box predictions, against the annotation guide.
Correct panel/content boxes and mark each reviewed image's COCO `review_status`
as `accepted`. Explicitly declared negatives have no annotation records; unknown
empty predictions require review first. Then manually copy the plain images and
COCO JSON to `data/labelled/<cutoff>/{train,val,test}` without changing membership.
The augmentation CLI rejects images explicitly marked as unreviewed drafts.
The canonical draft IDs 0–3 differ from some older exports; preserve one verified
mapping across all splits. Never merge IDs based only on list position.
