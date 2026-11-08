# Image coverage in the data-preparation snapshot

## Current snapshot

- The `2026-10-24` snapshot contains **212 raw images**. Image payloads stay
  local; the early raw snapshot can also be inspected in commit `9b15447`.
- The accepted labelled source, `data/labelled/2026-10-24/`, has **196 images**
  (137 train, 39 validation, 20 test). The current training folder has
  **479 images** (420 train, 39 validation, 20 test), verified on 2026-10-29.
  Training metadata groups outputs under 140 source names, three outputs each.
  It identifies a Roboflow export and lacks the manifest needed to verify its
  augmentation lineage. Derived outputs are not additional raw photos.
- The raw set mixes camera photos, screenshots, and visibly watermarked images.
  Source and usage-permission records are not in this branch. The retained
  local export manifests record file hashes and processing lineage, not verified
  capture provenance.

## Image coverage

Categories overlap; one image may belong to several rows. These are qualitative
coverage categories, not counts per category.

| Broad category | Subsets visible in the images | Why we included them |
| --- | --- | --- |
| **Viewing angle and display location** | Straight-on front; three-quarter front; side; rear; bus partly outside the frame; front EDS and side/rear displays where visible. | The display changes shape and position with perspective. Front and side EDS are targets; rear EDS is excluded under the annotation guide. |
| **Distance and image quality** | Close, readable buses; small or distant buses; soft focus, motion blur, low resolution, and cropped displays. | Tests whether the system still finds the bus and knows when EDS text is too small or unclear to read reliably. |
| **Lighting and environment** | Bright sun, shade, backlighting or windshield glare; dusk and night with bright LEDs/headlights; sheltered interchanges and bus stops. | EDS contrast and reflections vary substantially across real operating conditions. |
| **EDS text and layout** | Route number with destination; number and destination without a detailed route or “via” line; one-line and multi-line destination text; number placed at different positions; different LED brightness, colour, and spacing. | Prevents the reader from assuming one fixed text position or format. Covers short and long messages on different bus and display designs. |
| **Special display messages** | Non-standard service text such as **“Off Service”**, express or limited-stop wording, and other destination/status messages. | Helps the model avoid forcing every lit display into an ordinary route-number-and-destination pattern. |
| **Bus and operator variety** | Single- and double-deck buses; different front shapes, display housings, and liveries, including SBS Transit, SMRT, Tower Transit and SG Bus-branded vehicles. | Checks that detection generalises across bus models and operators. Display hardware and layout can vary even within one operator. |
| **Crowded or obstructed scenes** | Multiple buses in one image; buses behind other buses; people, poles, shelters, trees, and vehicles crossing the bus or EDS; busy interchange backgrounds. | Forces the system to associate each display with the correct bus and handle partly hidden text. |
| **Distracting text and hard negatives** | Bus-stop/service signs, advertisements, vehicle branding, side or rear text, and scenes with no readable front EDS. | Tests whether the system reads the actual front display instead of nearby unrelated text or inventing a reading when none is visible. |

The [training handoff](../docs/data_preparation/TRAINING_READINESS.md) describes
the prepared detector dataset. Remaining evidence and later project work are
recorded in the [pipeline review](../docs/data_preparation/OUTSTANDING_ISSUES.md).

## Reviewed visual examples

[data_visual_checks.ipynb](../notebooks/data_visual_checks.ipynb) displays three
images in one row for each category above. Filenames, SHA-256 hashes and brief
observations are recorded in
[the notebook sample JSON](../notebooks/preview_samples.json).
These examples were visually selected, not assigned by an automatic classifier.
They do not establish per-category counts or exhaustive coverage. Rear views,
bus-stop signs and arrival screens illustrate exclusion/hard-negative context;
they are not additional bounding-box classes. See the
[annotation guide](../docs/annotation/guide.md) for target scope.

## Selected representatives by subcategory

[The sample gallery](samples/README.md) contains **44 coverage images**: one for
each of the 41 distinct subsets documented below, plus straight-on front,
close/readable EDS and Off Service from the broad coverage table. Files are
grouped by broad category and named after the subcategory. The gallery includes
four separate augmentation previews (48 sample images total).

