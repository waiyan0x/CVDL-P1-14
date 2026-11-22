# V4 YOLO11s validation NMS and crop review

This is a **validation-only** follow-up to `v4-reviewed-01`. It reuses the saved
YOLO11s `best.pt` checkpoint and the same 53 validation images; it does not
train a model or open the held-out test. The dataset and checkpoint hashes,
per-image boxes, matches and metrics are in [nms_validation.json](nms_validation.json).

## NMS IoU comparison

Both settings used image size 640, prediction floor 0.001 for COCO mAP,
operating confidence 0.50 for the diagnostic counts, and one-to-one
class-correct matching at IoU 0.50. The ten zero-box validation images were
included. TP/FP/FN and F1 below are operating-point diagnostics, not COCO AP.

| NMS IoU | mAP50 | mAP50:95 | TP | FP | FN | IoU50 F1 | FP on negatives |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.50 | 0.6191 | 0.3532 | 130 | 24 | 91 | 0.6933 | 0 |
| 0.70 | 0.6131 | 0.3510 | 131 | 29 | 90 | 0.6877 | 0 |

NMS 0.50 has a **small validation advantage**: +0.0022 mAP50:95 and +0.0057
diagnostic F1, with five fewer unmatched predictions but one fewer true
positive. Only five of 53 images changed TP/FP/FN counts. The existing final
test was performed at NMS 0.70 before this follow-up; its mAP50:95 `0.3270`
belongs only to that recorded setting. Keep 0.70 as the **recorded tested
configuration**. Treat 0.50 as an exploratory candidate for a future version;
do not relabel or rerun the same held-out test to claim an improved final score.

## Failure and crop inspection

At NMS 0.70, the operating-point diagnostic found 131 TP, 29 FP and 90 FN
across 221 annotated boxes. Nine of 43 positive validation images had no
unmatched predictions or annotations at IoU 0.50. Thirteen unmatched
route/destination overlaps were potential class confusions: eight destination
labels predicted as route and five route labels predicted as destination. These
are candidates for the deferred Jy/Brendan annotation review, not proven label
errors. None of ten zero-box images produced a prediction at confidence 0.50.

The twelve highest-ranked failure overlays were visually inspected. They
contain 55 of the 90 diagnostic misses and 67 annotated boxes smaller than
0.25% of their image area. The selection deliberately concentrates difficult
images, so its scene frequencies are **not** a performance estimate by
lighting or bus type.

For contrast, three validation images with no diagnostic FP or FN were also
inspected: [one daylight single bus](overlays/success_01.jpg), [another daylight
frontal display](overlays/success_02.jpg), and [a night double-decker with a
large visible front sign](overlays/success_03.jpg). These show that the model
can return all annotated panel, number, route and destination boxes in both
day and night scenes when the display is sufficiently visible. This is a
box-matching observation; text readability and OCR correctness are unmeasured.

| Examples | Visible condition | Detector/crop observation |
| --- | --- | --- |
| [1](overlays/case_01.jpg), [2](overlays/case_02.jpg) | Several buses at different distances; wet daylight road in case 1 and night street in case 2 | Nearer displays yield boxes, while small distant signs have many missed component fields. Their missing crops cannot reach OCR. |
| [3](overlays/case_03.jpg), [7](overlays/case_07.jpg) | Night bus viewed from an oblique side angle | The annotation overlays show front/side text that is very small or compressed; at confidence 0.50 the detector returns no matching boxes in these cases. |
| [4](overlays/case_04.jpg), [9](overlays/case_09.jpg), [10](overlays/case_10.jpg) | Daylight scenes with multiple buses and adjacent display panels | Some clear nearby fields are detected, while other buses or nested route/destination regions are missed or confused. OCR must keep each crop tied to its bus/panel. |
| [5](overlays/case_05.jpg), [6](overlays/case_06.jpg), [8](overlays/case_08.jpg) | Night displays with glare, reflections, or small side signs | Number and some front text boxes survive, but side-sign and route/destination coverage is incomplete; small or saturated crops may be difficult for OCR. |
| [11](overlays/case_11.jpg), [12](overlays/case_12.jpg) | Daylight buses with visible front text | Major panels and numbers are detected; overlapping route/destination boxes and missed text still require a crop-level check. |

The committed [OCR handoff](../ocr_handoff/README.md) contains all 160
predicted-box crops at the recorded `0.50` confidence / `0.70` NMS setting and
221 annotation-box crops. It does not provide verified transcriptions or OCR
accuracy. Visual inspection of these examples suggests **small/distant signs,
oblique side views, and nested route/destination text** as priorities for
future image-quality and annotation review. No causal claim about a bus type
or lighting category is made from this purposive sample.

## Remaining boundary

Jy/Brendan human review of class semantics, negatives and source provenance is
on hold. Preserve this run and its tested configuration. If that review changes
labels or splits, create a new dataset/run and use a new independent held-out
set for the revised final configuration.
