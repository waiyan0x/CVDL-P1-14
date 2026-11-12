# OCR label review and per class evaluation PRD

Status: proposed scope for the next implementation commit, 12 November 2026.
These are project proposals, not coursework brief or rubric requirements.

## Problem and intended outcome

OCR predictions and weight identities exist, but reviewed crop eligibility cannot
yet be converted into reproducible three-class accuracy tables. Human decisions
need a validated import path, and the crop benchmark needs CER, WER and field
exact-match scoring. The next commit should supply those tools and generate
explicit pending results whenever the required evidence is incomplete.

A reviewer should be able to correct a crop label once, retain its provenance,
validate the decision, and score multiple models against the same frozen eligible
rows. Dataset content stays outside the commit.

## Current evidence

| Classification | Current state | Source |
| --- | --- | --- |
| Observed implementation | The recognition runner handles service number, route text and destination, separately for annotation and predicted crops. | `backend/app/evaluation/ocr_crop_baseline.py`, `FIELDS`, `load_crops`, `summarize` |
| Observed implementation | The older image evaluator supports CER and exact match for service number and destination. It does not implement crop-level WER or the three-class review schema. | `backend/app/evaluation/metrics.py`, `FIELD_NAMES`, `score_image`, `aggregate_engine` |
| Observed implementation | The first increment adds hash-bound human decision templates, dry-run validation, new review exports and blocker reports. Crop scoring and the final table generator remain to be implemented. | `scripts/import_ocr_review_decisions.py`; `docs/OCR_REVIEW_DECISIONS.md` |
| Observed run evidence | Preferred EasyOCR and public TrOCR MPS runs attempted the same 271 validation IDs. Both retained 20 unresolved layouts; TrOCR additionally failed generation on P051. No accuracy was calculated. | Local `evaluation/ocr_runs/weights-comparison-20261112/comparison.json` and linked run reports |
| Observed AI review | A new export proposes changes for 77 flagged validation crops. A focused training follow-up reinspected 44 field flags. Human adjudication, source grouping and scoring eligibility remain pending. | Local validation `submissions/codex-ai-20261112-01/review_audit.json`; training `v4-reviewed-01-ai-followup-20261112/review_audit.json` |
| User decision | Review training next and reserve test. Exclude datasets from the commit. | Session instructions, 12 November 2026 |
| Not stated | Assessment targets, rubric weights and a required whole-panel text protocol. | `README.md`, Evaluation and tests; `docs/OCR_TRANSCRIPTION_RULES.md`, Scoring boundary |

Local evidence references identify existing artifacts; they are not a request to
add those artifacts to Git. The earlier model-selection documentation predates
the successful public TrOCR runs and needs a concise status update.

## Scope of the next commit

1. A terminal command that validates and imports human review decisions into a
   new export, with a dry-run mode and an actionable unresolved-row report.
2. A frozen crop-scoring manifest with explicit eligibility and exclusions.
3. A scorer for raw per-class CER, WER and exact match, using saved predictions.
4. A report generator with model identities, per-model split/class tables,
   coverage, failures and existing timing evidence.
5. Focused tests using synthetic fixtures and documentation of the workflow.

Fine-tuning, checkpoint replacement, Paddle installation, new OCR inference,
application UI changes, reference matching and test-image review are outside
this commit. Tools must accept a reviewed test manifest later without opening
or scoring the reserved test set now.

## Class and input contract

| Crop class | Role in this commit |
| --- | --- |
| `front_eds_num` | Service identifier; text, preserving letters and leading zeros |
| `front_eds_destination` | Destination field; retain multiline text |
| `front_eds_route` | Separately annotated route-information field |
| `front_eds` | Panel context; text metrics remain not applicable until a panel transcription and reading-order protocol is defined |

Resolve class names through the source manifest, not numeric IDs alone. The
original `data/data.yaml` and v4 crop package have different class-ID mappings.
Keep annotation and predicted crops in separate evaluation populations, even
when they come from the same source image. Never combine their denominators.