The selections were compared visually with the raw candidates; the clearest
example of each distinguishing feature was preferred. In particular, the
gallery uses a 150 × 150 front view for low resolution and a daylight SMRT view
with clearer branding. The tables below remain additional candidate examples;
their rows do not dictate the gallery's chosen file. Sources, hashes and reasons
are recorded in `data/samples/manifest.json`. The notebook gallery is separate.

## Additional examples by subset

These examples extend the [notebook samples](../notebooks/preview_samples.json)
under the same eight categories, split into finer subsets. None of the
notebook's images are repeated. Paths are from the repository root.
Categories overlap; these are illustrative examples, not category counts.

Under the [annotation guide](../docs/annotation/guide.md), front and side EDS
are labelled targets and rear EDS is excluded, so rear views are listed as hard
negatives.

### Viewing angle and display location

| Subset | Image | Observation |
| --- | --- | --- |
| Three-quarter front | `data/raw/2026-10-24/1eb1313a-bus_25.jpg` | Three-quarter view of a double-decker; front panel seen at an angle. |
| Three-quarter front | `data/raw/2026-10-24/ccd80ac0-bus_3.jpg` | Three-quarter front view of a single-decker in bright daylight. |
| Side-on | `data/raw/2026-10-24/86406228__82dccf57-1453.jpg` | Side-on view; front panel is compressed at a steep angle. |
| Side-on | `data/raw/2026-10-24/8d6d224a__5e37e4fd-1204.jpg` | Side-on single-decker at a stop; front panel is small and angled. |
| Elevated viewpoint | `data/raw/2026-10-24/IMAGE 2026-10-23 22_12_50.jpg` | Elevated viewpoint looking down on the bus front. |
| Elevated viewpoint | `data/raw/2026-10-24/a1af74f0__3b8afd1d-10.jpg` | High-angle view of a single-decker turning in. |
| Bus partly outside the frame | `data/raw/2026-10-24/Screenshot_2026-10-24-20-31-51-31_f9ee0578fe1cc94de7482bd41accb329.jpg` | Bus cut off at the right edge; front panel still visible. |
| Bus partly outside the frame | `data/raw/2026-10-24/Screenshot_2026-10-24-20-36-08-87_f9ee0578fe1cc94de7482bd41accb329.jpg` | Bus cut off at the left edge; part of the destination is outside the frame. |
| Side EDS | `data/raw/2026-10-24/IMAGE 2026-10-23 22_04_04.jpg` | Side display beside the door in a dark scene; side EDS is a labelled target. |
| Side EDS | `data/raw/2026-10-24/IMAGE 2026-10-23 21_55_18.jpg` | Side display on a double-decker at an interchange berth. |

### Distance and image quality

| Subset | Image | Observation |
| --- | --- | --- |
| Distant / small bus | `data/raw/2026-10-24/18c17495__774fa852-32.jpg` | Distant bus behind a lorry; panel is only a few pixels high. |
| Motion blur | `data/raw/2026-10-24/8c3cf30a__afc6ed73-1452.jpg` | Night shot with motion blur and street-light flare. |
| Motion blur | `data/raw/2026-10-24/IMG20261024204414.jpg` | Moving double-decker; panel text smeared by motion blur. |
| Low resolution | `data/raw/2026-10-24/fce77034-bus_19.jpg` | 300x240 image; panel characters merge together. |
| EDS cropped at the image edge | `data/raw/2026-10-24/Screenshot_2026-10-24-20-31-47-75_f9ee0578fe1cc94de7482bd41accb329.jpg` | Front panel cut off at the top-left edge of the frame. |
| EDS cropped at the image edge | `data/raw/2026-10-24/Screenshot_2026-10-24-20-31-16-62_f9ee0578fe1cc94de7482bd41accb329.jpg` | Close crop; part of the destination text is outside the frame. |

### Lighting and environment

