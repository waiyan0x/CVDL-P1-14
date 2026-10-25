# Data preparation: image coverage and next work

## Current snapshot

- The `2026-10-24` snapshot contains **212 raw images**. The tracked manifest is
  `data/manifests/2026-10-24.csv`; image payloads are excluded from the current
  Git tree. The raw images can be inspected in commit `9b15447`.
- The base Roboflow COCO export has **199 images** (140 train, 39 validation,
  20 test) and four annotated classes: `front_eds`,
  `front_eds_destination`, `front_eds_num`, and `front_eds_route`. The augmented
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
| **Viewing angle and display location** | Straight-on front; three-quarter front; side; rear; bus partly outside the frame; front EDS and side/rear displays where visible. | The display changes shape and position with perspective. Side and rear views help distinguish the front EDS from other displays or bus markings. |
| **Distance and image quality** | Close, readable buses; small or distant buses; soft focus, motion blur, low resolution, and cropped displays. | Tests whether the system still finds the bus and knows when EDS text is too small or unclear to read reliably. |
| **Lighting and environment** | Bright sun, shade, backlighting or windshield glare; dusk and night with bright LEDs/headlights; sheltered interchanges and bus stops. | EDS contrast and reflections vary substantially across real operating conditions. |
| **EDS text and layout** | Route number with destination; number and destination without a detailed route or “via” line; one-line and multi-line destination text; number placed at different positions; different LED brightness, colour, and spacing. | Prevents the reader from assuming one fixed text position or format. Covers short and long messages on different bus and display designs. |
| **Special display messages** | Non-standard service text such as **“Off Service”**, express or limited-stop wording, and other destination/status messages. | Helps the model avoid forcing every lit display into an ordinary route-number-and-destination pattern. |
| **Bus and operator variety** | Single- and double-deck buses; different front shapes, display housings, and liveries, including SBS Transit, SMRT, Tower Transit and SG Bus-branded vehicles. | Checks that detection generalises across bus models and operators. Display hardware and layout can vary even within one operator. |
| **Crowded or obstructed scenes** | Multiple buses in one image; buses behind other buses; people, poles, shelters, trees, and vehicles crossing the bus or EDS; busy interchange backgrounds. | Forces the system to associate each display with the correct bus and handle partly hidden text. |
| **Distracting text and hard negatives** | Bus-stop/service signs, advertisements, vehicle branding, side or rear text, and scenes with no readable front EDS. | Tests whether the system reads the actual front display instead of nearby unrelated text or inventing a reading when none is visible. |

## Next Data Prep work

1. **Agree on the dataset contract.** Confirm supported front/side/rear EDS,
   required text fields, camera and video inputs, and whether multiple EDS in
   one frame are in scope. Write consistent box and text-label rules before
   adding more annotations.
2. **Make the snapshot accessible and traceable.** Put the raw and export files
   in shared storage matching the manifest. Record each image or source group's
   origin, collection method, usage permission, and relationship to a video or
   image sequence. Collect representative camera and uploaded-video examples.
3. **Audit cleaning, boxes, and splits.** The raw manifest contains **12 exact
   duplicate groups (13 extra files)**. Review near-duplicates and related
   frames; keep each group in one split. Review missing/inaccurate EDS boxes and
   the **22 base-export images with no boxes** to distinguish intentional
   negatives from missed labels. Preserve the held-out test set.
4. **Prepare OCR ground truth.** Create EDS crops and verified transcriptions,
   with field or line labels where needed. Include a clear rule for unreadable,
   partial, and special-message displays.
5. **Version the remaining inputs.** Document the export version, split
   membership, preprocessing, and training-only augmentation settings. Obtain
   the reference CSV, record its source and fields, and check missing or
   inconsistent entries before matching experiments.
