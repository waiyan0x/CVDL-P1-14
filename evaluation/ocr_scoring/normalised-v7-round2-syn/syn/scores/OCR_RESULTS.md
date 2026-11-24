# OCR results

Scoring: normalised (casefold, whitespace collapsed).
Failed/missing predictions count as empty strings.

## Table 1: annotation crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained | train | number | 280 | 33.8 | 46.8 | 56.4 |
| EasyOCR | pretrained | train | destination | 62 | 55.6 | 84.3 | 9.7 |
| EasyOCR | pretrained | train | route | 42 | 48.8 | 90.1 | 2.4 |
| EasyOCR | pretrained | train | all | 384 | 46.4 | 67.4 | 43.0 |
| EasyOCR | pretrained | valid | number | 43 | 23.7 | 39.5 | 60.5 |
| EasyOCR | pretrained | valid | destination | 19 | 45.4 | 77.4 | 0.0 |
| EasyOCR | pretrained | valid | route | 17 | 49.0 | 88.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 79 | 42.9 | 70.5 | 32.9 |
| EasyOCR | pretrained | test | number | 24 | 7.5 | 16.7 | 83.3 |
| EasyOCR | pretrained | test | destination | 17 | 38.6 | 67.3 | 23.5 |
| EasyOCR | pretrained | test | route | 4 | 36.7 | 83.3 | 0.0 |
| EasyOCR | pretrained | test | all | 45 | 32.7 | 57.4 | 53.3 |
| EasyOCR | finetuned | train | number | 280 | 10.6 | 10.7 | 92.5 |
| EasyOCR | finetuned | train | destination | 62 | 23.2 | 45.5 | 48.4 |
| EasyOCR | finetuned | train | route | 42 | 18.6 | 35.5 | 47.6 |
| EasyOCR | finetuned | train | all | 384 | 17.7 | 26.6 | 80.5 |
| EasyOCR | finetuned | valid | number | 43 | 7.9 | 11.6 | 88.4 |
| EasyOCR | finetuned | valid | destination | 19 | 22.1 | 40.3 | 42.1 |
| EasyOCR | finetuned | valid | route | 17 | 23.5 | 58.8 | 11.8 |
| EasyOCR | finetuned | valid | all | 79 | 20.1 | 38.5 | 60.8 |
| EasyOCR | finetuned | test | number | 24 | 4.5 | 12.5 | 87.5 |
| EasyOCR | finetuned | test | destination | 17 | 21.0 | 51.9 | 23.5 |
| EasyOCR | finetuned | test | route | 4 | 27.8 | 55.6 | 0.0 |
| EasyOCR | finetuned | test | all | 45 | 19.5 | 42.6 | 55.6 |
| Public TrOCR | pretrained | train | number | 280 | 25.6 | 35.0 | 67.9 |
| Public TrOCR | pretrained | train | destination | 62 | 41.1 | 78.1 | 11.3 |
| Public TrOCR | pretrained | train | route | 42 | 30.4 | 63.6 | 28.6 |
| Public TrOCR | pretrained | train | all | 384 | 32.8 | 54.2 | 54.4 |
| Public TrOCR | pretrained | valid | number | 43 | 13.2 | 25.6 | 74.4 |
| Public TrOCR | pretrained | valid | destination | 19 | 19.1 | 48.4 | 31.6 |
| Public TrOCR | pretrained | valid | route | 17 | 15.0 | 41.2 | 29.4 |
| Public TrOCR | pretrained | valid | all | 79 | 16.4 | 39.7 | 54.4 |
| Public TrOCR | pretrained | test | number | 24 | 3.0 | 4.2 | 95.8 |
| Public TrOCR | pretrained | test | destination | 17 | 15.5 | 40.4 | 29.4 |
| Public TrOCR | pretrained | test | route | 4 | 38.0 | 72.2 | 25.0 |
| Public TrOCR | pretrained | test | all | 45 | 17.9 | 37.2 | 64.4 |
| Public TrOCR | finetuned | train | number | 280 | 15.3 | 20.4 | 82.5 |
| Public TrOCR | finetuned | train | destination | 62 | 42.6 | 86.5 | 1.6 |
| Public TrOCR | finetuned | train | route | 42 | 49.1 | 91.7 | 7.1 |
| Public TrOCR | finetuned | train | all | 384 | 35.4 | 55.6 | 61.2 |
| Public TrOCR | finetuned | valid | number | 43 | 17.5 | 32.6 | 67.4 |
| Public TrOCR | finetuned | valid | destination | 19 | 50.4 | 83.9 | 0.0 |
| Public TrOCR | finetuned | valid | route | 17 | 49.0 | 98.0 | 5.9 |
| Public TrOCR | finetuned | valid | all | 79 | 43.8 | 74.4 | 38.0 |
| Public TrOCR | finetuned | test | number | 24 | 14.9 | 29.2 | 70.8 |
| Public TrOCR | finetuned | test | destination | 17 | 35.6 | 78.8 | 5.9 |
| Public TrOCR | finetuned | test | route | 4 | 48.1 | 88.9 | 0.0 |
| Public TrOCR | finetuned | test | all | 45 | 34.6 | 68.1 | 40.0 |
| PaddleOCR | pretrained | train | number | 280 | 11.8 | 16.4 | 84.6 |
| PaddleOCR | pretrained | train | destination | 62 | 31.4 | 70.8 | 19.4 |
| PaddleOCR | pretrained | train | route | 42 | 23.5 | 59.5 | 31.0 |
| PaddleOCR | pretrained | train | all | 384 | 22.6 | 42.1 | 68.2 |
| PaddleOCR | pretrained | valid | number | 43 | 2.6 | 2.3 | 97.7 |
| PaddleOCR | pretrained | valid | destination | 19 | 14.9 | 33.9 | 57.9 |
| PaddleOCR | pretrained | valid | route | 17 | 17.0 | 54.9 | 29.4 |
| PaddleOCR | pretrained | valid | all | 79 | 13.5 | 32.1 | 73.4 |
| PaddleOCR | pretrained | test | number | 24 | 3.0 | 8.3 | 91.7 |
| PaddleOCR | pretrained | test | destination | 17 | 8.2 | 26.9 | 41.2 |
| PaddleOCR | pretrained | test | route | 4 | 29.1 | 72.2 | 0.0 |
| PaddleOCR | pretrained | test | all | 45 | 11.6 | 30.9 | 64.4 |
| PaddleOCR | finetuned | train | number | 280 | 11.7 | 11.1 | 92.9 |
| PaddleOCR | finetuned | train | destination | 62 | 8.1 | 16.3 | 77.4 |
| PaddleOCR | finetuned | train | route | 42 | 13.8 | 31.4 | 71.4 |
| PaddleOCR | finetuned | train | all | 384 | 10.9 | 16.9 | 88.0 |
| PaddleOCR | finetuned | valid | number | 43 | 3.5 | 4.7 | 95.3 |
| PaddleOCR | finetuned | valid | destination | 19 | 9.5 | 17.7 | 68.4 |
| PaddleOCR | finetuned | valid | route | 17 | 11.7 | 31.4 | 52.9 |
| PaddleOCR | finetuned | valid | all | 79 | 9.3 | 18.6 | 79.7 |
| PaddleOCR | finetuned | test | number | 24 | 0.0 | 0.0 | 100.0 |
| PaddleOCR | finetuned | test | destination | 17 | 7.7 | 21.2 | 64.7 |
| PaddleOCR | finetuned | test | route | 4 | 24.1 | 50.0 | 25.0 |
| PaddleOCR | finetuned | test | all | 45 | 9.8 | 21.3 | 80.0 |