| Subset | Image | Observation |
| --- | --- | --- |
| Bright daylight | `data/raw/2026-10-24/ea59d01b-212fcccc-138.jpg` | Bright daylight; amber text against a dark housing. |
| Backlit / sunset | `data/raw/2026-10-24/Screenshot_2026-10-24-20-30-42-44_f9ee0578fe1cc94de7482bd41accb329.jpg` | Sunset behind the bus; panel against a bright sky. |
| Night with headlight glare | `data/raw/2026-10-24/159ee871__0cc20afd-643.jpg` | Night with strong headlight glare and glass reflections. |
| Night with headlight glare | `data/raw/2026-10-24/c3135218__54e3dc26-1456.jpg` | Night with headlight flare beside a red traffic light. |
| Dim covered interchange | `data/raw/2026-10-24/11c0e4ce__0efd8c24-16.jpg` | Covered interchange; bright headlights with dim surroundings. |
| Rain / wet road | `data/raw/2026-10-24/a3f68075-b877a683-3.jpg` | Rain haze and a wet road at an interchange. |
| Rain / wet road | `data/raw/2026-10-24/f168db11__5c0aa197-386.jpg` | Wet road with reflections under the bus. |

### EDS text and layout

| Subset | Image | Observation |
| --- | --- | --- |
| Destination + via route + number | `data/raw/2026-10-24/IMG20261024204212.jpg` | "via" route line under the destination, number on the right. |
| Two-line destination with > | `data/raw/2026-10-24/fce01393-3b0671f0-272.jpg` | Two-line destination; second line starts with ">". |
| One-line destination + number, no route | `data/raw/2026-10-24/7ad1fda5-948e0751-382G.jpg` | One-line destination and number; no route line. |
| One-line destination + number, no route | `data/raw/2026-10-24/8c8975f2__d9140853-49.jpg` | One-line destination and number at an interchange. |
| Number only | `data/raw/2026-10-24/IMAGE 2026-10-23 21_55_08.jpg` | Service number 384 shown without a destination. |
| Number only | `data/raw/2026-10-24/IMAGE 2026-10-23 21_55_41.jpg` | Service number 386 shown without a destination. |
| Number with a letter suffix | `data/raw/2026-10-24/88ceca91__c40d16a8-131M.jpg` | Service number with a letter suffix (131M). |
| Number with a letter suffix | `data/raw/2026-10-24/a99f66b7-1c01c769-170x.jpg` | Service number with a letter suffix (170X). |
| Number with a letter suffix | `data/raw/2026-10-24/e8f74339-bus_24.jpg` | Double-decker showing 248M. |
| Red/pink LED text | `data/raw/2026-10-24/Screenshot_2026-10-24-20-34-34-01_f9ee0578fe1cc94de7482bd41accb329.jpg` | Red/pink LED text instead of amber at night. |

### Special display messages

| Subset | Image | Observation |
| --- | --- | --- |
| Terminate at | `data/raw/2026-10-24/c22dd64d__8c462f49-51A.jpg` | "TERMINATE AT" short-working message with 51A. |
| Terminate at | `data/raw/2026-10-24/IMG20261024204444.jpg` | "TERMINATE AT ORCHARD RD" message with 7B. |
| Express and limited-stop branding | `data/raw/2026-10-24/IMG20261024204233.jpg` | "Fast Forward" branding beside 147e. |
| Express and limited-stop branding | `data/raw/2026-10-24/101d21ec-a1646361-660.jpg` | "CITY DIRECT" wording beside 660. |
| Public notice | `data/raw/2026-10-24/e6da286e__f1a820d8-77.jpg` | "Mask on before boarding" in place of a destination. |
| Non-English text | `data/raw/2026-10-24/IMG20261024203954.jpg` | Chinese New Year greeting in Chinese characters beside 284. |
| Operator name on the display | `data/raw/2026-10-24/Screenshot_2026-10-24-20-36-12-52_f9ee0578fe1cc94de7482bd41accb329.jpg` | Front panel shows "sbs Transit" instead of a destination. |

### Bus and operator variety

