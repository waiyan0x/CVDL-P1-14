# Inputs copied from the OCR branch

Copied unchanged from `origin/OCR` at commit `e14108d` (19 November 2026) so this branch can run
without checking out the OCR branch. Replace with Cody's `matching_inputs.jsonl` when it arrives.

| File here | Source on the OCR branch | SHA-256 |
| --- | --- | --- |
| `paddle_ft_valid_fields.jsonl` | `evaluation/ocr_runs/paddleocr-finetuned-valid-layoutv2/predictions.jsonl` | `4a8983f83d55aec851d84ec843425392d3ebab6bbeda9c275e14e7ca586ca17c` |
| `paddle_ft_test_fields.jsonl` | `evaluation/ocr_runs/paddleocr-finetuned-test/predictions.jsonl` | `b24ce719c522f5399e175c4261c6bacb0282a3098885bc6cc3435b63223f46ad` |
| `paddle_ft_panels.jsonl` | `evaluation/ocr_runs/paddleocr-finetuned-panels-validtest/predictions.jsonl` | `bcdc63e176db7b47d0bc61601178fb4fade094414ede8ff8b0248f5a7f32551b` |
| `valid_labels.csv` | `evaluation/ocr_review/human-verification-20261116/validation.source.corrected-P065.csv` | `88ad565d3211047307f1b7cb58eeb3fd96c195c55b8757b61dabc2daf39e40dc` |
| `test_labels.csv` | `evaluation/ocr_review/test-confirmation-20261117/test.source.confirmed.csv` | `0a16c8768effd0d14ca58684ed78504b18c2b83019aa89298cdf288b0738afbd` |

OCR model: Cody's selected round 1 fine-tuned PaddleOCR `en_PP-OCRv5_mobile_rec`, run `20261117-031848`.
Validation uses line layout v2 (the v3 fix for four crops is not in git). Labels are human-checked.
