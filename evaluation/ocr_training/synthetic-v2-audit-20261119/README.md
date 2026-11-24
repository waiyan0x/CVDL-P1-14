# Synthetic EDS v2 audit and proposed training run — 19 November 2026

## Decision

Observed: the existing scores concern the old 2,000-crop synthetic set, not the
new 10,000-crop archive. No v2 checkpoint has been trained, evaluated or selected
in this task. Keep real-only PaddleOCR run 20261117-031848 for inference matching.
Do not substitute a newly trained model until steps 6–7 have passed.

## Dataset evidence

Source: synthetic-eds-v2-20261119-test.zip. Despite its filename, all 10,000
labels declare train/synthetic/not scoring-eligible. Archive CRC and every crop
hash passed. No text collisions under scripts/synthetic_heldout.py; all five
recorded exclusion-source hashes match local files. Details: audit.json.

| Field | Crops | Distinct exact text strings |
| --- | ---: | ---: |
| Service number | 4,000 | 60 |
| Destination | 4,000 | 268 |
| Route text | 2,000 | 8 |

The 10,000 crops produce 10,196 training line pairs, with zero export skips.
513 crops require joining two label lines into one detected line under the
existing pairing rule. This is automated compatibility, not verified readability.
The user confirmed all 100 sampled image/text pairs in chat on 19 November 2026.
The completed upload file is synthetic_v2_human_spotcheck.csv; evidence is in
human_review_provenance.json. This is a sample check, not review of all 10,000 crops.
The original blank template is preserved. Review scope includes joined
lines and crops with visible neighbouring text. Record actual verdict, reviewer
and date. No AI inspection is recorded as a human check.

The archive does not contain its v2 generator/glyph-source files; exact producer
reproduction remains incomplete. The immutable archive can still be identified
and consumed by its SHA-256. labels_sha256 in its manifest identifies the source
evaluation/ocr_dataset/labels.csv, not its generated labels.csv.

## Existing benchmark reproduced

Source: evaluation/ocr_scoring/normalised-v8-layoutv3/{scores,syn/scores}/report.json.
Both reports reproduce exactly from saved predictions and frozen references.
Validation uses v3 for every version; test is unchanged. These are crop-level
scores before reference matching, not complete app performance.

| Model | Test n | CER real / old synthetic | WER real / old synthetic | Exact real / old synthetic |
| --- | ---: | ---: | ---: | ---: |
| PaddleOCR | 45 | 8.2 / 9.8 | 19.1 / 21.3 | 82.2 / 80.0 |
| TrOCR | 45 | 17.4 / 34.6 | 38.3 / 68.1 | 62.2 / 40.0 |
| EasyOCR | 45 | 21.6 / 19.5 | 45.7 / 42.6 | 60.0 / 55.6 |

Rates are percentages. EasyOCR improves CER/WER but loses exact match; the
other two regress on all three test rates. No old synthetic version replaces
real-only PaddleOCR. The small test set has already been used for selection;
it is not an independent final generalisation estimate. Never tune new settings
or checkpoints against these test outcomes.

## Alignment with steps 2–8

| Step | Evidence/status for v2 |
| --- | --- |
| 2: labels | Existing real text labels retained, including manual benchmark corrections. Synthetic labels supplied by rendering; automated checks passed, human 100-crop sample confirmed by user chat attestation. Real training labels remain historically unchanged. |
| 3: test | Existing 118 human-reviewed annotation crops, 45 eligible; no test detector crops. Existing test/hold-out layouts and labels stay frozen. No test files enter training. |
| 4: baselines | Current pretrained runs exist; saved benchmark scores reproduce. Reuse the same real crops and v3 validation layout. |
| 5: training | Candidate data/code ZIPs and new notebook prepared; CPU smoke checks, GPU training, best-checkpoint export and reload remain pending in Colab. |
| 6: evaluation | Pending new weights. Run all models on identical real train/valid/test/full+partial hold-out inputs. Use new synv2 run names/cache folders; current synthetic runners hard-code finetunedsyn and MUST NOT be reused unchanged for v2. |
| 7: selection | Pending actual v2 scores. Preserve the fixed rule: win 2 of 3 test measures against every other fine-tuned version, and validation/route hold-out CER no worse than own real-only version. |
| 8: results | This audit is preparation evidence, not v2 accuracy. Publish a separate v2 result table after scoring; preserve previous results. Rebuild matching handoff only if the selected model changes. |

Scoring: NFC, casefold, NFC, collapsed whitespace; punctuation retained; failed
or missing predictions count as empty. Eligible subsets: validation annotation
79 and detector 51; test annotation 45; real-train diagnostics 384. Route full
hold-out n=27 is supplementary; partial n=49 is a readable-text diagnostic.
The real text handoff is evaluation/ocr_dataset/reviewed-20261119/; crop-image
availability does not itself provide a text reference label.

## Candidate notebook and inputs

Notebook: colab/ocr_finetune/ocr_finetune_synthetic_v2.ipynb.
Upload these two files to My Drive/DRIVE without renaming:

- .runtime/ocr_finetune_bundle-20261119-synv2-candidate.zip
- .runtime/ocr_finetune_code-20261120-earlystop.zip

Upload the completed synthetic_v2_human_spotcheck.csv there with that exact filename.
View the corresponding images in
.runtime/synthetic-eds-v2-reference-20261119/contact_sheet.png and use its
contact_sheet.csv to locate individual crops. Wrong/unreadable findings require
correction/filtering and a rebuilt bundle/notebook hash; do not bypass the gate.
The notebook is a proposal with static checks, not a completed Colab smoke test.

The real training base has 366 line pairs. Validation export now explicitly uses
v3 (130 line images/pairs rather than the historical 128 images/124 pairs).
Old checkpoints used their historical training-time validation geometry; report
this checkpoint-selection protocol difference rather than attributing every
change solely to synthetic rendering.

Full candidate: 10,562 training pairs, 96.5% synthetic. Training keeps original
initial weights, seed 0, batch 32 (user-requested 20 November; T4 memory fit untested), lr 5e-5, at most 20 epochs; best epoch by
validation crop CER. PaddleOCR first, then TrOCR, then EasyOCR, sequentially on
the same Colab GPU. Epoch count stays fixed but optimiser-step budget grows with
the data, so this is a combined data/mixture/budget experiment. Proposed optional
follow-up: a matched-line-count and matched-update-budget control if the goal is
to isolate v2 rendering quality. That control has not been created or approved.
The original fixed full-data policy is retained in this candidate.

Return RUN_ID, best/ ZIPs, config.json, epoch_log.csv, selection.json,
validation_events.jsonl where produced, and environment/RUN_ID/input_receipt.json.
New trainer configs include manifest/train.tsv/valid.tsv hashes; the notebook
receipt includes data/code ZIP hashes and review CSV hash. No settings are
changed after inspecting TEST. No achieved latency or FPS claim is made.

## Local verification and pending work

Passed: all candidate payload hashes and ZIP CRC; all real training lines
preserved; validation pixels/labels identical to the explicit real-v3 base;
no test files; notebook cells parse; 5 preparation tests; 17 scorer tests.
Pending: original v2 generator source, Colab CPU/GPU smoke
checks and training, model reload, new-crop inference and all v2 benchmark scores.
Nothing has been pushed or launched remotely.

Update — 20 November 2026: batch size 32, maximum 20 epochs, and validation crop-CER early stopping (patience 3) for all three models. The updated notebook requires `ocr_finetune_code-20261120-earlystop.zip`; the data ZIP is unchanged. Seven local preparation tests pass. Paddle early-stop/export integration still needs Colab verification.
