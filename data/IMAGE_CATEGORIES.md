# Image coverage in the data-preparation snapshot

## Current snapshot

- The `2026-10-24` snapshot contains **212 raw images**. The tracked manifest is
  `data/manifests/2026-10-24.csv`; image payloads are excluded from the current
  Git tree. The raw images can be inspected in commit `9b15447`.
- The base Roboflow COCO export has **199 images** (140 train, 39 validation,
  20 test) and four annotated classes: `front_eds`,
  `front_eds_destination`, `front_eds_num`, and `front_eds_route`. The historical Roboflow augmented
  export has **479 images** (420 train, 39 validation, 20 test). These exports
  are derived data, not additional raw photos.
- The raw set mixes camera photos, screenshots, and visibly watermarked images.
  Source and usage-permission records are not in this branch. Its manifest
  records paths, sizes, and SHA-256 checksums, but not provenance.

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

The remaining work is tracked in [DATA_PREP_TODO.md](DATA_PREP_TODO.md).

## Reviewed visual examples

[data_visual_checks.ipynb](../notebooks/data_visual_checks.ipynb) displays three
images in one row for each category above. Filenames, SHA-256 hashes and brief
observations are recorded in
[the preview sample manifest](manifests/2026-10-24-preview-samples.json).
These examples were visually selected, not assigned by an automatic classifier.
They do not establish per-category counts or exhaustive coverage. Rear views,
bus-stop signs and arrival screens illustrate exclusion/hard-negative context;
they are not additional bounding-box classes. See the
[annotation guide](../eds_layout_and_annotation_guide.md) for target scope.
