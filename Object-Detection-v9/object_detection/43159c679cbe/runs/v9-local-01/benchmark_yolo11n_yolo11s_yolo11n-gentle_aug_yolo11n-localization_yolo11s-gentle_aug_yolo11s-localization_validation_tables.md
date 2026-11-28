# Detector benchmark: v9-local-01, v9-tuning-01

## Train

Images: 6858; negative images: 579.

| Model | Class | Boxes (n) | mAP50 (%) | mAP50:95 (%) | Recall mAR@100 (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| yolo11n | front_eds | 7,827 | 92.4 | 59.7 | 71.7 |
| yolo11n | front_eds_num | 7,410 | 95.1 | 76.4 | 80.1 |
| yolo11n | front_eds_route | 5,133 | 92.0 | 63.0 | 70.2 |
| yolo11n | front_eds_destination | 5,505 | 93.1 | 69.4 | 75.4 |
| **yolo11n** | **All (avg)** | **25,875** | **93.2** | **67.1** | **74.4** |
| yolo11s | front_eds | 7,827 | 96.3 | 69.1 | 75.7 |
| yolo11s | front_eds_num | 7,410 | 96.7 | 79.1 | 82.7 |
| yolo11s | front_eds_route | 5,133 | 93.8 | 69.0 | 74.5 |
| yolo11s | front_eds_destination | 5,505 | 94.5 | 74.8 | 79.4 |
| **yolo11s** | **All (avg)** | **25,875** | **95.3** | **73.0** | **78.1** |
| yolo11n-gentle_aug | front_eds | 7,827 | 98.7 | 82.2 | 85.6 |
| yolo11n-gentle_aug | front_eds_num | 7,410 | 97.0 | 83.0 | 85.5 |
| yolo11n-gentle_aug | front_eds_route | 5,133 | 95.9 | 77.0 | 81.2 |
| yolo11n-gentle_aug | front_eds_destination | 5,505 | 96.0 | 82.5 | 86.1 |
| **yolo11n-gentle_aug** | **All (avg)** | **25,875** | **96.9** | **81.2** | **84.6** |
| yolo11n-localization | front_eds | 7,827 | 95.0 | 66.7 | 75.8 |
| yolo11n-localization | front_eds_num | 7,410 | 96.7 | 80.5 | 84.2 |
| yolo11n-localization | front_eds_route | 5,133 | 94.2 | 72.5 | 78.3 |
| yolo11n-localization | front_eds_destination | 5,505 | 94.3 | 76.8 | 81.7 |
| **yolo11n-localization** | **All (avg)** | **25,875** | **95.0** | **74.1** | **80.0** |
| yolo11s-gentle_aug | front_eds | 7,827 | 98.9 | 84.3 | 87.3 |
| yolo11s-gentle_aug | front_eds_num | 7,410 | 97.0 | 84.2 | 86.5 |
| yolo11s-gentle_aug | front_eds_route | 5,133 | 95.9 | 77.5 | 81.8 |
| yolo11s-gentle_aug | front_eds_destination | 5,505 | 96.0 | 83.2 | 86.4 |
| **yolo11s-gentle_aug** | **All (avg)** | **25,875** | **96.9** | **82.3** | **85.5** |
| yolo11s-localization | front_eds | 7,827 | 94.1 | 61.0 | 72.1 |
| yolo11s-localization | front_eds_num | 7,410 | 96.4 | 79.5 | 83.6 |
| yolo11s-localization | front_eds_route | 5,133 | 94.3 | 68.9 | 75.9 |
| yolo11s-localization | front_eds_destination | 5,505 | 94.4 | 70.6 | 77.1 |
| **yolo11s-localization** | **All (avg)** | **25,875** | **94.8** | **70.0** | **77.2** |

## Validation

Images: 294; negative images: 20.

| Model | Class | Boxes (n) | mAP50 (%) | mAP50:95 (%) | Recall mAR@100 (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| yolo11n | front_eds | 348 | 88.6 | 49.5 | 66.6 |
| yolo11n | front_eds_num | 335 | 94.2 | 75.3 | 79.6 |
| yolo11n | front_eds_route | 230 | 91.6 | 62.5 | 69.2 |
| yolo11n | front_eds_destination | 241 | 91.0 | 66.8 | 72.6 |
| **yolo11n** | **All (avg)** | **1,154** | **91.4** | **63.5** | **72.0** |
| yolo11s | front_eds | 348 | 91.2 | 48.6 | 61.6 |
| yolo11s | front_eds_num | 335 | 94.8 | 76.2 | 79.9 |
| yolo11s | front_eds_route | 230 | 91.4 | 62.1 | 69.0 |
| yolo11s | front_eds_destination | 241 | 91.4 | 68.6 | 73.5 |
| **yolo11s** | **All (avg)** | **1,154** | **92.2** | **63.9** | **71.0** |
| yolo11n-gentle_aug | front_eds | 348 | 91.7 | 52.6 | 63.4 |
| yolo11n-gentle_aug | front_eds_num | 335 | 94.2 | 77.4 | 81.0 |
| yolo11n-gentle_aug | front_eds_route | 230 | 90.5 | 67.3 | 72.6 |
| yolo11n-gentle_aug | front_eds_destination | 241 | 90.3 | 69.9 | 74.8 |
| **yolo11n-gentle_aug** | **All (avg)** | **1,154** | **91.7** | **66.8** | **73.0** |
| yolo11n-localization | front_eds | 348 | 91.2 | 51.3 | 65.8 |
| yolo11n-localization | front_eds_num | 335 | 95.1 | 77.9 | 82.1 |
| yolo11n-localization | front_eds_route | 230 | 91.0 | 69.4 | 75.5 |
| yolo11n-localization | front_eds_destination | 241 | 90.3 | 70.8 | 75.1 |
| **yolo11n-localization** | **All (avg)** | **1,154** | **91.9** | **67.4** | **74.6** |
| yolo11s-gentle_aug | front_eds | 348 | 92.4 | 55.4 | 64.1 |
| yolo11s-gentle_aug | front_eds_num | 335 | 93.3 | 77.7 | 81.0 |
| yolo11s-gentle_aug | front_eds_route | 230 | 91.0 | 67.9 | 74.0 |
| yolo11s-gentle_aug | front_eds_destination | 241 | 91.2 | 72.7 | 77.3 |
| **yolo11s-gentle_aug** | **All (avg)** | **1,154** | **92.0** | **68.4** | **74.1** |
| yolo11s-localization | front_eds | 348 | 91.0 | 49.7 | 64.3 |
| yolo11s-localization | front_eds_num | 335 | 95.5 | 77.6 | 81.9 |
| yolo11s-localization | front_eds_route | 230 | 93.6 | 66.9 | 74.2 |
| yolo11s-localization | front_eds_destination | 241 | 92.4 | 66.9 | 73.7 |
| **yolo11s-localization** | **All (avg)** | **1,154** | **93.1** | **65.3** | **73.5** |

## Test

Held out; no measured results for this split yet.

Values are measured on the named split. A dash means the class metric is unavailable.
