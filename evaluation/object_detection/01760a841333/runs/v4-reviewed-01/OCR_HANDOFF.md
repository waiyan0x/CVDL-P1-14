# YOLO11s v4 validation crop handoff

The [crop package](ocr_handoff/README.md) is committed in `ocr_handoff/`, with
individual PNG files, `manifest.json` and `transcriptions_template.csv`. Cody
can get it by pulling `bren-object-detection`. A portable local ZIP also exists
at `.runtime/ocr_handoff/v4-reviewed-01-validation.zip`. Its SHA-256 is
`b45ad9d2414f4000ac57ab9af36a3fc51466628e6c9a7fb8502933c1dc494f14`
and its size is 4,888,780 bytes; the ZIP itself is not committed.

The package covers all 53 **validation** images from the reviewed Roboflow v4
export, including ten zero-box negatives. It contains 221 annotation-box crops
and 160 selected YOLO11s prediction-box crops. Of those, 157 annotation crops
and 114 prediction crops are number, route or destination fields; the remainder
are whole-panel crops for context. At confidence `0.50`, none of the ten
validation negatives produced a predicted box. The model used 640-pixel input
and NMS IoU `0.70`.

Inside `ocr_handoff/` (and the ZIP):

- `ground_truth/`: tight crops from COCO annotations, organised by the four
  detection classes. These box locations still require human content review.
- `predicted/`: tight crops from the selected v4 YOLO11s model, with the same
  class folders. These show what downstream OCR would actually receive.
- `manifest.json`: source image hashes, crop paths, box coordinates, predicted
  confidence, and diagnostic same-class IoU matches at 0.50.
- `transcriptions_template.csv`: one row per annotation-based text-field crop,
  with blank text and `pending` review status. It contains **no verified OCR
  transcription yet**.
- `README.md`: package usage and split limitations.

Do not report OCR accuracy until the text fields are reviewed and transcribed.
Use the same predicted crops and preprocessing choices when comparing OCR
engines. The final detector test split is held out and was not exported here.
The application now defaults to this v4 checkpoint at confidence `0.50` and
NMS `0.70`. The earlier `baseline-01` checkpoint remains documented separately.

To regenerate this package on a machine with the ignored reviewed-v4 dataset
and selected checkpoint, from the repository root run:

```powershell
venv\detector\Scripts\python.exe scripts\export_ocr_handoff_crops.py --zip
```

Use a new `--output` path for a new export; the script refuses to overwrite an
existing package. The selected checkpoint SHA-256 is recorded in [RESULTS.md](RESULTS.md).

The source export metadata identifies Roboflow Front EDS v4 with a CC BY 4.0
notice. Individual image source and permission records remain part of the
outstanding dataset provenance review.
