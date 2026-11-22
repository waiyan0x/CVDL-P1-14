# Reference data

| File | What it is |
| --- | --- |
| `../bus_information.csv` | Original route list. Never edited. |
| `bus_information.cleaned.csv` | Same routes, one row per route, with `source_line` pointing back to the original. Built by `scripts/clean_bus_reference.py`. |
| `cleaning_report.json` | Every change, dropped row and flag, plus names that become identical after normalising and similar names kept distinct. |
| `abbreviations.csv` | Word and place short forms. Both OCR text and reference names are mapped to the `standard` column before fuzzy scoring. |

## Cleaning (formatting and obvious errors only; no services added)

- 2 exact duplicate rows dropped (307 and 307T, lines 394–395).
- Spelling: `Kent Ridge MRT dtation` → `Kent Ridge MRT station` (92B).
- Trailing spaces trimmed (LCS1, LCS2); curly apostrophe straightened (21); `851e`/`960e`/`963e` → upper case.
- Flagged and kept: 92B has a blank destination; 27 named or shuttle services (`CW1`, `Giant/IKEA Bedok`, …).
- Both directions of a route are separate rows and both are kept (e.g. 179A, 850E).
- Services seen on real displays but missing here (e.g. `147E`, `74E`, `350`) are **not** added; the
  matcher reports them as "unable to detect".
- Similar names are never merged (e.g. `Bedok North Avenue 3` vs `Bedok North Street 3`); see
  `similar_names_kept_distinct` in the report. Names that differ only by `Bus`, `(loop)` or spelling
  (`Ave`/`Avenue`) become one endpoint after normalising.
