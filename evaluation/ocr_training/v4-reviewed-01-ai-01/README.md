# V4 training crops — AI review, 9 November 2026

Status: **AI first pass complete; human verification and source-scene grouping unresolved. No training-ready rows.**

## Evidence and scope

| Classification | Finding | Evidence |
| --- | --- | --- |
| Observed source artifact | Supplied train-only manifest: 735 source images, 245 named families, 2,754 annotation crops; 1,917 text crops and 837 panel/context crops. | `source_manifest.json`, `source_transcriptions_template.csv`; hashes in `intake_audit.json` |
| Observed AI review | Every text crop was individually inspected, with nearest-neighbour enlargement. 710 full, 508 partial, 699 illegible. These are annotation coverage counts. | `transcriptions.review.csv`, `review_audit.json`, `visual_review_log.json` |
| Observed AI review | 245 named families were inventoried; first supplied panel per variant was compared where available. Name/exact-source-hash links produce 244 training groups. The 147 zero-box source records cannot be visually certified as negatives from this crop-only package. | `source_review.csv`, `source_groups.json`, `source_audit.json` §method |
| Observed metadata/candidate links | 75 training variants share names with legacy validation/test sources. Nine additional variants link to previously quarantined legacy groups. All 84 source variants / 28 groups / 288 text crops are conservatively quarantined. | `source_audit.json` §§legacy_holdout_direct_links / legacy_holdout_matches |
| Not established | These historical links do not prove leakage in the new v4 train/valid/test split. No related-scene independence or human ground truth is claimed. | `source_audit.json` §limitations |
| Observed limitation | Full dataset ZIP was missing when this task started and remained unavailable. Full photos and complete v4 test grouping could not be reviewed. | `intake_audit.json`; supplied train manifest contains producer Windows paths, not available local originals |
| Project decision | Preserve visible text, case, punctuation, abbreviations and actual line breaks; use `[UNK]` for unresolved spans; no guessed completion or literal `[UNK]` training. | `docs/OCR_TRANSCRIPTION_RULES.md` §Transcription conventions; `docs/OCR_ANNOTATION_PACKAGE.md` §Text states and scoring policy |
| Not stated | Coursework requirements/weights, a closed character alphabet, human verification, and approval to train. | No additional brief/rubric or human review supplied in this task |

## Files to use

- `transcriptions.review.csv`: all 1,917 rows, preserving original crop paths, source identities, labels, annotation IDs and order; added crop/source hashes, geometry, neutral T IDs, AI review metadata, group/field flags and training disposition.
- `human_review_queue.csv`: the same rows, ordered by field/holdout issues, then full text verification, then partial/illegible review.
- `full_text.ai-candidates.csv`: **537 provisional human-verification candidates**, filtered to full text without a known legacy-holdout quarantine or explicit field-resolution flag. They are **not training data**: `training_ready=false`, human review pending, source grouping unresolved.
- `source_review.csv`: all 735 source records, including sources without annotation boxes, with group dispositions and source sheet references.
- `source_groups.json` and `source_audit.json`: candidate family links, historical holdout links, review boundaries and limitations. Valid-only groups retained from the existing manifest are metadata references, not newly reviewed validation groups.
- `source_*`: byte-preserved original README, manifest and blank CSV. The archive README is source documentation, not a new user instruction. `ground_truth/` names annotation geometry, not verified text.
- `transcriptions.first-pass.csv` and `reinspection_changes.json`: initial AI labels and transparent corrections. Use `transcriptions.review.csv` as the current version. Reinspection was by the same AI, not an independent second reviewer.
- `review_audit.json`: structural checks, final counts and hashes. `artifact_checksums.json` covers this package and the review tooling. `visual_review_log.json` identifies the contact sheets actually inspected.

## Crop and sheet locations

Original crop paths resolve against:

`/Users/tanyilin/Downloads/CVDL-P1-14/.cache/ocr_training/v4-reviewed-01-ai-01/source/`

The CSV also includes `crop_local_path` for each crop. Original PNG bytes were extracted from `v4-reviewed-01-training.zip`; no source or crop was edited. The cache contains all 2,754 supplied crops, including context crops.

Review images are in:

`/Users/tanyilin/Downloads/CVDL-P1-14/.cache/ocr_training/v4-reviewed-01-ai-01/review/`

`crops_01.png`–`crops_40.png` cover every text crop. `sources_01.png`–`sources_11.png` compare the first supplied panel per source variant. `letters_01.png`–`letters_09.png` and `target_01.png`–`target_03.png` support same-AI reinspection. Labels were not generated from an OCR engine, route CSV, filenames, another frame, or generative enhancement. Parent panels were used to assess field context; uncertain crop text remains unresolved.

## Class and review boundaries

Keep `front_eds_num`, `front_eds_destination` and `front_eds_route` separate. Supplied crop-manifest class IDs are 0=panel, 1=number, 2=route, 3=destination; these are not the full COCO category IDs. No class conversion or application integration was performed. Some destination boxes contain clipped route lines, and some fields contain operational messages. Explicit field flags require adjudication; no class was silently changed.

`review_status=reviewed` here means **visually reviewed by Codex (AI)**, as recorded in `reviewer_type`; it is not a human attestation. Six crops with unresolved field presence use `needs_resolution` and no asserted field status. Every row has `human_verification_status=pending`, `group_review_status=needs_resolution` and `training_ready=false`. Partial/illegible rows remain excluded from literal whole-string training. Do not recursively train from the crop directory or use the candidate CSV as approved truth.

## Checks and remaining review

Run from the repository root:

```sh
.venv/bin/python scripts/audit_ocr_training_review.py
```

This verifies the supplied archive SHA256/CRC and byte-preserved metadata, every text crop's hash and decoded dimensions, immutable row identity/order, source/geometry joins, NFC/newline/`[UNK]` conventions, AI provenance and training gates. Source hashes are producer attestations until full photos are available. No exact source SHA256 overlaps the existing 53-image v4 validation manifest. An exact/RGB and narrow perceptual comparison of all 837 training panels against the 64 existing validation panels and different training families found no candidate pairs; this limited comparison does not establish scene independence. No test image was decoded/viewed in this task.

Next: human-verify text and field identity; restore the full dataset path and resolve scene/burst groups across relevant held-out sets; adjudicate historical split links; then create an explicitly approved eligible training manifest. Keep all variants of a source/related-scene group together. No OCR accuracy, model selection, training, reference matching, application changes or checkpoint replacement was performed.
