# Task 3 — class, negative and split review

This packet audits the exact detector dataset used for the benchmark. It covers the 137 original training images plus 39 validation and 20 test images. The 274 training augmentations inherit their source annotations and are not counted as independent human-label decisions.

## Locked label contract

| Training index | COCO ID | Class | Decision rule |
|---:|---:|---|---|
| 0 | 1 | `front_eds` | Complete visible front- or side-facing EDS panel; rear displays excluded. |
| 1 | 3 | `front_eds_num` | Whole service-number group, including letter suffixes. |
| 2 | 4 | `front_eds_route` | Smaller/thinner intermediate road, stop or “via” text; meaning and typography, not position. |
| 3 | 2 | `front_eds_destination` | Larger/bolder final destination/terminal text and associated arrow/symbol. |

The unused COCO parent category `0: front-eds` has no boxes and is not a fifth foreground class. A true negative contains no eligible front or side EDS and therefore has zero COCO annotations—never a background-class box.

## Original-image inventory

| Split | Images | Zero-box | Panel | Number | Route | Destination |
|---|---:|---:|---:|---:|---:|---:|
| train | 137 | 16 | 161 | 141 | 120 | 126 |
| valid | 39 | 4 | 44 | 41 | 31 | 38 |
| test | 20 | 2 | 25 | 23 | 16 | 19 |

The full manifest-backed export also passes the existing automated readiness audit: 411/39/20 images, 1,644/154/83 boxes, and no exact/dHash cross-split match at the configured threshold. That does not prove semantic correctness or capture-session independence.

## Semantic candidates for joint review

These are heuristic flags, not automatic corrections. Inspect the image and annotation guide before accepting, relabeling or rejecting anything.

| # | Split | Image | Reason | Evidence | Human decision |
|---:|---|---|---|---|---|
| 1 | train | `Screenshot_2026-10-24-20-36-12-52_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.4bf33714370a1d5755de8af86aa3f4c5.jpg` | panel without content | [overlay](candidate_overlays/case_01.jpg) | Pending Jy/Brendan decision |
| 2 | train | `e1d7ff20-bus_36_jpg.rf.50931d4347074a989c99c26981eb4cfe.jpg` | panel without content | [overlay](candidate_overlays/case_02.jpg) | Pending Jy/Brendan decision |
| 3 | train | `Screenshot_2026-10-24-20-34-31-17_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.0c9ce34e0609d76a33d8948faf1ad1af.jpg` | panel without content | [overlay](candidate_overlays/case_03.jpg) | Pending Jy/Brendan decision |
| 4 | train | `c4072ca1-979_jpg.rf.e46a41d6f2ddcd74f98abfb0fd26f414.jpg` | panel without content | [overlay](candidate_overlays/case_04.jpg) | Pending Jy/Brendan decision |
| 5 | train | `3cf4b60f-bus_13_jpg.rf.1920692b5d8ddaccd09d59ff13130a55.jpg` | panel without content | [overlay](candidate_overlays/case_05.jpg) | Pending Jy/Brendan decision |
| 6 | train | `e89dca00-4ec58783-51_jpg.rf.43988cbd4784426fad460ef0275a94f8.jpg` | panel without content | [overlay](candidate_overlays/case_06.jpg) | Pending Jy/Brendan decision |
| 7 | train | `ccd80ac0-bus_3_jpg.rf.656e5f4a1a8ae4e715b4a75146d9cddd.jpg` | panel without content | [overlay](candidate_overlays/case_07.jpg) | Pending Jy/Brendan decision |
| 8 | train | `IMAGE_2026-10-23_21_55_36_jpg.rf.6b34543973a4300e76a0863d3af8916c.jpg` | panel without content | [overlay](candidate_overlays/case_08.jpg) | Pending Jy/Brendan decision |
| 9 | train | `IMG20261024204044_jpg.rf.1f4949e47a885dd0b8edbf5356241a43.jpg` | panel without content | [overlay](candidate_overlays/case_09.jpg) | Pending Jy/Brendan decision |
| 10 | train | `209ac893-6c0f00ef-14_jpg.rf.d7caaf301e064d352d2523c0411f5c71.jpg` | panel without content | [overlay](candidate_overlays/case_10.jpg) | Pending Jy/Brendan decision |
| 11 | train | `Screenshot_2026-10-24-20-36-01-26_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.bf0c2e35ae07633bbe888410476aa9d4.jpg` | panel without content | [overlay](candidate_overlays/case_11.jpg) | Pending Jy/Brendan decision |
| 12 | train | `Screenshot_2026-10-24-20-35-26-38_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.c77a4621b99c72961515489233fc3725.jpg` | panel without content | [overlay](candidate_overlays/case_12.jpg) | Pending Jy/Brendan decision |
| 13 | valid | `e273f0c9-8d3c1a80-132_jpg.rf.1fd6f21632e707a1913f6e07d8b68d6c.jpg` | panel without content | [overlay](candidate_overlays/case_13.jpg) | Pending Jy/Brendan decision |
| 14 | test | `IMAGE_2026-10-23_21_55_15_jpg.rf.c10c50d17372d129eb54404b81fa049d.jpg` | panel without content | [overlay](candidate_overlays/case_14.jpg) | Pending Jy/Brendan decision |
| 15 | test | `Screenshot_2026-10-24-20-32-06-12_f9ee0578fe1cc94de7482bd41accb329_jpg.rf.1804c20abcac5a3caf5ffcbae15a6425.jpg` | panel without content | [overlay](candidate_overlays/case_15.jpg) | Pending Jy/Brendan decision |

