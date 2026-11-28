# YOLO11s validation qualitative review

Generated from the 39-image validation split only. This package does not use the held-out test for further tuning.

## Settings and automatic counts

- Confidence: `0.20`
- NMS IoU: `0.70`
- Match IoU: `0.50`
- Images / reviewed negatives: `39 / 4`
- TP / FP / FN: `109 / 47 / 45`
- False positives on reviewed negative images: `0`
- Checkpoint SHA-256: `01d832cb6eda71dcf4a88e6ebbafc080f9dc299be8161c76ab15c75f7c60c2e3`

These counts use one-to-one, class-correct matching at the selected operating confidence. They are diagnostic counts rather than the COCO mAP computation.

## Highest-priority cases

| Rank | Image | TP | FP | FN | Blur score | Automatic reason | Overlay |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | `4ec3e58a-bus_17_jpg.rf.0cda1156155e556073d323b501e069b5.jpg` | 4 | 4 | 3 | 1539 | 3 missed box(es), 4 unmatched prediction(s), class confusion, 5 tiny GT | [overlays/case_01.jpg](overlays/case_01.jpg) |
| 2 | `5c28dd2e-426352df-66_jpg.rf.9fd217a1de1df695a431714e5ba75de6.jpg` | 3 | 1 | 5 | 573 | 5 missed box(es), 1 unmatched prediction(s), 5 tiny GT | [overlays/case_02.jpg](overlays/case_02.jpg) |
| 3 | `IMAGE_2026-10-23_22_04_04_jpg.rf.0cb9ed676b55ae03ba0719f27edc5177.jpg` | 1 | 4 | 3 | 91 | 3 missed box(es), 4 unmatched prediction(s), class confusion, 1 tiny GT | [overlays/case_03.jpg](overlays/case_03.jpg) |
| 4 | `fe6f9f51-bus_22_jpg.rf.63a66e19926e89ba20df8db74744695b.jpg` | 3 | 4 | 3 | 4894 | 3 missed box(es), 4 unmatched prediction(s), class confusion, 5 tiny GT | [overlays/case_04.jpg](overlays/case_04.jpg) |
| 5 | `Screenshot_2026-10-24-20-31-40-58_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.293cd45295c2e2157ff03fd9883e91fc.jpg` | 4 | 2 | 3 | 39 | 3 missed box(es), 2 unmatched prediction(s), class confusion, 6 tiny GT | [overlays/case_05.jpg](overlays/case_05.jpg) |
| 6 | `IMG20261024203759_jpg.rf.4c80b6912cb6bca0babd5a0c8968b7ed.jpg` | 3 | 2 | 3 | 5 | 3 missed box(es), 2 unmatched prediction(s), class confusion, 1 tiny GT | [overlays/case_06.jpg](overlays/case_06.jpg) |
| 7 | `Screenshot_2026-10-24-20-31-16-62_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.b89ba746618af3dbd32dff6d0b87890e.jpg` | 2 | 3 | 2 | 43 | 2 missed box(es), 3 unmatched prediction(s), class confusion, 3 small GT | [overlays/case_07.jpg](overlays/case_07.jpg) |
| 8 | `57ca1bf5__7bd6608a-7_jpg.rf.25c566a443488b9db54941fa46bd2f88.jpg` | 5 | 3 | 2 | 653 | 2 missed box(es), 3 unmatched prediction(s), class confusion, 6 tiny GT | [overlays/case_08.jpg](overlays/case_08.jpg) |
| 9 | `Screenshot_2026-10-24-20-31-36-84_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.c11ce65aacfffb873aa98abfd604f7f6.jpg` | 5 | 0 | 3 | 23 | 3 missed box(es), 3 tiny GT | [overlays/case_09.jpg](overlays/case_09.jpg) |
| 10 | `Screenshot_2026-10-24-20-33-23-69_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.c49a3f86ee38fbae3a205187a7cecc74.jpg` | 1 | 0 | 3 | 31 | 3 missed box(es), 4 tiny GT | [overlays/case_10.jpg](overlays/case_10.jpg) |

Contact sheet: [contact_sheet.jpg](contact_sheet.jpg)

## Class-confusion candidates

