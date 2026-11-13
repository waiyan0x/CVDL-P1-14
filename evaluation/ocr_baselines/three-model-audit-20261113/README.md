# Audited three-model baseline

Open [baseline tables](tables/baseline_tables.html). Accuracy is pending human
review; these are diagnostic execution results on validation crops.

| Model | Attempted | Completed | Failed | Empty successful outputs |
| --- | ---: | ---: | ---: | ---: |
| EasyOCR (MPS) | 271 | 251 | 20 | 3 |
| Public TrOCR (MPS) | 271 | 250 | 21 | 0 |
| Paddle English v5 (CPU) | 271 | 251 | 20 | 3 |

- `audit.json`: pinned prediction/report hashes and compatibility checks.
- `paired_status.csv`: all 271 IDs, hashes, layout states and engine outcomes.
- `failures.jsonl`: complete records for all 61 engine failures.
- `failed_engine_history.json`: TrOCR failed-generation diagnostics; P051
  reached its 64-token cap without EOS. Do not score that diagnostic text as
  a successful result.
- `tables/`: refreshed three-model tables, scoring manifest and eligibility
  audit using the challenge-excluded validation working snapshot.

All engines use the same crop hashes and frozen layout. Shared crop/layout code
snapshots are identical; historical line pixel buffers were not separately
hashed. Empty means empty or whitespace-only; original text is unchanged.
Twenty unresolved layouts remain explicit errors per engine, with no full-crop
fallback or omitted IDs. Failed eligible examples later count as empty hypotheses
under the scorer. No test images, OCR inference, fine-tuning or matching were used
in this audit. CPU and MPS timings cannot support a direct latency ranking.

See [the protocol and reproduction command](../../../docs/OCR_PRETRAINING_DELIVERABLE.md).
