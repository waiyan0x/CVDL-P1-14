# Inference matching handoff

Prepared 16 November 2026 for the reference-matching owner.

**You can start matching development now.** OCR outputs, pretrained weights and
comparison tables are supplied. Reference matching has not been run in this
handoff. Photo grouping remains pending, so final independent accuracy is still
pending. All package paths below are relative to the unzipped handoff folder.

## 1. Open these files first

| File | What you use it for |
| --- | --- |
| `START_HERE.txt` | Latest status and package entry point |
| `matching_inputs.jsonl` | Saved raw/normalised OCR and status flags; main matcher input |
| `reference/bus_information.csv` | Candidate services/endpoints to match against |
| `reference/audit.json` | Reference blanks, duplicates and source hash |
| `matching_outputs.template.csv` | Copy this to a new file for your results |
| `source_crop_index.csv`, `display_candidates.csv` | Image/crop provenance and proposed display ownership |
| `OCR_MODELS.md` | OCR recommendation, checkpoints and rerun instructions |
| `ocr_tables/tables.html` | Three-model Train/Validation comparison, before matching |

**Observed package:** 813 validation records = three models × 271 crops per
model. Each model has 157 annotation crops and 114 detector-predicted crops;
keep these populations separate. Failures and excluded crops remain in the
input for traceability. All current `scoring_eligible` flags are false because
review gates are incomplete; this does not prevent development on saved outputs.

The Train rows in the tables are separate training-split evaluation evidence.
The main matching input file contains validation outputs only.

## 2. Start with PaddleOCR

**Provisional recommendation:** select `model == "paddleocr"` first. PaddleOCR
has the lowest CER and highest exact match on both selected validation subsets.
Public TrOCR has lower WER on predicted crops; retain it and EasyOCR for comparison.
This is a local development choice, not a final independently verified winner.

The exact pretrained weights for all three engines are included under `weights/`.
No weights were fine-tuned. Saved-output matching does not require loading them.
For fresh OCR, read `OCR_MODELS.md`; use the repository, dependencies, data and
documented preprocessing/settings. To check the packaged model files:

```sh
python3 verify_weights.py
```

## 3. Prepare the matcher inputs

**Project decisions / existing interface:**

1. Preserve every `record_id`, original `raw_ocr_text` and `normalised_ocr_text`.
   Join results by `record_id`; put matched/inferred values in separate columns.
2. Only recognise text from `prediction_status == "success"` as usable OCR input.
   Nonempty diagnostic text in an error record is not a successful reading.
   Keep successful-empty, failed and missing outputs distinguishable.
3. Keep service identifiers as strings, including suffixes and leading zeros.
4. Apply `eds-crop-normalised-v1` consistently to reference candidates:
   NFC → Unicode casefold → NFC → collapse whitespace → trim. Preserve
   punctuation, abbreviations, suffixes and zeros. No abbreviation mappings have
   been approved. Any additional matching-only transformation needs a separate
   documented policy; retain the supplied OCR strings unchanged.
5. Reference CSV has 609 rows, one blank destination and two duplicate complete
   rows. Decide how to handle these and retain original data-row provenance.
   Row numbers start at 1 after the header. It has `Route number`, `Origin` and
   `Destination`; no explicit direction or road-name field is supplied.

## 4. Confirm which fields belong together

Three different jobs are involved:

- **Crop correspondence:** does a prediction show the same text region as its
  proposed annotation? This supports evaluation; it is not reference matching.
- **Display ownership:** do the number and destination belong to the same bus
  display? This is needed before combining fields.
- **Reference matching:** which reference service/endpoint is supported by the
  OCR evidence, and should the matcher accept it or leave it unresolved?

**Observed limitation:** confirmed `display_id` values are null. The supplied
`candidate_display_id` values are geometry proposals. One image can contain
multiple buses: image identity alone does not establish shared ownership.
Do per-field candidate development first; confirm ownership with the
detector/integration owner before combining fields. Keep models, crop
populations, buses and original images separate when combining evidence.

