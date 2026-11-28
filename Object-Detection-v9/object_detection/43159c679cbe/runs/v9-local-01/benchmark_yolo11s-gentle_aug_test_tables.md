# Detector benchmark: v9-tuning-01

## Train

Images: 6858; negative images: 579.

| Model | Class | Boxes (n) | mAP50 (%) | mAP50:95 (%) | Recall mAR@100 (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| yolo11s-gentle_aug | front_eds | 7,827 | 98.9 | 84.3 | 87.3 |
| yolo11s-gentle_aug | front_eds_num | 7,410 | 97.0 | 84.2 | 86.5 |
| yolo11s-gentle_aug | front_eds_route | 5,133 | 95.9 | 77.5 | 81.8 |
| yolo11s-gentle_aug | front_eds_destination | 5,505 | 96.0 | 83.2 | 86.4 |
| **yolo11s-gentle_aug** | **All (avg)** | **25,875** | **96.9** | **82.3** | **85.5** |

## Validation

Images: 294; negative images: 20.

| Model | Class | Boxes (n) | mAP50 (%) | mAP50:95 (%) | Recall mAR@100 (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| yolo11s-gentle_aug | front_eds | 348 | 92.4 | 55.4 | 64.1 |
| yolo11s-gentle_aug | front_eds_num | 335 | 93.3 | 77.7 | 81.0 |
| yolo11s-gentle_aug | front_eds_route | 230 | 91.0 | 67.9 | 74.0 |
| yolo11s-gentle_aug | front_eds_destination | 241 | 91.2 | 72.7 | 77.3 |
| **yolo11s-gentle_aug** | **All (avg)** | **1,154** | **92.0** | **68.4** | **74.1** |

## Test

Images: 299; negative images: 20.

| Model | Class | Boxes (n) | mAP50 (%) | mAP50:95 (%) | Recall mAR@100 (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| yolo11s-gentle_aug | front_eds | 354 | 87.5 | 52.0 | 61.3 |
| yolo11s-gentle_aug | front_eds_num | 340 | 90.8 | 74.9 | 78.6 |
| yolo11s-gentle_aug | front_eds_route | 239 | 90.9 | 68.9 | 75.7 |
| yolo11s-gentle_aug | front_eds_destination | 232 | 92.9 | 76.9 | 81.4 |
| **yolo11s-gentle_aug** | **All (avg)** | **1,165** | **90.5** | **68.2** | **74.3** |

Values are measured on the named split. A dash means the class metric is unavailable.
