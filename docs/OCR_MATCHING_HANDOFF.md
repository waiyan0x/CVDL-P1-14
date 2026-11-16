# OCR → reference-matching handoff

The concise next-owner checklist is `docs/INFERENCE_MATCHING_PREP.md`, included
at the ZIP root as `INFERENCE_MATCHING_PREP.md` and linked from `START_HERE.txt`.

## OCR recommendation and actual weights included — 16 November 2026

Start matching development with PaddleOCR `en_PP-OCRv5_mobile_rec`, retaining
EasyOCR and public TrOCR outputs for comparison. This is a provisional choice
from the current readable validation subsets: Paddle has the lowest CER and
highest exact match; public TrOCR has lower WER on predicted crops. Grouping
remains pending, so this does not establish a final independent accuracy winner.

The ZIP now includes all three original pretrained model directories under
`weights/`, plus a hash/settings lock and `verify_weights.py`. No weights were
fine-tuned. Read packaged `OCR_MODELS.md` or `docs/OCR_MODEL_HANDOFF.md` for
checkpoint revisions, scores, rerun instructions and limitations. Matching saved
outputs needs no model loading. New OCR inference needs the repository/runtime,
input data and appropriate preprocessing; source/layout snapshots are included
as evidence. The package is not a complete standalone application environment.

## Reviewed pairings imported — 16 November 2026

cody returned the focused 41-pair review and clarified P033/P109 as unresolved.
The 13 blank exported rows were completed from the user's explicit chat
confirmation that all were checked, accepting their displayed same-text choices.
The unchanged upload and the chat provenance are preserved separately.
Outcome: 29 same-visible-text pairs, one different-coverage pair (P025), one
exclusion (P028), and ten unresolved. The other 73 prediction candidates were
outside this focused review and remain unreviewed. All 110 distinct crop/source
files used by these pairs were checked against their recorded SHA-256 hashes.

The current cumulative form is
`.cache/ocr_review/cody-pairing-20261116-01/crop_pairing_decisions.current.csv`.
Retain it and cody's earlier validation text decisions for subsequent imports.
The latest tables are
`.cache/ocr-baselines/three-output-tables-20261116-02/tables.html`.
P028's exclusion changes the provisional predicted denominator from 41 to 40;
67 annotation candidates and 522 training candidates retain their earlier scores.
All 813 saved OCR strings remain unchanged in the handoff, with updated review
metadata. Validation exclusions now total 38. All source-photo grouping remains
pending, so official independent-benchmark eligibility remains zero.

The latest ZIP remains `.cache/ocr-handoff/reference-matching-20261115-01.zip`;
its `START_HERE.txt` and `review/cody_pairing/` record this update. The matching
owner can use it for development now. Earlier dated sections below describe
their respective snapshots; their pending-pair and 41-candidate counts are
superseded by this update.

## Training-split diagnostics added — 15 November 2026

The handoff's `ocr_tables/` now includes populated Train and Validation rows for
all three pretrained models. The training subset has 522 AI-assisted label
candidates; all weights are unchanged, so this is training-split evaluation,
not fine-tuning. Scores are provisional; the verified evidence view stays pending.
Training run evidence is under `evaluation/training/`, kept apart from matcher
inputs. The main `matching_inputs` interface remains the same 813 validation
model/crop records. No reference matching has been applied to OCR scores.

Training geometry is unreviewed automatic layout and validation geometry is the
earlier AI-reviewed layout; devices/native CPU quantisation also differ. Do not
treat train/validation differences as proof of learning or unseen-data accuracy.
See `docs/OCR_CROP_SCORING.md` for sample counts, skips, failures and run settings.

## Current assessed handoff — 15 November 2026

The `ocr_tables/tables.html` presentation now defaults to populated provisional
AI-label agreement cells, with raw/normalised and annotation/predicted controls.
Its separate verified Evidence view remains pending. The diagnostic subset has
67 annotation and 41 predicted crops; these are selected readable proposals,
not verified ground truth or evidence for choosing matching thresholds. CSVs
retain `score_basis` and actual `candidate_crops`. Matching inputs and raw engine
strings are unchanged by this presentation update.

