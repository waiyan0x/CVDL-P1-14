# OCR results

Scoring: normalised (casefold, whitespace collapsed).
Failed/missing predictions count as empty strings.

## Table 1: annotation crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained | train | number | 282 | 34.3 | 47.5 | 56.0 |
| EasyOCR | pretrained | train | destination | 63 | 55.6 | 84.4 | 9.5 |
| EasyOCR | pretrained | train | route | 42 | 48.6 | 90.0 | 2.4 |
| EasyOCR | pretrained | train | all | 387 | 46.5 | 67.7 | 42.6 |
| EasyOCR | pretrained | valid | number | 43 | 23.7 | 39.5 | 60.5 |
| EasyOCR | pretrained | valid | destination | 19 | 45.4 | 77.4 | 0.0 |
| EasyOCR | pretrained | valid | route | 17 | 49.4 | 88.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 79 | 43.0 | 70.5 | 32.9 |
| EasyOCR | pretrained | test | number | 24 | 7.5 | 16.7 | 83.3 |
| EasyOCR | pretrained | test | destination | 17 | 38.6 | 67.3 | 23.5 |
| EasyOCR | pretrained | test | route | 4 | 36.7 | 83.3 | 0.0 |
| EasyOCR | pretrained | test | all | 45 | 32.7 | 57.4 | 53.3 |
| EasyOCR | finetuned | train | number | 282 | 10.3 | 11.0 | 92.2 |
| EasyOCR | finetuned | train | destination | 63 | 23.8 | 47.2 | 47.6 |
| EasyOCR | finetuned | train | route | 42 | 20.4 | 45.0 | 47.6 |
| EasyOCR | finetuned | train | all | 387 | 18.3 | 29.2 | 80.1 |
| EasyOCR | finetuned | valid | number | 43 | 10.5 | 18.6 | 81.4 |
| EasyOCR | finetuned | valid | destination | 19 | 27.5 | 43.5 | 42.1 |
| EasyOCR | finetuned | valid | route | 17 | 34.4 | 76.5 | 11.8 |
| EasyOCR | finetuned | valid | all | 79 | 27.1 | 47.4 | 57.0 |
| EasyOCR | finetuned | test | number | 24 | 3.0 | 8.3 | 91.7 |
| EasyOCR | finetuned | test | destination | 17 | 22.7 | 51.9 | 29.4 |
| EasyOCR | finetuned | test | route | 4 | 34.2 | 77.8 | 0.0 |
| EasyOCR | finetuned | test | all | 45 | 21.6 | 45.7 | 60.0 |
| Public TrOCR | pretrained | train | number | 282 | 25.8 | 35.5 | 67.4 |
| Public TrOCR | pretrained | train | destination | 63 | 41.1 | 78.3 | 11.1 |
| Public TrOCR | pretrained | train | route | 42 | 30.0 | 63.3 | 28.6 |
| Public TrOCR | pretrained | train | all | 387 | 32.8 | 54.5 | 54.0 |
| Public TrOCR | pretrained | valid | number | 43 | 13.2 | 25.6 | 74.4 |
| Public TrOCR | pretrained | valid | destination | 19 | 19.1 | 48.4 | 31.6 |
| Public TrOCR | pretrained | valid | route | 17 | 23.5 | 49.0 | 29.4 |
| Public TrOCR | pretrained | valid | all | 79 | 19.7 | 42.3 | 54.4 |
| Public TrOCR | pretrained | test | number | 24 | 3.0 | 4.2 | 95.8 |
| Public TrOCR | pretrained | test | destination | 17 | 15.5 | 40.4 | 29.4 |
| Public TrOCR | pretrained | test | route | 4 | 38.0 | 72.2 | 25.0 |
| Public TrOCR | pretrained | test | all | 45 | 17.9 | 37.2 | 64.4 |
| Public TrOCR | finetuned | train | number | 282 | 11.0 | 9.9 | 93.3 |
| Public TrOCR | finetuned | train | destination | 63 | 24.7 | 53.3 | 31.7 |
| Public TrOCR | finetuned | train | route | 42 | 20.1 | 37.5 | 64.3 |
| Public TrOCR | finetuned | train | all | 387 | 18.8 | 29.0 | 80.1 |
| Public TrOCR | finetuned | valid | number | 43 | 7.0 | 9.3 | 90.7 |
| Public TrOCR | finetuned | valid | destination | 19 | 17.9 | 45.2 | 36.8 |
| Public TrOCR | finetuned | valid | route | 17 | 21.9 | 41.2 | 35.3 |
| Public TrOCR | finetuned | valid | all | 79 | 17.5 | 34.0 | 65.8 |
| Public TrOCR | finetuned | test | number | 24 | 4.5 | 8.3 | 91.7 |
| Public TrOCR | finetuned | test | destination | 17 | 15.5 | 44.2 | 29.4 |
| Public TrOCR | finetuned | test | route | 4 | 34.2 | 61.1 | 25.0 |
| Public TrOCR | finetuned | test | all | 45 | 17.4 | 38.3 | 62.2 |
| PaddleOCR | pretrained | train | number | 282 | 12.0 | 16.7 | 84.4 |
| PaddleOCR | pretrained | train | destination | 63 | 31.1 | 70.6 | 19.0 |
| PaddleOCR | pretrained | train | route | 42 | 23.1 | 59.2 | 31.0 |
| PaddleOCR | pretrained | train | all | 387 | 22.4 | 42.1 | 68.0 |
| PaddleOCR | pretrained | valid | number | 43 | 2.6 | 2.3 | 97.7 |
| PaddleOCR | pretrained | valid | destination | 19 | 14.9 | 33.9 | 57.9 |
| PaddleOCR | pretrained | valid | route | 17 | 17.0 | 54.9 | 29.4 |
| PaddleOCR | pretrained | valid | all | 79 | 13.5 | 32.1 | 73.4 |
| PaddleOCR | pretrained | test | number | 24 | 3.0 | 8.3 | 91.7 |
| PaddleOCR | pretrained | test | destination | 17 | 8.2 | 26.9 | 41.2 |
| PaddleOCR | pretrained | test | route | 4 | 29.1 | 72.2 | 0.0 |
| PaddleOCR | pretrained | test | all | 45 | 11.6 | 30.9 | 64.4 |
| PaddleOCR | finetuned | train | number | 282 | 8.8 | 9.2 | 93.3 |
| PaddleOCR | finetuned | train | destination | 63 | 9.1 | 16.1 | 82.5 |
| PaddleOCR | finetuned | train | route | 42 | 12.7 | 20.8 | 83.3 |
| PaddleOCR | finetuned | train | all | 387 | 10.0 | 13.7 | 90.4 |
| PaddleOCR | finetuned | valid | number | 43 | 2.6 | 2.3 | 97.7 |
| PaddleOCR | finetuned | valid | destination | 19 | 12.2 | 22.6 | 57.9 |
| PaddleOCR | finetuned | valid | route | 17 | 11.3 | 25.5 | 52.9 |
| PaddleOCR | finetuned | valid | all | 79 | 10.1 | 17.9 | 78.5 |
| PaddleOCR | finetuned | test | number | 24 | 0.0 | 0.0 | 100.0 |
| PaddleOCR | finetuned | test | destination | 17 | 5.2 | 15.4 | 70.6 |
| PaddleOCR | finetuned | test | route | 4 | 24.1 | 55.6 | 25.0 |
| PaddleOCR | finetuned | test | all | 45 | 8.2 | 19.1 | 82.2 |

