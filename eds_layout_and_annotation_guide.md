# Bus EDS Layouts and Annotation Guide

## 1. Objective and scope

Annotate **electronic destination signs (EDS) on the front and sides of buses**, together with the service numbers, destination text, and route details inside them.

**Latest agreed scope:**
- **Front-facing EDS:** include.
- **Side-facing EDS:** include, including small number-only displays beside entrance doors.
- **Rear-facing EDS:** exclude.
- **Other objects:** exclude—bus bodies, registration plates, operator logos, advertisements, bus-stop information screens, and unrelated text.

Despite its name, **`front_eds` now covers both front and side EDS panels**. Do not introduce separate side-EDS or background classes.

---

## 2. Final class definitions

Use exactly these four class names.

| Intended index* | Class | What to box |
|---:|---|---|
| 0 | `front_eds` | The complete visible front- or side-facing electronic display panel, enclosing its number and text areas. |
| 1 | `front_eds_num` | The complete service-number group, such as `132`, `991`, or an alphanumeric service identifier. |
| 2 | `front_eds_route` | Smaller, thinner text showing intermediate roads, street names, or “via” route details. |
| 3 | `front_eds_destination` | Larger, extra-bold text identifying the final destination, terminal, or interchange, including its associated arrow or symbol. |

\*These are your **requested index assignments**, not a verified export mapping. Before training, inspect the COCO JSON `categories` entries and their IDs. Do not assume export order matches this table.

**Do not use:** `front_eds_bus_destination`, `front_eds_bus_num`, or `front_eds_bus_route`.

---

## 3. Identify content by typography and meaning—not fixed position

Different operators and display configurations place route and destination text differently.

### Destination: `front_eds_destination`
Primary cues:
- Larger, extra-bold, high-density matrix lettering.
- Identifies the final destination.

Supporting cues:
- Names ending in `INT` or `TER`.
- Associated arrow `>`, loop symbol `↺`, or `EXP` tag.

Include the associated symbol in the text box. These cues are **supporting evidence**, not automatic rules.

### Route details: `front_eds_route`
Primary cues:
- Smaller, thinner, compressed matrix lettering.
- Describes intermediate roads or stops rather than the final destination.

Supporting cues:
- `via`.
- Road or street names.
- References such as `MRT`, `LRT`, `Interchange`, or `Hosp`.

**Neither keywords nor top/bottom placement alone determine the class.** For example, an interchange may be the final destination or an intermediate location.

---

## 4. Layout reference

These diagrams are schematic, not placement templates.

### A. SBS Transit example confirmed in our discussion

```text
┌──────────────────────────────────────┐
│ STEVENS RD                      132  │
│ >BUKIT MERAH INT                      │
└──────────────────────────────────────┘
```

| Element | Label |
|---|---|
| Entire display panel | `front_eds` |
| `132` | `front_eds_num` |
| `STEVENS RD`—thinner top line | `front_eds_route` |
| `>BUKIT MERAH INT`—bold bottom line | `front_eds_destination` |

**Do not change both lines to destination text.** This example demonstrates why a universal “route underneath destination” rule is incorrect.

### B. Destination above route details

```text
┌──────────────────────────────────────┐
│ FINAL DESTINATION               123  │
│ via Intermediate Road                │
└──────────────────────────────────────┘
```

Box the bold final destination as `front_eds_destination` and the thinner intermediate-road line as `front_eds_route`.

### C. Large destination occupying the left side

```text
┌──────────────────────────────────────┐
│ LARGE DESTINATION               123  │
│ TEXT                                 │
└──────────────────────────────────────┘
```

Annotate the panel, number, and destination text. **Do not invent a route box if route details are absent.**

### D. Small side-facing, number-only display

```text
┌─────────┐
│   123   │
└─────────┘
```

Create:
1. A `front_eds` box enclosing the visible display panel.
2. A `front_eds_num` box tightly enclosing the number.

No destination or route box is required when those contents are absent.

---

## 5. Bounding-box instructions

### Display panels
- Draw **one enclosing `front_eds` box per visible eligible panel**.
- Include the visible display area, not the surrounding windshield or bus body.
- Check small, angled side displays beside or above entrance doors.
- A panel showing only a number still receives a panel box.

### Content
- Box the **whole number group**, not individual digits.
- Box each distinct route or destination text line as a group—not individual letters or words.
- Include associated destination arrows or symbols.
- Keep text boxes tight, with minimal surrounding background and no clipped visible characters.
- Content boxes should lie inside their corresponding panel box, allowing for the panel’s axis-aligned bounding rectangle.

### Multiple signs and partial visibility
- Label **every visible front or side EDS**, including those on other buses in the image.
- For partially occluded signs, use visible evidence; do not invent hidden panel boundaries or unreadable content.
- If the panel is identifiable but its content cannot be classified reliably, label the panel and flag the uncertain content for review.
- Annotate only what is visible in the still image—not text presumed to appear later in a scrolling message.