Use `.cache/ocr-handoff/reference-matching-20261115-01.zip` for the latest
handoff. This supersedes the earlier package snapshot, preserving current
benchmark exclusions. Start with `START_HERE.txt`, then `matching_inputs.jsonl`.
All 813 saved OCR records remain (752 successes, 61 errors); the reference CSV,
blank matching-result template, provenance and separate evaluation tables are
included. No matching has been performed and text accuracy remains pending.

The user authorised AI assessments first, followed by their own double-check.
`review/text_field_assessment.ai.csv` consolidates the earlier recorded visual
review of all 271 validation crops. It preserves proposed transcriptions,
readability, field conflicts and exclusions as **AI proposals**. Outcomes: 110
readable candidates, 49 partial/clipped cases, 68 unreadable cases, 26 challenge
cases, 17 field conflicts and one unresolved-presence case. These disjoint queue
counts do not replace the overlapping benchmark eligibility/exclusion counts.
No new human decisions are asserted; all scoring gates remain in force.

For the user's double-check, open `review/check_my_proposals.html` offline.
Each native crop is embedded beside its AI reading, with editable text/state,
decision and reason controls. No crop or human attestation is selected by default.
After a person enters actual name/date, selects inspected crops and explicitly
attests inspection, the page exports a supported hash-bound human text-decision
CSV. All unselected rows stay blank. Separate bound pairing/group forms are
included. Eight scripted export checks and two handoff unit tests passed; full
browser visual testing was not performed.

`source_crop_index.csv` adds original image names, crop paths, original-source
boxes and detector scores. `display_candidates.csv` inventories 110 panel boxes.
The enriched matching records include `source_image`, `crop`, `box_xyxy`,
`candidate_display_id` and `display_association_status`; confirmed `display_id`
remains null. Candidate ownership uses the matching annotation/predicted panel
population on the same original image and at least 80% field-area containment,
with exactly one qualifying panel: 267 unique candidates, three with no enclosing
candidate and one ambiguous. These are geometry proposals, not confirmed bus or
display ownership. Annotation geometry is evaluation evidence, not deployment
detector output. Do not combine fields across populations, models or unconfirmed
displays. Whole-panel text recovery has not run in these saved baselines.

The matching owner can begin per-field candidate development immediately; human
accuracy evaluation can follow review. AI proposed reference readings remain
under `review/` and evaluation references under `evaluation/`, never in the
engine-only matching input strings. Preserve raw/normalised OCR and inferred or
matched values separately. Service suffixes/leading zeros remain significant;
no abbreviation mappings or measured matching thresholds have been added.

Prepared 13 November 2026. Owner: **next person, not yet named**.
This package supplies saved validation OCR for matching development. No reference
matching has been run in preparing it. No model winner or OCR accuracy is claimed.

## Start here

1. Read `handoff_manifest.json` for counts, source hashes and model identities.
   Verify packaged file hashes if moving the bundle to another machine.
2. Consume `matching_inputs.jsonl` (recommended) or `matching_inputs.csv`. Both
   contain identical input records, with **no reference transcriptions**.
   JSONL preserves explicit nulls and booleans. Import CSV columns as text so
   service identifiers and leading zeros survive.
3. Use `reference/bus_information.csv` only as candidate reference data; review
   `reference/audit.json` before deciding how to handle blanks and duplicates.
4. Copy `matching_outputs.template.csv` to a new result file. Every status starts
   `pending`; no result or acceptance threshold has been invented for you.
5. Keep `evaluation/` for later scoring. It contains pending/AI-proposed reference
   text and must not be fed into matching, candidate selection or threshold tuning
   as reviewed ground truth. Accuracy stays pending until review gates pass.

The directory and ZIP are portable: no models, image files or absolute paths are
needed to consume the matching inputs. Historical run identities in evaluation
evidence may refer to the producer's local paths.