## Table 2: detector crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained | valid | number | 33 | 16.1 | 24.2 | 75.8 |
| EasyOCR | pretrained | valid | destination | 6 | 59.2 | 81.2 | 16.7 |
| EasyOCR | pretrained | valid | route | 12 | 51.5 | 89.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 51 | 43.7 | 62.8 | 51.0 |
| EasyOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | valid | number | 33 | 9.2 | 12.1 | 87.9 |
| EasyOCR | finetuned | valid | destination | 6 | 54.9 | 81.2 | 33.3 |
| EasyOCR | finetuned | valid | route | 12 | 37.0 | 75.7 | 16.7 |
| EasyOCR | finetuned | valid | all | 51 | 33.4 | 52.3 | 64.7 |
| EasyOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | valid | number | 33 | 11.5 | 18.2 | 81.8 |
| Public TrOCR | pretrained | valid | destination | 6 | 36.6 | 68.8 | 50.0 |
| Public TrOCR | pretrained | valid | route | 12 | 24.8 | 37.8 | 33.3 |
| Public TrOCR | pretrained | valid | all | 51 | 23.8 | 36.0 | 66.7 |
| Public TrOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | valid | number | 33 | 5.7 | 6.1 | 93.9 |
| Public TrOCR | finetuned | valid | destination | 6 | 45.1 | 50.0 | 50.0 |
| Public TrOCR | finetuned | valid | route | 12 | 29.1 | 40.5 | 25.0 |
| Public TrOCR | finetuned | valid | all | 51 | 26.3 | 29.1 | 72.5 |
| Public TrOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | valid | number | 33 | 3.4 | 3.0 | 97.0 |
| PaddleOCR | pretrained | valid | destination | 6 | 28.2 | 62.5 | 33.3 |
| PaddleOCR | pretrained | valid | route | 12 | 21.2 | 59.5 | 25.0 |
| PaddleOCR | pretrained | valid | all | 51 | 18.0 | 38.4 | 72.5 |
| PaddleOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | valid | number | 33 | 4.6 | 6.1 | 93.9 |
| PaddleOCR | finetuned | valid | destination | 6 | 26.8 | 62.5 | 50.0 |
| PaddleOCR | finetuned | valid | route | 12 | 14.5 | 27.0 | 50.0 |
| PaddleOCR | finetuned | valid | all | 51 | 14.6 | 25.6 | 78.4 |
| PaddleOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
