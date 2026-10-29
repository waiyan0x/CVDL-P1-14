# Representative dataset samples

Reviewed on 2026-10-29 against all 212 top-level images in `data/raw/2026-10-24/`.
This folder contains **12 curated sample images**: eight unchanged raw-image copies
and four isolated augmentation previews. Four existing app presentation images
(`01-daylight-329.jpg`, `02-night-965.jpg`, `03-angle-181.jpg`, `04-stop-133.jpg`)
are also retained for the reader UI, giving **16 image files** in this folder. These are presentation/reference assets,
not new training records. The raw, labelled and training datasets are unchanged.

## Image coverage categories

One representative per broad category from [the coverage guide](../IMAGE_CATEGORIES.md).
Categories overlap; one photo cannot demonstrate every subset in a row. The
variety example shows one bus model/operator, with other examples providing contrast.

| Category | Sample | Selection rationale |
| --- | --- | --- |
| Viewing angle and display location | [01-viewing-angle.jpg](01-viewing-angle.jpg) | Three-quarter view of a single-deck bus, showing front and side displays on separate faces. |
| Distance and image quality | [02-distance-quality.jpg](02-distance-quality.jpg) | Distant bus at a roadside stop; the EDS occupies very few pixels and cannot be read reliably. |
| Lighting and environment | [03-lighting.jpg](03-lighting.jpg) | Night scene with a bright amber EDS, lit interior and headlight against dark surroundings. |
| EDS text and layout | [04-eds-layout.jpg](04-eds-layout.jpg) | Route 145 on the right of a wide front panel, with stacked destination/route text to the left. |
| Special display messages | [05-special-message.jpg](05-special-message.jpg) | OFF SERVICE fills the front display instead of an ordinary route number and destination. |
| Bus and operator variety | [06-bus-variety.jpg](06-bus-variety.jpg) | SBS Transit double-decker with purple/white livery and a tall, distinctive front; complements the single-deck examples. |
| Crowded or obstructed scenes | [07-crowded.jpg](07-crowded.jpg) | Several overlapping buses in an interchange; the nearer buses partly hide those behind. |
| Distracting text and hard negatives | [08-hard-negative.jpg](08-hard-negative.jpg) | Sheltered interchange berth/service sign with route numbers; this text is not a bus EDS. |

## Data augmentation examples

All four previews use the unchanged [EDS-layout sample](04-eds-layout.jpg) as
their before image. Each preview enables only the named effect through
`src/data_preparation/augmentation.py::augment_sample`, using the existing
`visualization.py::augmentation_cases` settings and seed 42.

| Augmentation | Sample | Applied value |
| --- | --- | --- |
| Brightness | [09-brightness-minus10.png](09-brightness-minus10.png) | factor 0.90 |
| Rotation | [10-rotation-plus3.png](10-rotation-plus3.png) | +3 degrees |
| Salt/pepper noise | [11-noise-1percent.png](11-noise-1percent.png) | 1% expected pixel rate |
| Gaussian blur | [12-blur-sigma1.png](12-blur-sigma1.png) | sigma 1 px |

Brightness covers a configured range of ±10%; the selected example uses −10%
(factor 0.90). Rotation covers ±3°; the example uses +3° and the pipeline's
grey padding to preserve the full scene. Noise is salt/pepper at a 1% expected
pixel rate (all RGB channels together), not Gaussian noise. Blur is Gaussian
sigma 1 px with the pipeline's kernel (up to 7 px). These are isolated effect
demonstrations, not four variants taken from the current combined training export.

Exact source paths, SHA-256 hashes, observations and augmentation settings are in
[manifest.json](manifest.json). [dataset_inventory.json](dataset_inventory.json)
records the verified counts and annotation hashes. Images are copied without
removing existing watermarks; usage permissions are not established by selection.