## Table 2: detector crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained | valid | number | 33 | 16.1 | 24.2 | 75.8 |
| EasyOCR | pretrained | valid | destination | 6 | 57.7 | 81.2 | 16.7 |
| EasyOCR | pretrained | valid | route | 12 | 51.5 | 89.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 51 | 43.3 | 62.8 | 51.0 |
| EasyOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | valid | number | 33 | 8.0 | 9.1 | 90.9 |
| EasyOCR | finetuned | valid | destination | 6 | 29.6 | 56.2 | 50.0 |
| EasyOCR | finetuned | valid | route | 12 | 29.1 | 56.8 | 16.7 |
| EasyOCR | finetuned | valid | all | 51 | 23.5 | 38.4 | 68.6 |
| EasyOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | valid | number | 33 | 11.5 | 18.2 | 81.8 |
| Public TrOCR | pretrained | valid | destination | 6 | 33.8 | 68.8 | 50.0 |
| Public TrOCR | pretrained | valid | route | 12 | 24.8 | 37.8 | 33.3 |
| Public TrOCR | pretrained | valid | all | 51 | 23.2 | 36.0 | 66.7 |
| Public TrOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | valid | number | 33 | 20.7 | 36.4 | 63.6 |
| Public TrOCR | finetuned | valid | destination | 6 | 50.7 | 81.2 | 0.0 |
| Public TrOCR | finetuned | valid | route | 12 | 52.1 | 100.0 | 0.0 |
| Public TrOCR | finetuned | valid | all | 51 | 43.3 | 72.1 | 41.2 |
| Public TrOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | valid | number | 33 | 3.4 | 3.0 | 97.0 |
| PaddleOCR | pretrained | valid | destination | 6 | 29.6 | 68.8 | 33.3 |
| PaddleOCR | pretrained | valid | route | 12 | 21.2 | 59.5 | 25.0 |
| PaddleOCR | pretrained | valid | all | 51 | 18.3 | 39.5 | 72.5 |
| PaddleOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | valid | number | 33 | 3.4 | 3.0 | 97.0 |
| PaddleOCR | finetuned | valid | destination | 6 | 14.1 | 37.5 | 50.0 |
| PaddleOCR | finetuned | valid | route | 12 | 17.6 | 35.1 | 41.7 |
| PaddleOCR | finetuned | valid | all | 51 | 13.0 | 23.3 | 78.4 |
| PaddleOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
