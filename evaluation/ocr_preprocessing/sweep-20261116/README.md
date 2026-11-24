# Preprocessing sweep: validation only, 16 November 2026

Question: can preprocessing replace fine-tuning? Short answer: no.

## Setup

- **Crops:** the 109 scoring-eligible validation crops (67 annotation, 42 detector), using the same eligibility as `evaluation/ocr_scoring/normalised-v2-valid`.
- **Engines:** public pretrained EasyOCR (`english_g2`, recogniser only) and TrOCR (`trocr-base-printed`, greedy decoding). PaddleOCR could not be installed on this machine because the disk was full.
- **Input handling:** each crop is fed whole, with no line layout. My raw EasyOCR numbers reproduce the repo baseline exactly. TrOCR raw is 12.4% CER here against 11.2% in the repo, because the repo runner splits crops into lines.
- **Scoring:** normalised (casefold, collapsed whitespace), CER and exact match. Smaller CER is better.
- **Data use:** validation only. Test was not used.

## Results (CER %)

| Variant | TrOCR annotation | TrOCR detector | EasyOCR annotation | EasyOCR detector |
| --- | ---: | ---: | ---: | ---: |
| raw | 12.4 | **8.8** | 34.2 | 24.7 |
| 2x upscale | 12.0 | 10.0 | 35.9 | 22.7 |
| 2x upscale + unsharp | **11.6** | 10.0 | 34.4 | 23.5 |
| CLAHE | 12.2 | 10.8 | 36.7 | 24.7 |
| Otsu threshold, inverted | 16.8 | 24.7 | 53.7 | 50.6 |
| Morphological closing | 15.8 | 13.1 | 42.9 | 29.5 |
| Gaussian blur | 22.8 | 22.7 | 52.5 | 32.3 |
| Erosion 3x3 | 13.9 | 12.0 | **29.2** | **19.1** |
| Border padding | 17.0 | 13.1 | 29.2 | 26.3 |

The full table with per-field exact match is in `summary.txt`. Per-crop outputs are in `results_*.csv`.

## Findings

- No variant improves TrOCR on both annotation and detector crops.
- Colour thresholding is the worst variant on every engine and crop type. EDS text is LED dot-matrix, and a threshold splits each glyph into separate dots.
- Erosion helps EasyOCR by about 5 CER points. EasyOCR remains about 4x worse than pretrained PaddleOCR on raw crops (7.7%, repo baseline).
- Spacing and `>` conventions explain little of the error. Ignoring all non-alphanumerics lifts Paddle's annotation exact match only from 79.1% to 83.6% (`convention_errors.py`).
- The remaining errors are mostly:
  - dot-matrix glyph confusions: R/P/O, D/O, V/U ("AVE" read as "aue");
  - washed-out yellow text on light backgrounds (UPPER THOMSON RD, BALESTIER RD). All three engines fail on these.
- These error types are font-specific, which favours fine-tuning.
- Caveat: this is 9 variants chosen on 67 crops, so small differences are noise.

## Reproduce

```sh
.venv/bin/python -I evaluation/ocr_preprocessing/sweep-20261116/sweep.py {easyocr|trocr} \
  .runtime/ocr-task-files-20261116 \
  evaluation/ocr_scoring/normalised-v2-valid/scores/text_records.csv OUT.csv
python3 -I evaluation/ocr_preprocessing/sweep-20261116/summarize.py OUT.csv
```
