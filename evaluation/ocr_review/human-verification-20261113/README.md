# Human verification files

Start with [the instructions](../../../docs/OCR_HUMAN_VERIFICATION.md).

- Open `training.html` to inspect the 1,917 training crops without AI text.
- Copy `training.decisions.template.csv` to a reviewer-named file and fill only
  inspected rows. All human decisions/identity/date fields are currently blank.
- For validation, use `validation.html` and `validation.decisions.template.csv`
  (271 crops). Earlier flagged IDs still require adjudication.
- `training.source.csv` and `validation.source.csv` freeze prior AI proposals,
  immutable identities and user-approved challenge exclusions. Do not edit them:
  the decision templates bind their hashes. Review images before viewing AI text.
- `challenge_register.csv` lists 35 training and 26 validation cases excluded
  from primary field scoring/training. Field ownership is still unresolved.
- `audit.json` records counts and original-source hashes. No row is training- or
  scoring-ready. Source-scene grouping and legacy quarantine remain unresolved.

Generated with `scripts/prepare_ocr_verification.py` from the 12 November AI
follow-up files. The HTML pages link existing byte-verified local crops; they
must be used within this repository/cache layout and do not save edits.
No test crops are included.
