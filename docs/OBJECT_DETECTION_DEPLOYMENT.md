# Selected object detector deployment

The validation-selected detector is **YOLO11s baseline-01**, checkpoint SHA-256
`01d832cb6eda71dcf4a88e6ebbafc080f9dc299be8161c76ab15c75f7c60c2e3`.
Selection used validation mAP50:95 before the held-out test.

## Install the local checkpoint

The 19 MB checkpoint is a generated runtime artifact and is intentionally not
committed to Git. Install and verify the saved training output from the repository root:

```powershell
venv\detector\Scripts\python.exe scripts\install_selected_detector.py
venv\detector\Scripts\python.exe scripts\install_selected_detector.py --verify-only
```

The app reads `evaluation/object_detection/bf938f526d2c/runs/baseline-01/checkpoints/yolo11s-best.pt`.
If the runtime training folder is unavailable, supply `--source PATH`. Installation
refuses a checkpoint whose SHA-256 differs from the selected checkpoint. The full
machine-readable contract is in the adjacent deployment `detector_config.json`.

## Inference contract

| Model ID | Model label | Stable API label | OCR/application use |
|---:|---|---|---|
| 0 | `front_eds` | `eds` | Owns component fields and supplies the whole-panel crop. |
| 1 | `front_eds_num` | `bus_number` | OCR service identifier and exact reference lookup. |
| 2 | `front_eds_route` | `route` | OCR intermediate road/landmark text; displayed but not treated as a verified endpoint. |
| 3 | `front_eds_destination` | `destination` | OCR destination and reference endpoint comparison. |

The app rejects a checkpoint whose embedded class names do not exactly match this
order. Inference uses 640-pixel input, confidence `0.20`, NMS IoU `0.70`, all four
classes and at most 100 detections. Rear-facing EDS and unrelated text are excluded.

## Evidence and limitations

- Multiple panels and fields are associated by containment; fields are not paired
  across known panel owners.
- Detection, OCR and matching confidence remain separate quantities.
- Route OCR is observational; current references do not verify road-name coverage.
- OCR accuracy remains unmeasured because reviewed text transcriptions are absent.
- Browser camera and uploaded-video controls have automated lifecycle/decode tests.
  Real camera hardware, moving buses, glare and sustained field latency still require
  a recorded field test; simulated tests must not be reported as that evidence.
