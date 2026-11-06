# Object detection handoff

The latest result is the [reviewed Roboflow v4 run](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md),
with three trained models, three validation reports and one final YOLO11s test.
The new YOLO11s checkpoint and dataset payload are local Git-ignored artifacts.
The [v4 validation crop handoff](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/OCR_HANDOFF.md)
is committed as individual annotation and detector-predicted crop files.
The [validation NMS/failure review](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/validation_review/REVIEW.md)
and [tested v4 detector configuration](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/detector_config.json)
are also saved. The v4 checkpoint is now installed as the application default
and passed a local detection/crop smoke test at confidence `0.50`, NMS `0.70`.
The older `baseline-01` result and weights remain preserved as historical
documentation. The sections below describe that earlier baseline separately.

The earlier three-model benchmark and its application integration are recorded
as `baseline-01`. Keep both completed held-out tests closed for tuning.

## Completed baseline

- Dataset fingerprint: `bf938f526d2c01f1960b9af018f1fd1dc78a431e725037c84d1707dfcc5b826c`
- Models: YOLO11n, YOLO11s and DETR-ResNet50
- Classes: panel, service number, route/landmark and destination
- Selected model: YOLO11s, chosen using validation mAP50:95 (`0.4274`)
- Deployment settings: 640-pixel input, confidence `0.20`, NMS IoU `0.70`
- Held-out test, per-class metrics, latency, negative-image false positives and
  qualitative failure analysis are saved under
  `evaluation/object_detection/bf938f526d2c/runs/baseline-01/`.
- The selected checkpoint contract and SHA-256 are saved in
  `deployment/detector_config.json`. The generated weight itself is intentionally
  ignored by Git and must be retained or transferred separately.

The authoritative numerical summary is [the baseline results](../evaluation/object_detection/bf938f526d2c/runs/baseline-01/RESULTS.md).

## Pending Jy/Brendan data decisions (on hold)

Brendan and Jy still need to complete the prepared [data-review packet](../evaluation/object_detection/bf938f526d2c/runs/baseline-01/data_review/REVIEW.md):

1. Confirm the four class definitions and mapping.
2. Decide the 15 semantic candidates.
3. Confirm all 22 zero-box images are genuine negatives.
4. Resolve the 12 timestamp-derived groups that cross splits using source/capture
   records.
5. Record source ownership and usage permission.

No labels or split assignments were changed by the automated audit. If the human
review changes either, publish a new manifest-backed dataset version and use a new
run ID to retrain all three candidates. Preserve `baseline-01` unchanged as
historical evidence. If the review makes no changes, retraining is unnecessary.

The v4 validation-only NMS IoU `0.50` versus `0.70` comparison is now recorded
in the [review](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/validation_review/REVIEW.md).
NMS `0.50` had a small validation advantage, but the existing final test belongs
to the originally selected `0.70` setting. Keep that tested configuration fixed.
If a future revision selects `0.50`, use a new independent held-out set.

## Application and OCR continuation for Cody

Cody should start with the [OCR handoff README](OCR_CODY_HANDOFF.md) for the
committed crop package, reviewed-text workflow and three-engine comparison steps.

The committed detector integration covers model loading, stable four-class API
labels, multiple-display association, uploaded-video decoding and a simulated
camera response path. Installation and the runtime contract are documented in
[OBJECT_DETECTION_DEPLOYMENT.md](OBJECT_DETECTION_DEPLOYMENT.md).

The EasyOCR continuation includes
real EasyOCR asset installation/verification, raw OCR timing observations and
graceful behaviour when the route-reference CSV is missing. It does **not** prove
OCR accuracy because no reviewed transcription manifest is available. Tesseract,
fine-tuned TrOCR, a physical camera and moving-bus field testing remain pending.
For the new v4 detector, Cody can pull the crop folder and use its manifest to
review actual predicted text regions. Its transcription template is blank;
reviewed text must be entered before measuring OCR accuracy. A separate local
ZIP is available for direct transfer if preferred.

Do not add the loose root-level `yolo11n.pt` file to a commit. Model weights and
local caches are generated artifacts, not source files.

## Safe continuation order

1. Read the baseline results, qualitative review, data-review packet and deployment
   contract.
2. Inspect `git status` and the latest commits before continuing the OCR work.
3. Obtain reviewed OCR transcriptions before reporting CER or exact-text accuracy.
4. Run OCR comparisons on identical detector crops and report raw OCR separately
   from reference matching.
5. Perform real camera and moving-bus field tests before claiming live-system
   performance.
6. Start a new detector run only if the reviewed dataset or experiment question
   changes; never overwrite `baseline-01`.

## Local verification commands

Run from the repository root in PowerShell:

```powershell
# Confirm that the v4 default checkpoint is present and matches the saved hash.
venv\detector\Scripts\python.exe scripts\install_selected_detector.py --verify-only

# Review the current working state.
git status --short
git diff --check

# Run focused tests after any application/OCR changes.
venv\detector\Scripts\python.exe -m pytest tests\backend tests\test_matching.py -q
```

The simulated camera and still-image video fixtures validate control flow only;
they must not be described as real field evidence.
