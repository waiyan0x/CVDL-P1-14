# OCR results — round 2 (synthetic training data)

pre = pretrained; fine = fine-tuned on real labels (run 20261117-031848); fine+syn = fine-tuned on real + synthetic lines (`ocr_finetune_bundle-20261118-syn.zip`). `pending` = synthetic-trained run not available yet. Normalised scoring; all values %.

### Test annotation crops (official)

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 24 | 3.0 | 0.0 | 0.0 | 8.3 | 0.0 | 0.0 | 91.7 | 100.0 | 100.0 |
| PaddleOCR | destination | 17 | 8.2 | 5.2 | 7.7 | 26.9 | 15.4 | 21.2 | 41.2 | 70.6 | 64.7 |
| PaddleOCR | route | 4 | 29.1 | 24.1 | 24.1 | 72.2 | 55.6 | 50.0 | 0.0 | 25.0 | 25.0 |
| PaddleOCR | **all fields** | 45 | 11.6 | 8.2 | 9.8 | 30.9 | 19.1 | 21.3 | 64.4 | 82.2 | 80.0 |
| TrOCR | number | 24 | 3.0 | 4.5 | 14.9 | 4.2 | 8.3 | 29.2 | 95.8 | 91.7 | 70.8 |
| TrOCR | destination | 17 | 15.5 | 15.5 | 35.6 | 40.4 | 44.2 | 78.8 | 29.4 | 29.4 | 5.9 |
| TrOCR | route | 4 | 38.0 | 34.2 | 48.1 | 72.2 | 61.1 | 88.9 | 25.0 | 25.0 | 0.0 |
| TrOCR | **all fields** | 45 | 17.9 | 17.4 | 34.6 | 37.2 | 38.3 | 68.1 | 64.4 | 62.2 | 40.0 |
| EasyOCR | number | 24 | 7.5 | 3.0 | 4.5 | 16.7 | 8.3 | 12.5 | 83.3 | 91.7 | 87.5 |
| EasyOCR | destination | 17 | 38.6 | 22.7 | 21.0 | 67.3 | 51.9 | 51.9 | 23.5 | 29.4 | 23.5 |
| EasyOCR | route | 4 | 36.7 | 34.2 | 27.8 | 83.3 | 77.8 | 55.6 | 0.0 | 0.0 | 0.0 |
| EasyOCR | **all fields** | 45 | 32.7 | 21.6 | 19.5 | 57.4 | 45.7 | 42.6 | 53.3 | 60.0 | 55.6 |

### Validation annotation crops (official)

Validation also chose each model's training epoch, so fine-tuned values are optimistic.

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 43 | 2.6 | 2.6 | 3.5 | 2.3 | 2.3 | 4.7 | 97.7 | 97.7 | 95.3 |
| PaddleOCR | destination | 19 | 14.9 | 12.2 | 9.5 | 33.9 | 22.6 | 17.7 | 57.9 | 57.9 | 68.4 |
| PaddleOCR | route | 17 | 17.0 | 11.3 | 11.7 | 54.9 | 25.5 | 31.4 | 29.4 | 52.9 | 52.9 |
| PaddleOCR | **all fields** | 79 | 13.5 | 10.1 | 9.3 | 32.1 | 17.9 | 18.6 | 73.4 | 78.5 | 79.7 |
| TrOCR | number | 43 | 13.2 | 7.0 | 17.5 | 25.6 | 9.3 | 32.6 | 74.4 | 90.7 | 67.4 |
| TrOCR | destination | 19 | 19.1 | 17.9 | 50.4 | 48.4 | 45.2 | 83.9 | 31.6 | 36.8 | 0.0 |
| TrOCR | route | 17 | 15.0 | 15.4 | 49.0 | 41.2 | 39.2 | 98.0 | 29.4 | 35.3 | 5.9 |
| TrOCR | **all fields** | 79 | 16.4 | 14.9 | 43.8 | 39.7 | 33.3 | 74.4 | 54.4 | 65.8 | 38.0 |
| EasyOCR | number | 43 | 23.7 | 10.5 | 7.9 | 39.5 | 18.6 | 11.6 | 60.5 | 81.4 | 88.4 |
| EasyOCR | destination | 19 | 45.4 | 27.5 | 22.1 | 77.4 | 43.5 | 40.3 | 0.0 | 42.1 | 42.1 |
| EasyOCR | route | 17 | 49.0 | 34.0 | 23.5 | 88.2 | 76.5 | 58.8 | 0.0 | 11.8 | 11.8 |
| EasyOCR | **all fields** | 79 | 42.9 | 27.0 | 20.1 | 70.5 | 47.4 | 38.5 | 32.9 | 57.0 | 60.8 |

