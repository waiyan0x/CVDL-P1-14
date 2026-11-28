# Reviewed-v4 OCR package

The **reviewed-v4 package** is `ocr_handoff_v4-reviewed-01.zip`, stored with Git LFS. Extract it before using the crops or editing the templates. It supersedes the old validation-only crop folder and local crop-only ZIPs. It does not use Jy's v5 dataset.

ZIP size: 219,028,922 bytes. SHA-256: `785a0958b79e1062847e9dc81c9d024cd67a9acb0c614bf74c64e2147d344685`.

Inside the ZIP:

| Location | Contents |
| --- | --- |
| `train/`, `valid/`, `test/` | Annotation crops in `front_eds/`, `front_eds_num/`, `front_eds_route/`, and `front_eds_destination/` class folders, plus one blank `transcriptions_template.csv` per split. |
| `transcriptions_template.xlsx` | The same blank text-field rows in three Excel sheets. Reviewers can work in Excel after extraction. |
| `valid/predicted/` | 160 distinct YOLO11s validation detector crops. |
| `manifest.json` and `valid/detector_predictions_manifest.json` | Crop, source image, box, hash, and detector prediction provenance. |
| `source_coco/` | Original reviewed-v4 train/valid/test whole photos, each split's `_annotations.coco.json`, and `preparation_manifest.json`. |
| `detector/yolo11s-best.pt` | Selected YOLO11s checkpoint (SHA-256 `97150601de39a999754015648cad2ef930842d52e8e37eb77d7576ffe2da33b5`). |

| Split | Whole source images | Annotation crops | Text-field rows | Zero-box negatives |
| --- | ---: | ---: | ---: | ---: |
| Train | 735 | 2,754 | 1,917 | 147 |
| Validation | 53 | 221 | 157 | 10 |
| Test | 53 | 171 | 118 | 12 |

Class folders identify **box categories**, not the sign text. Every transcription field is blank and pending review. Reviewers must record the visible text, their own name and actual date, and unreadable/excluded cases. Keep the test split closed while selecting OCR settings. Detector settings for the validation predictions were confidence `0.50`, NMS IoU `0.70`, and image size `640`.

Verify the extracted source with its `preparation_manifest.json`. The source metadata identifies Roboflow Front EDS v4 with a CC BY 4.0 notice; individual image source and usage permission records still require review. The original frozen detector dataset and historical `baseline-01` results remain unchanged.

For the historical v4 work sequence, read the [OCR handoff guide](../../OCR_HANDOFF.md).
