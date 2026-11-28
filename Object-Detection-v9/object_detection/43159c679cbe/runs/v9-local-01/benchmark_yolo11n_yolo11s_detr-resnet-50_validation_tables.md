# Detector benchmark: v9-local-01

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
| detr-resnet-50 | front_eds | 7,827 | 91.8 | 54.6 | 66.2 |
| detr-resnet-50 | front_eds_num | 7,410 | 92.3 | 63.4 | 71.1 |
| detr-resnet-50 | front_eds_route | 5,133 | 84.1 | 49.8 | 66.3 |
| detr-resnet-50 | front_eds_destination | 5,505 | 90.4 | 63.5 | 73.0 |
| **detr-resnet-50** | **All (avg)** | **25,875** | **89.6** | **57.8** | **69.1** |

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
| detr-resnet-50 | front_eds | 348 | 90.9 | 48.9 | 61.5 |
| detr-resnet-50 | front_eds_num | 335 | 92.5 | 60.8 | 68.6 |
| detr-resnet-50 | front_eds_route | 230 | 83.4 | 48.4 | 64.9 |
| detr-resnet-50 | front_eds_destination | 241 | 87.9 | 59.1 | 69.3 |
| **detr-resnet-50** | **All (avg)** | **1,154** | **88.7** | **54.3** | **66.1** |

## Test

Held out; no measured results for this split yet.

Values are measured on the named split. A dash means the class metric is unavailable.
