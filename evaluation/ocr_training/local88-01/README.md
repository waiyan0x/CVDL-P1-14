# Local 88-photo OCR training preparation

Status: provisional, **not training-ready**. Sources and existing A/P validation crops are unchanged.

This export uses the legacy mapping in `data/classes.txt`, not the v4 class order. Source image paths are relative to the repository root; crop paths are relative to this directory.

Exported 179 tight PNG crops: {'front_eds_num': 90, 'front_eds_destination': 89}. Source-photo dispositions: {'candidate_pending_review': 62, 'excluded_holdout_link': 22, 'excluded_duplicate': 4}. Crop dispositions: {'candidate_pending_review': 123, 'excluded_holdout_link': 48, 'excluded_duplicate': 8}.

`transcriptions.template.csv` preserves the requested ten columns then appends provenance, review and training-disposition columns. `source_review.csv` lists all 88 photos. `audit.json` records hashes, split members, conservative group links and exclusions. `review/candidate_*.png` shows only nonexcluded candidates, with neutral T IDs.

The exported crops include quarantined material for traceability. Never train by recursively loading the `crops/` directory. Select explicit eligible manifest rows only. Rows marked excluded_holdout_link or excluded_duplicate must remain out of training.

File/pixel duplicates are deterministic links. Source-name and perceptual links are conservative candidates, not verified scene identities. Candidate links crossing validation/test boundaries are quarantined; duplicates within training retain one candidate copy. No link does not prove independence. Review remaining related scenes/bursts before training. Full v4 test sources are unavailable and were not inspected.

The legacy destination boxes often contain both a road line and a destination line. Their field meaning must be reviewed and, when needed, split into separately annotated boxes. There is no legacy route-text class: no route crops have been invented. New route geometry must come from visible training-photo content. Keep panel/bus-front boxes as context, not text targets.

Next: inspect candidate source groups and native crops; add/correct route and destination geometry; transcribe visible text using `docs/OCR_TRANSCRIPTION_RULES.md`; validate labels. Assistant-authored labels must identify reviewer_type=AI and must not claim human review. Use the actual review date, not the export date. Blank cells remain unannotated. Partial/illegible text and [UNK] syntax are not literal whole-string training targets.

Reproduce from the repository root with a new output path:

```sh
.venv/bin/python scripts/prepare_local_ocr_training.py --output evaluation/ocr_training/local88-02
```