Input roots and output locations must be explicit CLI arguments. Validate unique
IDs, crop/source hashes, supplied class, split and immutable geometry. Local
absolute paths may resolve inputs but must not be required by portable reports.

## Human review requirements

- Preserve original submissions and AI proposals. Write corrections to a new
  versioned export; refuse accidental overwrite.
- Require an explicit reviewer type and actual review date. AI proposals remain
  AI-attributed; filling a name or accepting an AI suggestion alone is not proof
  of independent review. Record the human decision and final visible text.
- Support accepting, correcting, leaving unresolved, or explicitly excluding a
  proposal. Retain previous values and a reason for each decision. Never resolve
  an issue by deleting its checklist row.
- Enforce NFC, declared word spacing, real line breaks, visible case and
  punctuation. Full text contains no `[UNK]`; partial text contains readable
  text plus `[UNK]`; wholly illegible text is exactly `[UNK]`.
- Represent blank, absent, wrong-field and uncertain field presence explicitly.
  They must not become an empty transcription scored as ordinary full text.
- Retain supplied class identity. Any proposed class correction is a separate
  reviewed decision with lineage, never an automatic folder move.
- Keep human text review, field review, grouping and predicted-crop
  correspondence as separate states. Completing one must not complete another.

Mixed-field crops remain a separately counted challenge population until their
target and reading order are adjudicated. Do not silently remove adjacent text
to make a service-number crop look correct. Operational messages such as
`OFF SERVICE` and `EXPRESS`, and road names appearing in destination fields,
need a declared field policy; their wording alone does not prove a wrong label.

## Eligibility and scoring protocol

Primary text eligibility requires full visible text, a present and confirmed
field, completed human adjudication where required, real review metadata, no
exclusion, confirmed source grouping and, for predicted crops, resolved
correspondence. Preserve all pending/excluded rows in coverage summaries.

Use the same frozen eligible IDs for every model. A missing prediction, empty
output or failed model call on an eligible crop is an empty hypothesis, so it
contributes deletions and fails exact match. Unavailable models remain unscored.
Unresolved layout entries remain explicit failures when their text is eligible;
do not omit them merely because recognition did not run. Reject duplicate IDs,
unknown IDs and mismatched crop hashes rather than choosing a row silently.

Partial and illegible text are outside primary whole-string scoring; `[UNK]`
must never become literal reference text in CER/WER. Blank/absent cases retain
their separate assessment policy from `docs/OCR_ANNOTATION_PACKAGE.md`. Where
no reference characters or words exist, the corresponding error rate is null.

| Metric | Proposed calculation |
| --- | --- |
| CER | Sum character edit distances divided by sum reference characters within one model/split/input-set/class cell |
| WER | Sum token edit distances divided by sum reference words within the same cell |
| Field exact match | Identical complete strings divided by eligible fields in the cell |

Primary exact match preserves case, punctuation and actual line breaks under
the existing transcription whitespace convention. Primary CER counts those
stored characters, including line breaks. For WER, split on Unicode whitespace;
line breaks separate words, while case and punctuation remain significant.
WER for service identifiers is computed using the same rule, with a note that
a one-token identifier largely duplicates exact-match correctness. Error rates
may exceed 100 percent because of insertions; do not clamp them.

Do not average crop-level error percentages. Optional normalized scores need
a separate versioned policy and separate columns; they are not required for
this commit. No detector mAP, confidence score or reference-match similarity
may substitute for text accuracy.

## Required report

Start with a model identity block: engine/software version, exact checkpoint
name and revision where available, recognition-weight SHA-256 and size,
processor/tokenizer hashes, pretrained/fine-tuned status, and run identity.
One checkpoint is shared across the text classes unless a run explicitly records
class-specific models.

Generate three model tables: EasyOCR, public TrOCR and the proposed PaddleOCR
candidate. Each uses this layout; Paddle remains unscored until a pinned model
and compatible predictions are supplied.