Whole-display OCR/field extraction has not run in these baselines. If added
later, it may recover multiple fields, but must retain its own source and field
extraction evidence rather than assume those fields were already supplied.

## 5. Implement these matching decisions

The following are the **user-supplied intended rules**, still to implement and
validate for this handoff:

| Evidence from the same confirmed display | Matching action |
| --- | --- |
| Number only | Exact service-string match. Infer an endpoint only when reference and direction evidence establish one unique endpoint. |
| Destination only | Rank distinct endpoint candidates, then apply a similarity cutoff and a margin over the next distinct candidate. Infer a service only if uniquely supported. |
| Number and destination | Use an exact service match to narrow endpoint candidates. If destination fails acceptance, leave that field unresolved. Preserve conflicting evidence. |
| Route/road text only | Retain the transcription; the current reference has no route-text field to match against. |
| No usable text | Record whether OCR failed, returned no text, or fields/ownership remain unresolved. The saved crop inputs alone cannot establish detector misses. |

Keep dedicated-crop and any future whole-display evidence with their source IDs.
Agreement can share one resolved value while retaining both sources. Unresolved
disagreements need a conflict reason; copying reference text into OCR truth is
not a way to resolve them.

**Next-owner decisions:** document similarity method/range, acceptance cutoff,
ambiguity margin, direction/loop handling, alias provenance and abstention rules.
The suggested 25/50/75 cutoffs are proposals to compare, not measured optima.
Freeze policies before scoring; reserved test data stays untouched. Current
provisional scores do not establish verified matching thresholds.

## 6. Return results and a decision log

**Existing proposed output interface:** copy `matching_outputs.template.csv`;
keep each input ID and fill:

- `matching_status`: `matched`, `service_only`, `unmatched`, `input_error`,
  `no_text`, `needs_review` or `not_applicable`; `pending` means unprocessed.
- `matched_service`, `matched_endpoint`: leave unsupported values empty.
- `reference_row_numbers`: JSON array of original reference data-row numbers.
- `match_similarity`, `match_similarity_method`, `matching_policy_id`, `reason`.

Add a separate log or documented columns for recovered versus inferred values,
confirmed display/source IDs, rejected candidates, runner-up margin, conflicting
fields and per-field decision reasons. Preserve accepted fields even if another
field stays unresolved. Keep detector confidence, OCR confidence and match
similarity separate; their scores are not calibrated correctness probabilities.

Return the completed result CSV plus the matching policy/configuration and log.
Retain unresolved records and exclusions so the OCR owner can later evaluate
raw versus matched results, including wrong accepted values and harmful changes.

## 7. Review status and evaluation boundary

**Observed review/import status:**

| Item | Current state |
| --- | --- |
| Validation text/field proposals | cody checked them: 253 accepted, 18 unresolved |
| Focused 41 crop-pair reviews | 29 same text, 1 different coverage, 1 excluded, 10 unresolved |
| Pair candidates outside that subset | 73 unreviewed |
| Validation exclusions | 38, including P028; retained in the input with flags |
| Source-photo grouping | Pending; known scene-risk exclusions retained |
| Provisional scoring subsets | Train 522; validation annotation 67 / predicted 40, scored separately |
| Official independent scoring eligibility | Zero until the remaining gates pass |

Current cumulative pair decisions are `review/crop_pairing_decisions.csv`.
Text decisions are `review/validation.decisions.cody.csv`; import both alongside
later grouping decisions so completed review work is retained. Detailed pairing
provenance and unresolved selected pairs are under `review/cody_pairing/`.

Use `review/` and `evaluation/` for review/scoring, separately from matcher
inputs. Their transcriptions must not supply missing OCR, select reference
candidates or certify an accepted match. Source-photo grouping controls whether
evaluation images are sufficiently independent; it does not supply display
ownership or automatically fix a reading.

Evidence: packaged `handoff_manifest.json`, `reference/audit.json`,
`weights/models.lock.json`, `review/cody_pairing/`, `ocr_tables/` and
`OCR_MODELS.md`. These describe project decisions, implementation observations
and proposals; no coursework rubric requirements are asserted here.
