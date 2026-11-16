# OCR text-label dataset — 16 November 2026

`labels.csv` holds one row per crop, giving the text visible in that crop. It
covers train, valid and test. This is not Brendan's crop/box dataset.

The crop images are not in git. `crop` paths are relative to
`.runtime/ocr-text-dataset-20261116/`. Rebuild that folder with
`scripts/build_ocr_text_dataset.py`; every row carries `crop_sha256` so the
images can be verified.

| Split | Crops | Scorable | Label source | Human check |
| --- | ---: | ---: | --- | --- |
| train | 387 annotation | 387 | Codex, kept only where all 3 augmented copies got the same text | 50-crop spot-check pending |
| valid | 150 annotation + 108 detector | 67 + 42 | 185 typed by the team, 73 Codex | in progress |
| test | 118 annotation | 60 | Claude AI proposals, read from the crop pixels only (no OCR engine output) | pending (`test_confirm` page) |

## Columns

- `text`: the visible text. Case and punctuation are kept, a real line break is kept as a newline, and `[UNK]` marks an unreadable span.
- `legibility`: full / partial / illegible.
- `label_source`: `human_typed_by_team`, `codex_ai`, `codex_ai_3copy_consensus`, or `claude_ai_proposal`.
- `scoring_eligible`: True only when legibility is full, the text has no `[UNK]`, the field is present, and the crop is not a challenge-only case. For validation this matches the repo scorer row for row.
- `exclusion_reason`: why a row is not scored.

## Rules

- Never use test for training, tuning or matching cutoffs.
- Test detector crops do not exist yet. They need `yolo11s-best.pt` and the full v4 photos from Brendan.
- Validation labels are refreshed from the human review once it finishes.
- Final test labels come from `scripts/finalize_test_labels.py` after a human confirms each row.