| Split | Input set | Crop class | Inventory crops | Eligible crops | CER (%) | WER (%) | Exact match (%) | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| valid | annotation | `front_eds_num` | From manifest | From review gate | Pending | Pending | Pending | Review pending |

Include all declared split/class combinations. Inventory counts are distinct
from eligible denominators. Unrun train/test rows show `Not run`; missing
review evidence shows `Review pending`; panel text scores show `Not applicable`.
Never copy illustrative screenshot values into a report. Creating table rows
must not trigger inference or access test-image pixels.

Report coverage by class: inventory, eligible, partial, illegible, mixed-field,
wrong-field and unresolved review/layout counts. Explain overlapping reason
counts so they are not mistaken for disjoint totals. For actual runs, show
attempted/completed/failed/empty counts and successful-crop latency median/p95,
with hardware, warmup and timing boundaries. Keep raw outputs and matched
outputs separate; matched-output scoring is outside this commit.

## Proposed implementation boundaries

Add focused modules under `backend/app/evaluation/` for review import,
eligibility, crop text scoring and report assembly, with thin scripts under
`scripts/`. Reuse the existing edit-distance and percentile helpers where their
contracts fit. Do not change the older image evaluator's output schema merely
to accommodate crop reports.

Use one canonical JSON result keyed by model, split, input set and class. Derive
HTML tables from it. Store null plus an explicit status for unavailable metrics;
zero is a measured value. Preserve reference/hypothesis edit counts and sample
denominators in local audit output. Hash the scoring manifest, protocol and
prediction inputs so stale or incomparable reports can be identified.

## Acceptance criteria

1. A synthetic correction round-trip preserves immutable identity and original
   values, records the human decision, and reports remaining blockers.
2. AI-only, partial, ungrouped, unresolved-field and unresolved-correspondence
   rows cannot enter primary scoring. Valid reviewed full rows can enter it.
3. Synthetic perfect matches score CER/WER 0 percent and exact match 100
   percent; known character/word insertions, deletions and substitutions have
   independently specified expected counts. Case, punctuation and multiline
   behavior follow the declared protocol.
4. Failed/missing predictions remain in eligible denominators. Hash/ID
   inconsistencies fail validation. Unavailable engines do not produce zeros.
5. Class and A/P populations remain separate. Every comparable model uses the
   same eligible IDs. Reports include denominator and exclusion evidence.
6. Current unresolved local reviews produce pending accuracy, not fabricated
   scores. Three model tables render with the correct explicit statuses.
7. Tests run without real dataset images, model downloads or model loading.
   Existing OCR reader and layout checks continue to pass.
8. No training/test inference or automatic promotion to training-ready occurs.

## Commit contents and dataset exclusion

Commit implementation, tests with synthetic fixtures, this PRD, and concise
workflow/status documentation. Generated local evidence is referenced by hash
or run ID; aggregate examples must not embed images or full label/prediction rows.

Exclude archives, dataset images/crops, segmentation previews, model binaries,
transcription exports, human-review CSVs, raw predictions and HTML containing
embedded crop bytes. Do not assume an `.html`, `.csv` or `.json` extension makes
a file free of dataset content. `.cache/` remains local.

Before staging, inspect the candidate paths and payloads. Before committing,
inspect `git diff --cached --stat` and the staged file list; explicitly exclude
the newly staged PNG previews and crop-bearing HTML from the current working
changes. Leave historical tracked datasets unchanged. Preparing this PRD does
not stage, unstage or commit any files.

## Dependencies and completion boundary

Human review decisions, full-photo grouping evidence and explicit field policy
are external inputs to measured accuracy. The implementation can be completed
and tested while those inputs remain pending; completion means validated tools
and honest pending tables, not a claim that labels are verified or a model won.
The assessment brief/rubric, whole-panel transcription policy, mixed-field
reading order and operational-message treatment remain open requirements.
