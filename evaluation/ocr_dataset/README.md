# OCR text-label dataset

New experiment: [5k train/validation/test split](5k-split-20261120/README.md),
4,000/500/500 exported image/text pairs. This is a separate benchmark from the
reviewed real-photo references below; no new trained-model scores exist yet.


The current reviewed benchmark references are in
[`reviewed-20261119/`](reviewed-20261119/README.md). This is a dataset of the
**text visible in each identified crop**, separate from Brendan's crop/box dataset.

| Split | Reference rows retained | Scorable rows | Provenance/use |
| --- | ---: | ---: | --- |
| Train | 387 | 384 | Primarily AI labels; human spot-check overrides retained; diagnostic only |
| Validation | 271 | 130 (79 annotation + 51 detector) | Human-reviewed text; excluded/overlap rows retained with reasons |
| Test | 118 | 45 annotation | Human-confirmed/corrected AI proposals |

- [`reviewed-20261119/labels.csv`](reviewed-20261119/labels.csv): every benchmark
  row with text, crop identity/hash, split, field, legibility, eligibility and provenance.
- [`reviewed-20261119/evaluation_labels.csv`](reviewed-20261119/evaluation_labels.csv):
  the 175 eligible validation/test references, identical for pretrained and
  fine-tuned evaluation. Synthetic crops are not evaluation references.
- [`reviewed-20261119/manifest.json`](reviewed-20261119/manifest.json): source
  hashes, counts and verification evidence.

Text-only handoff ZIP: `.runtime/ocr-text-labels-reviewed-20261119.zip`.
Selected-model matching handoff: `.runtime/ocr-matching-final-20261119.zip`.
The latter includes raw OCR, separate labels, route reference, images, weights
and inference code. `review_id` and `matching_record_id` provide explicit joins.
Display ownership still requires human confirmation before combining fields.

The top-level `labels.csv` and `summary.json` are historical 16 November
snapshots, retained because earlier training and synthetic-data preparation used
them. In particular, their test rows are AI proposals (60 eligible), superseded
by the reviewed export above (45 eligible). They are not the current test answer
key. No historical training labels or evaluation source documents were changed.

Reproduce the reviewed export into new destinations with:

```sh
python3 scripts/export_reviewed_ocr_labels.py --manifest evaluation/ocr_scoring/normalised-v8-layoutv3/manifest.json --matching .runtime/ocr-matching-final-20261119 --output evaluation/ocr_dataset/NEW_EXPORT --zip .runtime/NEW_EXPORT.zip
```

The export uses the existing frozen benchmark text, retains the manual
corrections and exclusions, verifies the 389 validation/test crop hashes and
checks their texts against the matching package. It performs no OCR or new
human review. See the exported README for normalization and scoring rules.