### Validation detector crops (official)

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 33 | 3.4 | 4.6 | 3.4 | 3.0 | 6.1 | 3.0 | 97.0 | 93.9 | 97.0 |
| PaddleOCR | destination | 6 | 29.6 | 21.1 | 14.1 | 68.8 | 43.8 | 37.5 | 33.3 | 50.0 | 50.0 |
| PaddleOCR | route | 12 | 21.2 | 14.5 | 17.6 | 59.5 | 27.0 | 35.1 | 25.0 | 50.0 | 41.7 |
| PaddleOCR | **all fields** | 51 | 18.3 | 13.3 | 13.0 | 39.5 | 22.1 | 23.3 | 72.5 | 78.4 | 78.4 |
| TrOCR | number | 33 | 11.5 | 5.7 | 20.7 | 18.2 | 6.1 | 36.4 | 81.8 | 93.9 | 63.6 |
| TrOCR | destination | 6 | 33.8 | 25.4 | 50.7 | 68.8 | 43.8 | 81.2 | 50.0 | 50.0 | 0.0 |
| TrOCR | route | 12 | 24.8 | 29.1 | 52.1 | 37.8 | 40.5 | 100.0 | 33.3 | 25.0 | 0.0 |
| TrOCR | **all fields** | 51 | 23.2 | 22.0 | 43.3 | 36.0 | 27.9 | 72.1 | 66.7 | 72.5 | 41.2 |
| EasyOCR | number | 33 | 16.1 | 9.2 | 8.0 | 24.2 | 12.1 | 9.1 | 75.8 | 87.9 | 90.9 |
| EasyOCR | destination | 6 | 57.7 | 45.1 | 29.6 | 81.2 | 75.0 | 56.2 | 16.7 | 33.3 | 50.0 |
| EasyOCR | route | 12 | 51.5 | 37.0 | 29.1 | 89.2 | 75.7 | 56.8 | 0.0 | 16.7 | 16.7 |
| EasyOCR | **all fields** | 51 | 43.3 | 31.3 | 23.5 | 62.8 | 51.2 | 38.4 | 51.0 | 64.7 | 68.6 |

### Route hold-out, full crops (supplementary)

Single human reviewer; split shows as train because the crops come from train photos.

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | route | 27 | 12.6 | 10.7 | 11.3 | 34.7 | 25.3 | 22.7 | 48.1 | 59.3 | 59.3 |
| PaddleOCR | **all fields** | 27 | 12.6 | 10.7 | 11.3 | 34.7 | 25.3 | 22.7 | 48.1 | 59.3 | 59.3 |
| TrOCR | route | 27 | 24.9 | 23.9 | 54.4 | 56.0 | 48.0 | 104.0 | 18.5 | 29.6 | 0.0 |
| TrOCR | **all fields** | 27 | 24.9 | 23.9 | 54.4 | 56.0 | 48.0 | 104.0 | 18.5 | 29.6 | 0.0 |
| EasyOCR | route | 27 | 33.2 | 22.5 | 19.8 | 80.0 | 54.7 | 50.7 | 3.7 | 25.9 | 25.9 |
| EasyOCR | **all fields** | 27 | 33.2 | 22.5 | 19.8 | 80.0 | 54.7 | 50.7 | 3.7 | 25.9 | 25.9 |

### Train (diagnostic only)

AI labels; models were trained on these crops. Not an accuracy result.

