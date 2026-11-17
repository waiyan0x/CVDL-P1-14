# Training-label spot-check, 17 November 2026

## Final review (v3), 17 November 2026 — current result

cody settled the spot-check in a third export. Compared with v2, S004 is now
`S43` (full), S018 `RIVER VALLEY DR / JALAN KAYU` (full) and S029
`[UNK] Tomlinson Road` (partial). Final files: `spotcheck_export.v3.final.raw.csv`
(the export as received), `comparison.v3.final.csv`, `summary.v3.final.json`.
v1 and v2 files are kept for the record. **No training label was changed.**

| Category | Crops | Meaning |
| --- | ---: | --- |
| match | 22 | Same text after normalisation. |
| label_text_ok_extra_cut_off_part | 19 | Same text plus a cut-off part marked `[UNK]` (`80` vs `80 [UNK]`). |
| human_reads_only_part_consistent | 3 | The human reads part of the label; that part agrees (S003, S014, S043). |
| human_illegible | 2 | The human cannot read the crop (S012, S031). |
| conflicting_reading | 4 | S018, S041, S046, S050. |

- **Text:** the human reading agrees with the label on 41/50 (82%, Wilson 95%
  69–90%) once cut-off parts are ignored; exact agreement is 22/50.
- **Conflicts:** S018 (label `RIVERVALE DR`, human `RIVER VALLEY DR`; a Claude
  visual check reads RIVERVALE). S041, S046 and S050 are too blurred to settle.
  Recorded as disagreements; neither reading overrides the other.
- **Legibility:** all 387 training labels have `legibility=full` in the
  fine-tuning bundle's `labels.csv` (selection required it). The human rated
  27/50 of the sampled crops (54%, 95% CI 40–67%) partial or illegible.
- **Consequence:** training-split scores against these labels are
  **diagnostic only**. Labels and fine-tuned models are unchanged; validation
  and test use human-verified labels only.

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