## Field definitions and ownership

**Observed implementation:** the current app recognises service number and
destination. Route/road-text recognition is a broader project goal, not an
established application or coursework requirement. Dataset labels remain intact.

| `dataset_field` | Handoff `field` | Meaning and matching boundary |
| --- | --- | --- |
| `front_eds_num` | `bus_number` | Service identifier as text, including letters and leading zeros; never cast to integer or guess a replacement digit |
| `front_eds_destination` | `destination` | Text visible in the supplied destination crop; a reference endpoint is a candidate, not a replacement OCR label |
| `front_eds_route` | `route_text` | Separately labelled route-information region, provisionally road/stop/VIA text; no separate road-name reference field exists in the CSV |

**Project decision (user instruction):** mixed-field crops and operational messages
stay in a separate challenge set, excluded from primary scoring and training until
field ownership is confirmed. Preserve `scope_policy`, `exclusion_reason` and review
states. Do not silently relabel an OFF SERVICE message as a service number, strip
adjacent visible words, or derive destination text from road text.

The `front_` dataset prefix does not prove front/side/rear view. Field class and
visible text/field ownership still need human review in this snapshot.

## Input interface, schema version 1

**Proposed downstream interface:** this is an offline per-crop handoff, not a new
live application API. Each record belongs to one model, variant, crop population
and field. Keep the original record immutable and join matching results by ID.

| Keys | Type / rule |
| --- | --- |
| `record_id` | Unique string `model/variant/review_id`; use as the result join key |
| `model`, `variant`, `review_id`, `split` | Strings; this bundle contains three pretrained baselines and validation (`valid`) only |
| `input_set` | `annotation` or `prediction`; evaluate them separately, never pool or substitute one for the other |
| `dataset_field`, `field` | Supplied class plus the mapping above |
| `source_image_sha256`, `crop_sha256` | Parent-image provenance and crop identity; not a reviewed bus/scene group |
| `display_id` | Null: a confirmed same-display association is not supplied by this handoff |
| `raw_ocr_text` | Untouched engine string, including whitespace/line breaks; null for a missing prediction |
| `normalised_ocr_text` | Separate normalised string, or null for a missing prediction |
| `prediction_status`, `error` | `success`, `error` or `missing`; error message when recorded |
| `successful_nonempty_input` | Boolean: only successful nonempty normalised text; it does **not** certify field correctness or evaluation eligibility |
| `ocr_confidence`, `detector_confidence` | Original optional numbers, kept distinct; neither is calibrated correctness probability or match similarity |
| `scoring_eligible` | Boolean from the frozen review gate; every current value is false |
| `field_review_status`, `human_field_confirmation` | Preserve pending/unresolved/empty values; do not auto-confirm |
| `scope_policy`, `exclusion_reason` | `challenge_only` or `review_required`, plus existing exclusions |
| `group_review_status`, `correspondence_status` | Review metadata; empty/pending does not mean reviewed |

Do not match on diagnostic text from an `error` record, even if it is nonempty.
A `success` with empty or whitespace-only text is a no-text case; retain it rather
than inventing a match. A missing record's null value differs from successful
empty output. `[UNK]` belongs to evaluation annotations, never an OCR target or
literal candidate to train/match.

### Text rules

**Project decision / implemented OCR policy:** keep raw strings unchanged.
Secondary normalisation is NFC → Unicode `casefold()` → NFC → collapse all Unicode
whitespace (including line breaks) to one ASCII space → trim ends. Preserve
punctuation, abbreviations and leading zeros. Do not expand abbreviations,
transliterate, strip accents, correct spelling or substitute lookalike characters.
Apply the same normalisation to reference candidates when comparing under this
policy. Its identifier is `eds-crop-normalised-v1`.

Primary raw scoring separately standardises NFC/per-line word spacing and keeps
case, punctuation and nonempty line breaks. Both scoring modes transform
predictions and references identically; neither uses matched strings as raw OCR.
The package contains both exact text policies in its manifest/evaluation report.