Contact sheet: [semantic_candidates.jpg](semantic_candidates.jpg)

## Negative review

There are 22 original zero-box images: 16 train, 4 validation and 2 test. Review every image on [negative_contact_sheet.jpg](negative_contact_sheet.jpg) against this rule: rear-only EDS, unrelated signs and scenes without an eligible visible front/side EDS stay negative; any visible eligible front/side panel requires boxes. The COCO export cannot prove these were explicitly marked Null in the annotation platform.

## Capture/source split isolation

The following timestamp-derived filename groups span more than one split. This is a conservative provenance warning: the filenames suggest the same minute/session, but only the original source/recording records can confirm whether they are frames from one capture.

| Inferred group | Splits | Images | Decision |
|---|---|---:|---|
| `image-minute:image_2026-10-23_21_55` | test, train, valid | 11 | Pending provenance confirmation |
| `image-minute:image_2026-10-23_21_56` | test, train, valid | 3 | Pending provenance confirmation |
| `image-minute:image_2026-10-23_22_00` | train, valid | 2 | Pending provenance confirmation |
| `img-minute:img202610221159` | train, valid | 2 | Pending provenance confirmation |
| `img-minute:img202610242037` | train, valid | 2 | Pending provenance confirmation |
| `img-minute:img202610242042` | train, valid | 2 | Pending provenance confirmation |
| `img-minute:img202610242044` | test, train | 3 | Pending provenance confirmation |
| `screenshot-minute:screenshot_2026-10-24-20-30` | test, train, valid | 4 | Pending provenance confirmation |
| `screenshot-minute:screenshot_2026-10-24-20-31` | test, train, valid | 10 | Pending provenance confirmation |
| `screenshot-minute:screenshot_2026-10-24-20-32` | test, train, valid | 4 | Pending provenance confirmation |
| `screenshot-minute:screenshot_2026-10-24-20-33` | train, valid | 4 | Pending provenance confirmation |
| `screenshot-minute:screenshot_2026-10-24-20-35` | test, train | 3 | Pending provenance confirmation |

The current repository has hashes and augmentation lineage but no authoritative capture/recording IDs or source-permission register. Therefore Task 3 cannot honestly certify split isolation or usage permission yet.

## Approval checklist for Brendan and Jy

- [ ] Confirm all four class definitions and the COCO-to-training mapping above.
- [ ] Decide every semantic candidate row; record keep/relabel/add/remove and reviewer initials.
- [ ] Confirm every original zero-box image is a valid negative and was explicitly accepted as Null, if platform history is available.
- [ ] Confirm whether each inferred cross-split timestamp group belongs to one recording/capture. If yes, rebuild a grouped split before the next benchmark; do not silently move only selected frames.
- [ ] Add source owner/origin and usage permission for each capture group or source collection.
- [ ] If annotations or splits change, publish a new versioned dataset/manifest and rerun all three models; preserve the current baseline as historical evidence.

No dataset labels or split assignments were changed by this audit.