| Model | Field | n | CER pre | CER fine | CER fine+syn | WER pre | WER fine | WER fine+syn | Exact pre | Exact fine | Exact fine+syn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR | number | 280 | 11.8 | 8.9 | 11.7 | 16.4 | 9.3 | 11.1 | 84.6 | 93.2 | 92.9 |
| PaddleOCR | destination | 62 | 31.4 | 9.2 | 8.1 | 70.8 | 16.3 | 16.3 | 19.4 | 82.3 | 77.4 |
| PaddleOCR | route | 42 | 23.5 | 13.1 | 13.8 | 59.5 | 22.3 | 31.4 | 31.0 | 81.0 | 71.4 |
| PaddleOCR | **all fields** | 384 | 22.6 | 10.2 | 10.9 | 42.1 | 14.2 | 16.9 | 68.2 | 90.1 | 88.0 |
| TrOCR | number | 280 | 25.6 | 11.0 | 15.3 | 35.0 | 10.0 | 20.4 | 67.9 | 93.2 | 82.5 |
| TrOCR | destination | 62 | 41.1 | 25.1 | 42.6 | 78.1 | 53.9 | 86.5 | 11.3 | 30.6 | 1.6 |
| TrOCR | route | 42 | 30.4 | 20.5 | 49.1 | 63.6 | 38.8 | 91.7 | 28.6 | 64.3 | 7.1 |
| TrOCR | **all fields** | 384 | 32.8 | 19.1 | 35.4 | 54.2 | 29.5 | 55.6 | 54.4 | 79.9 | 61.2 |
| EasyOCR | number | 280 | 33.8 | 10.4 | 10.6 | 46.8 | 11.1 | 10.7 | 56.4 | 92.1 | 92.5 |
| EasyOCR | destination | 62 | 55.6 | 24.1 | 23.2 | 84.3 | 47.8 | 45.5 | 9.7 | 46.8 | 48.4 |
| EasyOCR | route | 42 | 48.8 | 20.8 | 18.6 | 90.1 | 46.3 | 35.5 | 2.4 | 45.2 | 47.6 |
| EasyOCR | **all fields** | 384 | 46.4 | 18.6 | 17.7 | 67.4 | 29.7 | 26.6 | 43.0 | 79.7 | 80.5 |

### Route hold-out, partial crops — readable text only (diagnostic)

| Model | Version | n | Readable-text CER | 95% range | All readable correct |
| --- | --- | ---: | ---: | --- | ---: |
| EasyOCR | pretrained | 49 | 56.7 | 48.2–65.1 | 4.1 |
| EasyOCR | fine-tuned | 49 | 45.0 | 36.3–53.5 | 8.2 |
| EasyOCR | fine-tuned+syn | 49 | 40.1 | 31.7–48.9 | 6.1 |
| TrOCR | pretrained | 49 | 41.3 | 32.9–50.1 | 12.2 |
| TrOCR | fine-tuned | 49 | 38.9 | 30.0–48.1 | 16.3 |
| TrOCR | fine-tuned+syn | 49 | 59.9 | 54.2–65.1 | 2.0 |
| PaddleOCR | pretrained | 49 | 33.0 | 24.0–42.5 | 22.4 |
| PaddleOCR | fine-tuned | 49 | 31.3 | 22.8–40.1 | 22.4 |
| PaddleOCR | fine-tuned+syn | 49 | 28.5 | 20.7–36.5 | 24.5 |

### Round 2 app-model check (agreed rule)

| Fine-tuned model | Test CER | Test WER | Test exact |
| --- | ---: | ---: | ---: |
| PaddleOCR fine | 8.2 | 19.1 | 82.2 |
| PaddleOCR fine+syn | 9.8 | 21.3 | 80.0 |
| TrOCR fine | 17.4 | 38.3 | 62.2 |
| TrOCR fine+syn | 34.6 | 68.1 | 40.0 |
| EasyOCR fine | 21.6 | 45.7 | 60.0 |
| EasyOCR fine+syn | 19.5 | 42.6 | 55.6 |

- PaddleOCR fine+syn: beats every other fine-tuned model on test (2 of 3): no; validation CER no worse than its round 1 version: yes; route hold-out CER no worse: no → **does not replace**
- TrOCR fine+syn: beats every other fine-tuned model on test (2 of 3): no; validation CER no worse than its round 1 version: no; route hold-out CER no worse: no → **does not replace**
- EasyOCR fine+syn: beats every other fine-tuned model on test (2 of 3): no; validation CER no worse than its round 1 version: yes; route hold-out CER no worse: yes → **does not replace**

With 45 test crops one crop moves exact match by 2.2 points; choosing among more candidates on the same test set makes the winner look better than it is.
