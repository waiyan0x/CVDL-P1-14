# Training-label spot-check, 17 November 2026

## Revised review (v2), 17 November 2026 — current result

cody re-exported the spot-check with 11 rows revised (mostly adding a leading
`[UNK]` and reading more text). The v2 files supersede the v1 result below:
`spotcheck_export.v2.raw.csv` (the export as received), `comparison.v2.csv`,
`summary.v2.json`. **No training label was changed.**

| Category | Crops | Meaning |
| --- | ---: | --- |
| match | 21 | Same text after normalisation. |
| label_text_ok_extra_cut_off_part | 18 | Same text plus a cut-off part marked `[UNK]` (`80` vs `80 [UNK]`). |
| human_reads_only_part_consistent | 3 | The human reads part of the label; that part agrees (S003, S014, S043). |
| human_illegible | 2 | The human cannot read the crop (S012, S031). |
| conflicting_reading | 6 | S004, S018, S029, S041, S046, S050. |

- **Text:** the human reading agrees with the label on 39/50 (78%, Wilson 95%
  65–87%) once cut-off parts are ignored; exact agreement is 21/50.
- **Conflicts:** for S004 (`S43`), S018 (`RIVERVALE DR`) and S029
  (`Tomlinson Road`) a Claude visual check reads the crop as the label says;
  the human reading differs. S041, S046 and S050 are too blurred to settle.
  These are recorded as disagreements; neither reading overrides the other.
- **Legibility:** every training label says `full`, but the human rated 28/50
  (56%, 95% CI 42–69%) partial or illegible.
- **Consequence:** training-split scores computed against these labels are
  **diagnostic only**, not official results. Labels and the fine-tuned models
  are unchanged; validation and test use human-verified labels only.

## v1 result (superseded)

A random sample of 50 of the 387 training labels (Codex, 3-copy consensus) was
re-read blind by cody. **No training label was changed.** `labels.csv` and the
fine-tuning bundle are unchanged, so all three models still train on the same labels.

## Files

- `spotcheck_export.csv`: the reviewer's export with the image data replaced by the crop path and SHA-256. All 50 hashes match `labels.csv`.
- `comparison.csv`: one row per crop, with the label, the human reading and a category.
- `summary.json`: counts and Wilson 95% intervals.

## Result

| Category | Crops | Meaning |
| --- | ---: | --- |
| match | 26 | Same text after normalisation. |
| label_correct_reviewer_misread | 3 | S004 `S43`, S018 `RIVERVALE DR / JALAN KAYU`, S029 `Tomlinson Road`. The crop clearly shows the label text (Claude visual check). |
| label_text_ok_extra_cut_off_part | 10 | Same text, but the human sees an extra cut-off character (`80` vs `80 [UNK]`). |
| label_not_verifiable_by_eye | 9 | The human cannot read part or all of what the label states. The labels look consistent with the blurred shapes but can't be confirmed. |
| conflicting_reading | 2 | S046 (`67` vs `167 [UNK]`) and S050 (`11` vs `77 [UNK]`). Unresolved. |

- **Text:** on the 29 crops the human could read in full, the label text was right on all 29 after the visual check. Wrong-text rate is 0/29 (Wilson 95% upper bound about 12%). No label is confirmed wrong.
- **Legibility:** every training label says `full`, but the human rated 21/50 (42%, 95% CI 29–56%) as partial or illegible. Codex reads degraded and cut-off crops more generously than a human reviewer.

## Decision

Labels are kept as they are. No retraining is needed for this spot-check: no label text
was shown to be wrong, and the main finding is a legibility-standard difference that
would need a full review of all 387 crops to act on consistently. Report it as a
training-label limitation. Validation and test scores do not depend on these labels;
they use human-verified labels only.