| Subset | Image | Observation |
| --- | --- | --- |
| SBS Transit | `data/raw/2026-10-24/49775ed2__a5dcfafd-122.jpg` | SBS Transit double-decker at a night interchange. |
| SMRT | `data/raw/2026-10-24/11f93650__c441d33c-67.jpg` | SMRT double-decker at a night interchange. |
| SMRT | `data/raw/2026-10-24/IMAGE 2026-10-23 22_00_52.jpg` | SMRT single-decker on cross-border service 950. |
| Tower Transit | `data/raw/2026-10-24/7768179e-bus_16.jpg` | Tower Transit double-decker; panel shows the operator name. |
| SG Bus livery | `data/raw/2026-10-24/8d1b1e36__9b19a4c8-62.jpg` | Green SG Bus double-decker on a wet road. |
| Articulated bus | `data/raw/2026-10-24/8a7bda49-965.jpg` | Articulated (bendy) bus at a stop at dusk. |
| Advertising-wrapped bus | `data/raw/2026-10-24/352eed8b__1433d18a-1325.jpg` | Advertising wrap with large text along the bus side. |

### Crowded or obstructed scenes

| Subset | Image | Observation |
| --- | --- | --- |
| Multiple buses in one image | `data/raw/2026-10-24/Screenshot_2026-10-24-20-30-22-72_f9ee0578fe1cc94de7482bd41accb329.jpg` | Two buses side by side, each with its own front panel. |
| Multiple buses in one image | `data/raw/2026-10-24/404c1c1b-bus_2.png` | Two buses at interchange berths; one shows only a number. |
| Pole or pillar blocking the bus | `data/raw/2026-10-24/5f70217e-b77e92ba-329.jpg` | Pole in front of part of the front panel at a crowded stop. |
| Pole or pillar blocking the bus | `data/raw/2026-10-24/IMAGE 2026-10-23 21_55_51.jpg` | Pillar and boarding passengers cover part of the bus front. |
| People in the foreground | `data/raw/2026-10-24/f530945b-43ba0cf3-31.jpg` | Person in the foreground at a bus stop. |
| People in the foreground | `data/raw/2026-10-24/bceb09d2-c89c1fa8-14_2.jpg` | Passengers boarding in front of the bus. |
| Photographed through glass | `data/raw/2026-10-24/IMG20261022115750.jpg` | Bus seen through interchange glass with reflections. |
| Photographed through glass | `data/raw/2026-10-24/IMG20261022123822.jpg` | Buses behind glass panels and railings. |

### Distracting text and hard negatives

| Subset | Image | Observation |
| --- | --- | --- |
| Bus-stop sign with service numbers | `data/raw/2026-10-24/6b2ac35e-2508011c-135.jpg` | Bus-stop sign lists service numbers next to a real front panel. |
| Advertising text on the bus body | `data/raw/2026-10-24/Screenshot_2026-10-24-20-36-28-77_f9ee0578fe1cc94de7482bd41accb329.jpg` | Large advertising text on the bus side; video-player overlay at top left. |
| Livery text on the bus body | `data/raw/2026-10-24/Screenshot_2026-10-24-20-33-02-23_f9ee0578fe1cc94de7482bd41accb329.jpg` | "1000th Citaro" lettering on the bus body. |
| Rear EDS | `data/raw/2026-10-24/IMG20261024204105.jpg` | Rear number display; rear EDS is excluded from labelling. |
| Rear EDS | `data/raw/2026-10-24/Screenshot_2026-10-24-20-35-28-51_f9ee0578fe1cc94de7482bd41accb329.jpg` | Rear "OFF SVC" display; rear EDS is excluded from labelling. |
| No front or side EDS in view | `data/raw/2026-10-24/Screenshot_2026-10-24-20-34-58-22_f9ee0578fe1cc94de7482bd41accb329.jpg` | Bus front with the panel outside the frame. |
| Interchange signage, no bus | `data/raw/2026-10-24/IMG_20261022_115936.jpg` | "Bus Services towards HarbourFront" sign; no bus. |
| Interchange signage, no bus | `data/raw/2026-10-24/IMAGE 2026-10-23 21_56_09.jpg` | Interchange concourse with signs; no bus EDS. |

### Image not to use

`data/raw/2026-10-24/annotated_0c7ddfa8-27d65774-133.jpg` is a copy of
`data/raw/2026-10-24/0c7ddfa8-27d65774-133.jpg` with a box and caption drawn
onto the pixels. Do not use it as a raw image.
