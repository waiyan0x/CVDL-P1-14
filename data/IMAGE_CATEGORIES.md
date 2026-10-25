# Image categories for the data-preparation set

This is a presentation-friendly description of the **212 raw images** in the
2026-10-24 snapshot. I reviewed the raw images from commit `9b15447`; the
current branch keeps only their paths and checksums in
`data/manifests/2026-10-24.csv`, so the image files are not in a fresh checkout.
Categories overlap: one photo can be both distant, at night, and partly blocked.
The 898 manifest files also include labelled and augmented exports, so they
should not be presented as 898 distinct photos.

| Broad category | Subsets visible in the images | Why we included them |
| --- | --- | --- |
| **Viewing angle and display location** | Straight-on front; three-quarter front; side; rear; bus partly outside the frame; front EDS and side/rear displays where visible. | The display changes shape and position with perspective. Side and rear views help distinguish the front EDS from other displays or bus markings. |
| **Distance and image quality** | Close, readable buses; small or distant buses; soft focus, motion blur, low resolution, and cropped displays. | Tests whether the system still finds the bus and knows when EDS text is too small or unclear to read reliably. |
| **Lighting and environment** | Bright sun, shade, backlighting or windshield glare; dusk and night with bright LEDs/headlights; sheltered interchanges and bus stops; some wet-road or rainy-looking scenes. | EDS contrast and reflections vary substantially across real operating conditions. |
| **EDS text and layout** | Route number with destination; number and destination without a detailed route or “via” line; one-line and multi-line destination text; number placed at different positions; different LED brightness, colour, and spacing. | Prevents the reader from assuming one fixed text position or format. Covers short and long messages on different bus and display designs. |
| **Special display messages** | Non-standard service text such as **“Off Service”**, express or limited-stop wording, and other destination/status messages. | Helps the model avoid forcing every lit display into an ordinary route-number-and-destination pattern. |
| **Bus and operator variety** | Single- and double-deck buses; different front shapes, display housings, and liveries, including SBS Transit, SMRT, Tower Transit and SG Bus-branded vehicles. | Checks that detection generalises across bus models and operators. Display hardware and layout can vary even within one operator. |
| **Crowded or obstructed scenes** | Multiple buses in one image; buses behind other buses; people, poles, shelters, trees, and vehicles crossing the bus or EDS; busy interchange backgrounds. | Forces the system to associate each display with the correct bus and handle partly hidden text. |
| **Distracting text and hard negatives** | Bus-stop/service signs, advertisements, vehicle branding, side or rear text, and scenes with no readable front EDS. | Tests whether the system reads the actual front display instead of nearby unrelated text or inventing a reading when none is visible. |

For a slide, the categories can be summarised as **viewpoint, scale/clarity,
lighting, display content/layout, bus variety, and scene complexity**. The raw
set also contains screenshots and visibly watermarked images alongside camera
photos; describe these as *collected images* unless individual sources have
been verified as team-taken photos. These are qualitative coverage categories,
not counts or mutually exclusive labels.

The suggested **“In Training”** message belongs under special display
messages, but I could not confidently verify that exact wording in this raw
snapshot. Add it as a confirmed example once its source image is identified.
