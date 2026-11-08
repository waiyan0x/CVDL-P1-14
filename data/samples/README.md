# Samples by image subcategory

Reviewed on **2026-10-29**. This gallery replaces the old numbered broad-category
and legacy UI samples with **48 images**: **44 coverage representatives** and
**four isolated augmentation previews**. The 44 cover every one of the 41 distinct
subcategories in [the coverage guide](../IMAGE_CATEGORIES.md), plus three baseline
cases from its broad table: straight-on front, close/readable EDS and Off Service.

Folders follow the eight broad categories. Each image filename describes its
subcategory. One image is selected per subcategory; categories can overlap.
Selection prioritises a visible distinguishing feature over overall image beauty.
Rows describe the pictured scene; they are not new annotation classes or counts
of how many dataset images belong to a category. Rear EDS is excluded from targets.

Coverage images are byte-for-byte copies of raw sources. Two raw files named
`.jpg` contain AVIF data; their sample filenames correctly use `.avif` while
retaining the original bytes. No cropping, resizing or overlays were added.


## Viewing angle and display location

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Straight-on front | [straight-on-front.avif](viewing-angle-and-display-location/straight-on-front.avif) | Almost straight-on view of route 176 at a sheltered stop; the front display spans the bus face with little perspective compression. |
| Three-quarter front | [three-quarter-front.jpg](viewing-angle-and-display-location/three-quarter-front.jpg) | Three-quarter front view of a single-decker in bright daylight. |
| Side-on | [side-on.jpg](viewing-angle-and-display-location/side-on.jpg) | Side-on view; front panel is compressed at a steep angle. |
| Elevated viewpoint | [elevated-viewpoint.jpg](viewing-angle-and-display-location/elevated-viewpoint.jpg) | High-angle view of a single-decker turning in. |
| Bus partly outside the frame | [bus-partly-outside-the-frame.jpg](viewing-angle-and-display-location/bus-partly-outside-the-frame.jpg) | Bus cut off at the left edge; part of the destination is outside the frame. |
| Side EDS | [side-eds.jpg](viewing-angle-and-display-location/side-eds.jpg) | Side display beside the door in a dark scene; side EDS is a labelled target. |

## Distance and image quality

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Close readable EDS | [close-readable-eds.jpg](distance-and-image-quality/close-readable-eds.jpg) | Close front view with legible two-line destination and service 124; offers a readable contrast to small, blurred and cropped examples. |
| Distant / small bus | [distant-small-bus.jpg](distance-and-image-quality/distant-small-bus.jpg) | Distant bus behind a lorry; panel is only a few pixels high. |
| Motion blur | [motion-blur.jpg](distance-and-image-quality/motion-blur.jpg) | Moving double-decker; panel text smeared by motion blur. |
| Low resolution | [low-resolution.jpg](distance-and-image-quality/low-resolution.jpg) | Native 150 × 150 front-view image; LED characters merge into a few pixels. Stronger low-resolution example than the 300 × 240 alternative. |
| EDS cropped at the image edge | [eds-cropped-at-the-image-edge.jpg](distance-and-image-quality/eds-cropped-at-the-image-edge.jpg) | The front display runs into the left/top edge of the screenshot, clipping the start of the LED message. |

## Lighting and environment

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Bright daylight | [bright-daylight.jpg](lighting-and-environment/bright-daylight.jpg) | Bright daylight; amber text against a dark housing. |
| Backlit / sunset | [backlit-sunset.jpg](lighting-and-environment/backlit-sunset.jpg) | Sunset behind the bus; panel against a bright sky. |
| Night with headlight glare | [night-with-headlight-glare.jpg](lighting-and-environment/night-with-headlight-glare.jpg) | Night with strong headlight glare and glass reflections. |
| Dim covered interchange | [dim-covered-interchange.jpg](lighting-and-environment/dim-covered-interchange.jpg) | Covered interchange; bright headlights with dim surroundings. |
| Rain / wet road | [rain-wet-road.jpg](lighting-and-environment/rain-wet-road.jpg) | Rain haze and a wet road at an interchange. |

## EDS text and layout

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Destination + via route + number | [destination-via-route-number.jpg](eds-text-and-layout/destination-via-route-number.jpg) | "via" route line under the destination, number on the right. |
| Two-line destination with > | [two-line-destination-with-chevron.avif](eds-text-and-layout/two-line-destination-with-chevron.avif) | Two-line destination; second line starts with ">". |
| One-line destination + number, no route | [one-line-destination-number-no-route.jpg](eds-text-and-layout/one-line-destination-number-no-route.jpg) | One-line destination and number; no route line. |
| Number only | [number-only.jpg](eds-text-and-layout/number-only.jpg) | Service number 384 shown without a destination. |
| Number with a letter suffix | [number-with-a-letter-suffix.jpg](eds-text-and-layout/number-with-a-letter-suffix.jpg) | Service number with a letter suffix (170X). |
| Red/pink LED text | [red-pink-led-text.jpg](eds-text-and-layout/red-pink-led-text.jpg) | Red/pink LED text instead of amber at night. |

