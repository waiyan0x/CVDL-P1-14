# Selected object detector deployment

The application default is now **YOLO11s `v4-reviewed-01`**, checkpoint SHA-256
`97150601de39a999754015648cad2ef930842d52e8e37eb77d7576ffe2da33b5`.
It was selected using validation mAP50:95 before its held-out test. The old
`baseline-01` detector and its results remain preserved for documentation.

See [the Cody handoff](OBJECT_DETECTION_HANDOFF.md) for the current evidence and
remaining integration work.

## Current v4 detector verification

The newer [v4 detector configuration](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/detector_config.json)
records YOLO11s confidence `0.50`, NMS IoU `0.70` and the local checkpoint hash.
On a machine with the ignored v4 checkpoint and reviewed validation dataset,
install the checkpoint and run the application-path smoke test:

```powershell
venv\detector\Scripts\python.exe scripts\install_selected_detector.py
venv\detector\Scripts\python.exe scripts\install_selected_detector.py --verify-only
venv\detector\Scripts\python.exe scripts\verify_v4_detector_handoff.py
```

The app reads `evaluation/object_detection/01760a841333/runs/v4-reviewed-01/checkpoints/yolo11s-best.pt`.
The installer checks the saved SHA-256 before and after copying; use
`--source PATH` when transferring weights from another machine. Git contains
the configuration and results, not the checkpoint or full dataset. At startup,
the default detector rejects a checkpoint with the wrong SHA-256. The smoke
test checks that the app's default path and threshold match v4, then verifies
detection, grouping and nonempty crops on validation stills;
it does not measure OCR, moving-bus video or a physical camera. The human v4
annotation review is still on hold.
The browser uses a new v4 settings key so a saved baseline threshold does not
silently override the new `0.50` default. Users can still adjust detection
confidence in Advanced settings.

## Historical baseline checkpoint

The earlier baseline checkpoint, results and deployment configuration remain
under `evaluation/object_detection/bf938f526d2c/runs/baseline-01/`. It is not
the app default. To verify that its local file is still intact:

```powershell
venv\detector\Scripts\python.exe scripts\install_selected_detector.py --config evaluation\object_detection\bf938f526d2c\runs\baseline-01\deployment\detector_config.json --verify-only
```

The baseline SHA-256 is
`01d832cb6eda71dcf4a88e6ebbafc080f9dc299be8161c76ab15c75f7c60c2e3`.
Passing its config to the installer verifies or reinstalls that separate file;
it does not change the v4 application default.

## OCR assets

Install the EasyOCR English assets once before starting the app:

```powershell
venv\detector\Scripts\python.exe scripts\install_easyocr_assets.py
```

The assets stay under ignored `.cache/easyocr/`. Missing Tesseract or TrOCR does
not disable EasyOCR. Missing route-reference CSV now disables only endpoint
matching; detection, crops and raw OCR remain available.

## Inference contract

| Model ID | Model label | Stable API label | OCR/application use |
|---:|---|---|---|
| 0 | `front_eds` | `eds` | Owns component fields and supplies the whole-panel crop. |
| 1 | `front_eds_num` | `bus_number` | OCR service identifier and exact reference lookup. |
| 2 | `front_eds_route` | `route` | OCR intermediate road/landmark text; displayed but not treated as a verified endpoint. |
| 3 | `front_eds_destination` | `destination` | OCR destination and reference endpoint comparison. |

The app rejects a checkpoint whose embedded class names do not exactly match this
order. Inference uses 640-pixel input, default confidence `0.50`, NMS IoU `0.70`, all four
classes and at most 100 detections. Rear-facing EDS and unrelated text are excluded.

## Evidence and limitations

- Multiple panels and fields are associated by containment; fields are not paired
  across known panel owners.
- Detection, OCR and matching confidence remain separate quantities.
- Route OCR is observational; current references do not verify road-name coverage.
- EasyOCR integration latency and raw observations are recorded in
  `deployment/easyocr_integration_verification.json`. OCR accuracy remains
  unmeasured because reviewed text transcriptions are absent.
- Browser camera and uploaded-video controls have automated lifecycle/decode tests.
  Real camera hardware, moving buses, glare and sustained field latency still require
  a recorded field test; simulated tests must not be reported as that evidence.