**Observed app implementation:** `backend/app/services/matching.py::normalise`
has a different matching-only policy: uppercase, remove non-ASCII alphanumeric
punctuation, shorten INTERCHANGE/TERMINAL/STATION and remove BUS before INT/TER.
Do not apply that policy to the stored OCR text or raw/normalised scoring targets.
If reusing it for candidate matching, record it under a separate matching-policy
ID and freeze any aliases, thresholds and rejection rules for that experiment.

## Reference constraints and missing association

**Observed reference data:** 609 data rows, columns `Route number`, `Origin`,
`Destination`; one empty destination cell and two duplicate complete rows. The
snapshot is byte-preserved and hashed. Data row numbers start at 1 after the
header. No alias, explicit direction, loop-service or road-name columns exist.

The existing app restricts endpoint candidates by exact recognised service,
considers both origin and destination and reports direction as unverified.
Its default threshold is an implementation setting, not a measured optimum.
Reference endpoints must never fill OCR ground truth or resolve unreadable glyphs.
Do not equate two endpoints with a verified travel direction.

**Required matching dependency:** service and destination must belong to the same
confirmed display. Source-image hash alone does not establish that relation:
an image can contain multiple buses/displays. Do not pair arbitrary fields from
one image, pool annotation/predicted crops, combine engines or borrow text from
another frame. Ask the detector/integration owner for explicit display ownership
before making complete service-plus-endpoint matches. Per-field diagnostic
candidate work can proceed while ownership remains unresolved.

## Output interface and next-owner decisions

**Proposed interface:** retain all input IDs and source OCR. Fill the output copy
with `matching_status` from `matched`, `service_only`, `unmatched`, `input_error`,
`no_text`, `needs_review`, or `not_applicable`. `pending` means unprocessed.
Use `needs_review` for uncertain ownership/field semantics; route text has no
supported reference domain yet. Excluded challenge cases must stay labelled.

`matched_service` and `matched_endpoint` are separate strings; leave unconfirmed
values empty. Record `reference_row_numbers` as a JSON array of snapshot data-row
numbers; `match_similarity` as a separately labelled optional score, together with
`match_similarity_method`, `matching_policy_id` and a human-readable `reason`.
Document the similarity formula, scale/range and threshold in the matching policy.
No output score is automatically a calibrated probability. A rejected match must
retain raw/normalised OCR and its rejection reason, with matched values empty.

Next owner must define and document: service constraints; endpoint/direction/loop
semantics; aliases and their provenance; reference blanks/duplicates; supported
road-text coverage; similarity metric, thresholds, ambiguity/tie rejection and
abstention rules. Confirm display ownership before integration. Do not choose
thresholds on reserved test data. Keep matched outputs separate for later
raw-versus-matched evaluation, including harmful corrections and rejected matches.

## Evidence and limits

The current package has 813 records: three engines × 271 validation crops (157
annotation / 114 predicted). It preserves 61 failed calls, all 78 model/challenge
records and all successful empty outputs. There are zero scoring-eligible rows;
CER/WER/exact match remain pending. Failed TrOCR P051 token-generation diagnostics
remain in the earlier paired baseline audit; they are not successful OCR text.
No test images, new inference, matching or training were used to prepare this bundle.

## Rebuild from the repository

Run from the repository root with a new output path (existing directories and
ZIPs are refused). The command copies saved evidence and creates a directory plus
ZIP; it does not run the matcher or send files to anyone.

```sh
.venv/bin/python scripts/prepare_ocr_matching_handoff.py \
  --report-dir .cache/ocr-baselines/eligible-scoring-20261113-01 \
  --config .cache/ocr-baselines/eligible-scoring-20261113-01/comparison.json \
  --output .cache/ocr-handoff/reference-matching-NEW
```

Source guide: `docs/OCR_MATCHING_HANDOFF.md`. Verification:
`.venv/bin/python -m unittest tests.evaluation.test_matching_handoff`.