**Four classes do not mean exactly four boxes per image.** Some images have multiple panels or text lines; others lack particular content types.

---

## 6. Negative samples

Negative images contain **no eligible front or side EDS targets**.

Examples can include:
- Bus-stop arrival-information screens.
- Unrelated signs or vehicles.
- Rear-only bus views, since rear EDS remains excluded.

For each negative image:
1. Draw **zero boxes**.
2. Explicitly mark it **Null / no objects** using **∅** in the annotation editor.
3. Save it and move it through the applicable Dataset acceptance process.
4. Do **not** create a background class.

An empty, unannotated image is not the same workflow state as an explicitly marked Null image.

In **COCO JSON**, negative images belong in `images`, with **no corresponding entries in `annotations`**.

---

## 7. Auto Label configuration and process

Use **Gemini 4 Argon** with the following prompt-to-class mapping. These prompts incorporate the final front-and-side scope and the removal of fixed vertical-layout assumptions.

| Class | Auto Label prompt |
|---|---|
| `front_eds` | Every electronic destination sign panel on the FRONT and SIDE of every bus. Include the large front panel AND small narrow side panels beside or above entrance doors, even when they show only a service number. Box each panel separately, enclosing its number and text areas. Do not omit small angled side displays. Exclude rear-facing displays. |
| `front_eds_num` | Every glowing orange or green bus service number group inside FRONT and SIDE electronic destination signs. Include numbers on small narrow angled side displays beside entrance doors, as well as the large front number. Box each number group separately. Exclude rear-facing displays. |
| `front_eds_destination` | Large extra-bold text showing the final bus terminal name or interchange station inside FRONT or SIDE electronic destination signs, sometimes preceded by >. Include the associated arrow. Determine destination by typography and meaning, not fixed top/bottom position. Exclude rear-facing displays. |
| `front_eds_route` | Smaller thinner text showing intermediate roads, via route details, or street names inside FRONT or SIDE electronic destination signs. Text may be above or below the destination depending on operator layout. Exclude rear-facing displays. |

### Labeling sequence
1. Separate positive images from declared negative samples.
2. Configure only the four correct classes.
3. Test the exact Auto Label prompts on representative images.
4. Inspect panel coverage, text-box placement, and route/destination distinctions.
5. Obtain the job estimate and run the requested batch.
6. Review and correct the resulting annotations.
7. Approve the reviewed positives; explicitly mark negatives Null.
8. Add the eligible images to Dataset.

**Important:** the final prompts above were supplied as an explicit job configuration. Do not assume the Project’s saved class descriptions automatically contain them.

---

## 8. Quality-control checklist

Before accepting an image, check:

- [ ] Every visible front and side EDS has an enclosing `front_eds` box.
- [ ] Small side panels were not missed.
- [ ] Number, route, and destination boxes use only the four correct names.
- [ ] Route and destination were distinguished by typography and meaning, not position alone.
- [ ] Destination arrows and associated symbols are included.
- [ ] No duplicate, clipped, or unnecessarily loose boxes remain.
- [ ] Rear signs and unrelated text are unlabelled.
- [ ] True negative images are explicitly Null, with zero boxes.

The tested sample demonstrated the corrected side-display behavior; **it did not establish accuracy across every image**.

---

## 9. Split and augmentation settings

Your latest verified Dataset contained **199 images**:

| Split | Images |
|---|---:|
| Train | 140 |
| Validation | 39 |
| Test | 20 |

Keep near-duplicate photos or frames from the same recording in the **same split** to reduce evaluation leakage.

### Conservative augmentation recipe

| Setting | Value |
|---|---:|
| Brightness | ±10% |
| Rotation | ±3° |
| Noise | 1% |
| Blur | 1 px |
| Augmentation multiplier | 3×, including originals |
| Other transformations | Off initially |

Apply augmentation **only to training images**. These are starting recommendations, not confirmed saved settings. Inspect combined effects and disable blur or noise if thin route text becomes indistinguishable.

Avoid flips, 90° rotations, strong distortions, and transformations that erase or clip labeled text. Keep negative images free of boxes after augmentation.

---

## 10. COCO JSON export checks

Before downloading:
- Include the intended positive **and Null** images.
- If generating a version, leave **Filter Null disabled** to retain negatives.
- Verify the four class names and actual category IDs.
- Check that exported boxes use COCO’s `[x, y, width, height]` format.
- Confirm that negative images have no annotation entries.
- Verify exported image counts against the selected source or version.

The completed relabeling job reported **795 generated boxes** for the 178-positive-image job, and you subsequently approved those images. That total is a processing result—not a requirement that future batches match it.