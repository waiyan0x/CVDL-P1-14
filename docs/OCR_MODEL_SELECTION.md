# OCR model selection

**Observed evidence:** EasyOCR is the working pretrained baseline. No accuracy
winner has been selected. The current validation labels and groups do not pass
the existing scoring gate. Reference matching, application post-processing and
training remain untouched.

## Candidate register

These are project proposals, not coursework requirements. The model-specific
details below come from external official documentation, outside the supplied
course materials. None establishes performance on these LED dot-matrix crops.

| Candidate | Reason to compare | Current status |
| --- | --- | --- |
| EasyOCR 1.7.2 English generation-2 | Existing recognizer; working local MPS baseline with native variable-width line preprocessing | Completed fixed-layout runs on verified `mps:0` |
| `microsoft/trocr-base-printed` | Different transformer recognizer; public printed single-line checkpoint, with explicit line handling | Downloaded pinned revision; loaded on `mps:0`, but disk exhaustion stopped the run before inference. User chose another machine later |
| PaddleOCR `en_PP-OCRv5_mobile_rec` | Lightweight English text-line recognizer; useful third candidate | Proposed, not installed or benchmarked. Requires a separate supported environment for a native GPU comparison |

TrOCR's [model card](https://huggingface.co/microsoft/trocr-base-printed)
specifies single-line input and printed-text SROIE training; its official
[configuration](https://huggingface.co/microsoft/trocr-base-printed/blob/93450be3f1ed40a930690d951ef3932687cc1892/config.json)
uses a 384-pixel square encoder input. This is a domain mismatch to investigate,
not evidence that it will outperform EasyOCR. The baseline processor retains
its native resize/normalization; shared grayscale lines are replicated into RGB.

The [Paddle recognition module](https://www.paddleocr.ai/main/en/version3.x/module_usage/text_recognition.html)
documents the proposed English recognizer. Paddle's
[macOS installation guide](https://www.paddlepaddle.org.cn/documentation/docs/en/install/pip/macos-pip_en.html)
currently lists Python 3.9–3.13 and CPU-only native macOS support. This repository's
Python 3.14/MPS setup is therefore unsuitable for that native GPU benchmark.
No alternative Paddle backend has been implemented or validated here.

PARSeq is deferred to keep the first comparison to three engines. This is a
scope decision, not a measured rejection. Tesseract remains an existing optional
application engine but its executable is absent on this machine; it is not part
of this proposed GPU shortlist. The private supplied TrOCR checkpoint is excluded
from the untouched-public-baseline comparison because its training provenance
is a different experiment.

## Observed EasyOCR result

Latest verification: `evaluation/ocr_runs/easyocr-v4-mps-fixed-lines-02/`.
The earlier `fixed-lines-01` is retained. Both used the same frozen
`evaluation/ocr_layouts/v4-lines-v1/manifest.json` and produced identical raw text,
statuses, crop hashes and geometry for all 271 IDs. Source/transcription and
cached-model before/after hashes passed in both runs.

| Set / field | Completed / attempted | Unresolved layout | Empty completed output | Recognition median / p95 ms (run 02) |
| --- | ---: | ---: | ---: | ---: |
| A service number | 58 / 60 | 2 | 1 | 6.70 / 18.63 |
| A route text | 39 / 42 | 3 | 1 | 13.41 / 111.74 |
| A destination | 49 / 55 | 6 | 1 | 11.93 / 45.79 |
| P service number | 40 / 42 | 2 | 0 | 6.31 / 8.10 |
| P route text | 35 / 37 | 2 | 0 | 11.31 / 86.94 |
| P destination | 30 / 35 | 5 | 0 | 12.69 / 85.15 |

There were 251 completed crops, 20 explicit layout errors and 280 recognized
line regions. No recognizer execution errors occurred on accepted layouts.
Run 02 verifies the extended runner's default EasyOCR path. It is not a selected
best latency trial: run 01's aggregate A median/p95 was 12.73/50.22 ms and P was
16.22/174.73 ms, versus 10.55/46.06 and 9.63/82.65 ms in run 02. Machine state
and first-use costs vary; these are single passes, not sustained throughput.

The shared boundaries are **AI-reviewed diagnostic geometry**, without independent
human attestation. They supply upstream information unavailable to automatic
deployment. Unresolved crops remain in completion/error counts and never fall
back to whole-crop recognition. The separate A/P populations must stay separate.

## Run TrOCR on another machine

Bring this branch, the 271 source crops and templates under
`evaluation/ocr_annotations/v4-reviewed-01/`, and the frozen layout manifest plus
checksum. The committed run/source hashes make input verification possible.
Install the project dependencies and a PyTorch build supporting that machine's
GPU; verify CUDA availability before choosing `--device cuda`. CUDA execution
has not been tested here. A CPU run is supported but must be labelled separately.

```sh
python -m pip install -r requirements.txt
python scripts/fetch_public_trocr.py
python -u scripts/run_easyocr_crops.py \
  --engine trocr --device cuda --warmup 3 --seed 0 \
  --line-layout evaluation/ocr_layouts/v4-lines-v1/manifest.json \
  --output evaluation/ocr_runs/trocr-base-printed-v4-cuda-fixed-lines-01
```

Use the new machine's environment interpreter in place of `python` as necessary.
The download pins public revision
`93450be3f1ed40a930690d951ef3932687cc1892`; only the safetensors checkpoint is
downloaded, without a duplicate PyTorch weight file. Caches remain Git-ignored.
Do not use `scripts/fetch_trocr.py`, which fetches the application's private model.
Keep several GB free for model loading and memory/swap overhead. A local
3-GiB disk guard follows the observed failure; this is an operational margin,
not a published model hardware requirement.

The shared runner requires frozen layouts for TrOCR, verifies the actual parameter
device and hashes source/model files before/after. Native processing, float dtype,
environment and sources are saved. Generation is greedy, batch one, at most 64
new tokens per line; missing EOS is an explicit error with retained token history.
Per-token probabilities exclude special tokens, with a geometric mean per line.
Those scores are not calibrated accuracy or comparable to EasyOCR confidence.
Timing includes processor/transfer/generation/confidence/decode inside synchronized
line calls, with initialization and warmups excluded. No inference-time downloads
or text correction are performed. The local failed attempt is preserved under
`evaluation/ocr_runs/trocr-base-printed-v4-mps-fixed-lines-01/`.

Paddle still needs its own recognition-only adapter using exactly these line
regions and the same artifact/timing contract. Run all candidates on the same
machine for a latency ranking; do not rank Mac MPS timings against another
machine's CUDA timings. Freeze and hash its eventual checkpoint before running.

## Decision gate and next actions

**Existing project policy:** `OCR_TRANSCRIPTION_RULES.md` §Scoring boundary and
`OCR_ANNOTATION_PACKAGE.md` §Text states and scoring policy require reviewed visible
text, field identity, reviewer/date, no exclusion and confirmed groups; P also
requires correspondence review. The Codi import audit currently has zero
scoring-ready rows, 77 rows needing resolution/inspection and all groups pending.
Geometry acceptance alone does not resolve those text/group gates.

1. Resolve the listed labels and review related-frame groups across splits;
   adjudicate the 20 unresolved layouts. Keep all 271 A/P examples validation-only.
2. Run public TrOCR on the other machine, then implement and run the proposed
   Paddle recognizer. Preserve all failures and identical paired inputs.
3. Once labels pass the gate, compare raw per-field exact match and CER on the
   same eligible rows; retain engine failures in denominators. Report coverage,
   empty outputs, multiline failures and A/P results separately. Raw exact
   scoring preserves case, punctuation and line breaks; any optional normalized
   metric must follow the existing rules and be labelled separately.
4. Select using accuracy and failure behavior first, then measured latency and
   deployment feasibility. This is a proposal with no invented weighted score or
   target threshold. Inspect tradeoffs per field rather than declaring a winner
   from aggregate confidence or a few visual examples.

Model selection on this validation package does not establish independent test
generalization. A separate reviewed, group-disjoint OCR test is still required
for that claim. Reference matching, post-processing and training remain later work.
