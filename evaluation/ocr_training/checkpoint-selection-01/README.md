# Checkpoint selection status

No checkpoint selected. Repository-root `results.csv` records the unavailable supplied TrOCR model with empty epoch/CER cells and `selected=false`; these blanks are unknown, not zero scores.

Observed evidence: the supplied fine-tuned model file is an LFS pointer, not hydrated weights. No new OCR training run, checkpoint epoch history, or per-checkpoint validation CER logs was found in the repository or the searched Downloads artifact names. The current v4 AI label audit records zero training-ready rows. No new training was performed in this conversation.

Selection will use validation CER only on one frozen reviewed validation set. The proposed aggregate follows the existing protocol: micro CER from total edits and reference characters, with number/destination/route CER reported separately. The proposed small-margin tie rule is absolute CER <= minimum CER + 0.005 (0.5 percentage points), then earliest epoch/step; it has not been applied. No test metrics enter selection.

No test crop was used for training, inference or checkpoint selection in this task. A global “no test-set crop used at any point” statement cannot be confirmed for historical training without its split manifests, preprocessing lineage, data-loader records and checkpoint provenance. Metadata-only split auditing is distinct from training/inference use.

Required to complete: actual training run directory or exported checkpoint history; epochs and validation per-field metrics/counts; configuration; training and validation manifests and evidence that test crops and their related/augmented variants were excluded. If validation CER has not been computed, the actual checkpoints and reviewed validation labels are also needed.

## Saved configuration mismatch found on recheck

Static inspection of `models/trocr-finetuned/training_args.bin` found
`load_best_model_at_end=true`, `metric_for_best_model=exact_match_accuracy`,
and `greater_is_better=true`. This configuration does not implement the requested
validation-CER-only checkpoint choice. The scalar configuration is recorded in
`supplied_training_configuration.json` and inline in root `results.csv`, with
its source path and hash. It describes saved arguments, not a verified run.
Configured three epochs are not reported as the checkpoint epoch.

The next viable change is to obtain/recompute validation micro CER and per-field
CER for every saved OCR checkpoint on one fixed reviewed validation manifest,
then select the earliest epoch within a declared margin of the minimum CER.
For future training, use the actual logged validation CER metric key with
`greater_is_better=false`. The earlier-within-margin rule requires explicit
selection over the checkpoint history; ordinary strict minimum selection does
not implement that tolerance. Preserve test exclusion evidence in the run's
manifests and data lineage. Do not substitute detector mAP or saved exact-match
accuracy for the requested criterion.

## Training-run discovery

See `discovery_audit.json` for the wider local, current remote Git branch/history, and connected Drive searches. No OCR training run was located. The Codi validation submission also retains unresolved text/group gates, so no checkpoint comparison was run. An actual training-environment path or shared run export is required; no new training was substituted for the missing run.