- `front_eds_destination` predicted as `front_eds_route`: 17
- `front_eds_route` predicted as `front_eds_destination`: 10

## Human visual review

The contact sheet, all ten individual overlays and representative OCR-field crops were visually inspected. Green/orange boxes are ground truth (orange means missed); blue boxes are matched predictions; red boxes are unmatched predictions.

| Rank | Image | Human observation |
|---:|---|---|
| 1 | `4ec3e58a-bus_17_jpg.rf.0cda1156155e556073d323b501e069b5.jpg` | Crisp daylight multi-bus scene, but five of seven GT fields are tiny. Route and destination occupy adjacent text bands and are repeatedly swapped; the crops are readable only when enlarged. |
| 2 | `5c28dd2e-426352df-66_jpg.rf.9fd217a1de1df695a431714e5ba75de6.jpg` | Night scene with two buses, glare and a strongly angled side display. The front number survives, while five small route/destination fields are missed; side-display crops are poor OCR inputs. |
| 3 | `IMAGE_2026-10-23_22_04_04_jpg.rf.0cb9ed676b55ae03ba0719f27edc5177.jpg` | Low-light display viewed through/behind the bus structure with overlapping field boxes. Four unmatched predictions correspond mainly to route/destination swaps, showing class-boundary ambiguity more than failure to find the display. |
| 4 | `fe6f9f51-bus_22_jpg.rf.63a66e19926e89ba20df8db74744695b.jpg` | Distant daylight multi-bus scene. Most component boxes occupy a tiny image fraction; the main number is found, but small route/destination fields on the main and background buses are missed or confused. |
| 5 | `Screenshot_2026-10-24-20-31-40-58_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.293cd45295c2e2157ff03fd9883e91fc.jpg` | Two buses at different distances with partial obstruction from roadside objects. The nearer number/route are usable, while the farther display is too small and soft for dependable OCR; three fields are missed. |
| 6 | `IMG20261024203759_jpg.rf.4c80b6912cb6bca0babd5a0c8968b7ed.jpg` | Severe motion/defocus blur and partial bus cropping. Characters are unreadable even in the saved crops, so the missed and confused component fields should be treated as image-quality failures. |
| 7 | `Screenshot_2026-10-24-20-31-16-62_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.b89ba746618af3dbd32dff6d0b87890e.jpg` | Large frontal daylight EDS with little blur. The detector localizes the display but route/destination predictions overlap and swap, making this a strong candidate for label-definition review rather than a scale-only failure. |
| 8 | `57ca1bf5__7bd6608a-7_jpg.rf.25c566a443488b9db54941fa46bd2f88.jpg` | Night multi-bus scene with headlight glare, reflections and partial occlusion. Five fields are recovered, but tiny component fields and overlapping buses create two misses and three unmatched predictions; crop readability is marginal. |
| 9 | `Screenshot_2026-10-24-20-31-36-84_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.c11ce65aacfffb873aa98abfd604f7f6.jpg` | Three tightly packed buses with distant, narrow displays. There are no unmatched predictions, but three tiny GT fields are missed; the limiting factor is scale and crowding, and OCR crops are marginal. |
| 10 | `Screenshot_2026-10-24-20-33-23-69_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.c49a3f86ee38fbae3a205187a7cecc74.jpg` | Night side view at an oblique angle. Only one of four tiny fields is recovered; perspective compression and low effective text resolution make the remaining crops unsuitable for reliable OCR. |

## Conclusions and next action

- Small/distant text is the most common miss condition: 52 of the 61 GT boxes in the ranked cases are below 1% of image area, and 36 are below 0.25%.
- Route/destination separation is the clearest class problem. Diagnostic IoU matching found 17 destination-to-route and 10 route-to-destination candidates across validation. Several examples localize the correct text band but assign the other semantic label.
- Blur, glare, oblique perspective, crowding and partial occlusion further reduce crop readability. Cases 2, 6, 8 and 10 are particularly poor OCR inputs.
- None of the four reviewed validation negatives produced a prediction at confidence 0.20. This is encouraging but too few negatives for a deployment claim.
- Before a loss-function ablation, review route/destination annotation rules and borderline boxes with Jy, then add or rebalance difficult small, night, angled and motion-blurred examples. Preserve capture/source groups when revising the split.