## Special display messages

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Off Service | [off-service.jpg](special-display-messages/off-service.jpg) | Large, clearly visible OFF SERVICE message with no ordinary route number/destination pair. |
| Terminate at | [terminate-at.jpg](special-display-messages/terminate-at.jpg) | "TERMINATE AT ORCHARD RD" message with 7B. |
| Express and limited-stop branding | [express-and-limited-stop-branding.jpg](special-display-messages/express-and-limited-stop-branding.jpg) | "CITY DIRECT" wording beside 660. |
| Public notice | [public-notice.jpg](special-display-messages/public-notice.jpg) | "Mask on before boarding" in place of a destination. |
| Non-English text | [non-english-text.jpg](special-display-messages/non-english-text.jpg) | Chinese-character text appears beside route 284. The display is soft and this sample is not a verified text transcription. |
| Operator name on the display | [operator-name-on-the-display.jpg](special-display-messages/operator-name-on-the-display.jpg) | Front panel shows "sbs Transit" instead of a destination. |

## Bus and operator variety

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| SBS Transit | [sbs-transit.jpg](bus-and-operator-variety/sbs-transit.jpg) | SBS Transit double-decker at a night interchange. |
| SMRT | [smrt.jpg](bus-and-operator-variety/smrt.jpg) | Daylight single-decker with legible SMRT branding and red/black/white livery; clearer operator evidence than the dark front-only candidate. |
| Tower Transit | [tower-transit.jpg](bus-and-operator-variety/tower-transit.jpg) | Daylight double-decker with a clearly visible Tower Transit body logo; identifies the operator even though its livery resembles other operators. |
| SG Bus livery | [sg-bus-livery.jpg](bus-and-operator-variety/sg-bus-livery.jpg) | Green SG Bus double-decker on a wet road. |
| Articulated bus | [articulated-bus.jpg](bus-and-operator-variety/articulated-bus.jpg) | Articulated (bendy) bus at a stop at dusk. |
| Advertising-wrapped bus | [advertising-wrapped-bus.jpg](bus-and-operator-variety/advertising-wrapped-bus.jpg) | Advertising wrap with large text along the bus side. |

## Crowded or obstructed scenes

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Multiple buses in one image | [multiple-buses-in-one-image.jpg](crowded-or-obstructed-scenes/multiple-buses-in-one-image.jpg) | Two buses side by side, each with its own front panel. |
| Pole or pillar blocking the bus | [pole-or-pillar-blocking-the-bus.jpg](crowded-or-obstructed-scenes/pole-or-pillar-blocking-the-bus.jpg) | Pole in front of part of the front panel at a crowded stop. |
| People in the foreground | [people-in-the-foreground.jpg](crowded-or-obstructed-scenes/people-in-the-foreground.jpg) | Person in the foreground at a bus stop. |
| Photographed through glass | [photographed-through-glass.jpg](crowded-or-obstructed-scenes/photographed-through-glass.jpg) | Buses behind glass panels and railings. |

## Distracting text and hard negatives

| Subcategory | Sample | What makes it representative |
| --- | --- | --- |
| Bus-stop sign with service numbers | [bus-stop-sign-with-service-numbers.avif](distracting-text-and-hard-negatives/bus-stop-sign-with-service-numbers.avif) | Bus-stop sign lists service numbers next to a real front panel. |
| Advertising text on the bus body | [advertising-text-on-the-bus-body.jpg](distracting-text-and-hard-negatives/advertising-text-on-the-bus-body.jpg) | Large advertising text on the bus side; video-player overlay at top left. |
| Livery text on the bus body | [livery-text-on-the-bus-body.jpg](distracting-text-and-hard-negatives/livery-text-on-the-bus-body.jpg) | "1000th Citaro" lettering on the bus body. |
| Rear EDS | [rear-eds.jpg](distracting-text-and-hard-negatives/rear-eds.jpg) | Rear "OFF SVC" display; rear EDS is excluded from labelling. |
| No front or side EDS in view | [no-front-or-side-eds-in-view.jpg](distracting-text-and-hard-negatives/no-front-or-side-eds-in-view.jpg) | Bus front with the panel outside the frame. |
| Interchange signage, no bus | [interchange-signage-no-bus.jpg](distracting-text-and-hard-negatives/interchange-signage-no-bus.jpg) | "Bus Services towards HarbourFront" sign; no bus. |

## Data augmentation

All previews use [close-readable-eds.jpg](distance-and-image-quality/close-readable-eds.jpg)
as their before image. Each enables only its named effect through the existing
`augment_sample` and `augmentation_cases` functions with seed 42.

| Subcategory | Sample | Applied value |
| --- | --- | --- |
| Brightness | [brightness-minus-10-percent.png](data-augmentation/brightness-minus-10-percent.png) | factor 0.90 |
| Rotation | [rotation-plus-3-degrees.png](data-augmentation/rotation-plus-3-degrees.png) | +3 degrees |
| Salt/pepper noise | [salt-pepper-noise-1-percent.png](data-augmentation/salt-pepper-noise-1-percent.png) | 1% expected pixel rate |
| Gaussian blur | [gaussian-blur-sigma-1-px.png](data-augmentation/gaussian-blur-sigma-1-px.png) | sigma 1 px |

Brightness uses −10% (factor 0.90) from the configured ±10% range. Rotation uses
+3° from ±3°, with the pipeline's grey padding to retain the scene. Salt/pepper
noise affects a 1% expected pixel fraction, with RGB channels changed together.
Gaussian blur uses sigma 1 px and a kernel up to 7 px. These are controlled
demonstrations, not claimed members of the current combined training export.

[manifest.json](manifest.json) records source paths, SHA-256 hashes, observations
and transform settings. [dataset_inventory.json](dataset_inventory.json) retains
the independently verified dataset counts. Gallery copies and demonstrations
do not change raw, labelled or training dataset counts. The notebook's existing
gallery and metadata remain a separate selection.
