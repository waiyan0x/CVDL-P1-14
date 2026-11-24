# Codi OCR label import

Reviewer supplied by user: **Codi**. Actual review date: **2026-11-07**.
Independent second review has not been attested. This import checks structure and conventions, not visual transcription correctness.

| Crop set | Field | Full | Partial | Illegible |
| --- | --- | ---: | ---: | ---: |
| annotation | service number | 34 | 9 | 17 |
| annotation | route text | 11 | 17 | 14 |
| annotation | destination | 15 | 19 | 21 |
| prediction | service number | 30 | 7 | 5 |
| prediction | route text | 12 | 22 | 3 |
| prediction | destination | 5 | 24 | 6 |

All 271 expected IDs are present without duplicates. Original text, quality, field labels and crop provenance are retained.
Source CSVs are preserved byte-for-byte in `raw/`. Five overflow note cells are rejoined and quoted in the imported files; no transcription is changed.

## Items to resolve

**77 distinct rows** need resolution or visual inspection. See `rows_to_resolve.csv` for text, issue and requested action. A row can have multiple issues.

- **partial_missing_unknown (36):** A009, A010, A014, A015, A019, A020, A035, A036, A045, A046, A058, A077, A086, A088, A089, A090, A091, A109, A117, A131, A132, A154, A155, P010, P011, P012, P018, P021, P022, P033, P034, P049, P062, P063, P065, P094
- **case_variant (3):** A117, A131, P094
- **illegible_has_readable_text (1):** A134
- **field_bleed (26):** P002, P003, P006, P009, P014, P024, P026, P027, P029, P037, P041, P043, P047, P048, P051, P064, P070, P071, P080, P083, P088, P089, P104, P106, P107, P108
- **no_text_state (1):** P005
- **field_mismatch (15):** P011, P018, P067, P068, P072, P082, P085, P086, P087, P097, P098, P100, P101, P105, P110
- **full_contains_unknown (1):** P100

Case variants are candidates for inspection, not proof of incorrect case. Do not auto-uppercase.
A partial label needs the actual unresolved span marked; do not guess its location or reclassify solely because the crop is blurred.
Keep field-bleed and field-mismatch observations separate from character recognition errors. Confirm the intended target before scoring; source classes must not be silently changed.

## Remaining scoring prerequisites

All 271 group IDs remain unassigned and group review is pending. The imports retain the original `valid` split, so there is no recorded train/test split conflict, but burst/scene leakage cannot be assessed or ruled out.
Predicted-crop correspondence review is also pending. No row is declared scoring-ready and no OCR accuracy has been measured.
No complete field-specific regex or closed alphabet has been established. Checks cover the declared legibility/whitespace conventions, not an invented service/destination grammar.
The earlier `human_review/annotation_jun_yong.draft.csv` is a historical partial submission and is not merged into this new Codi submission. The source templates and preparation audit are unchanged.
