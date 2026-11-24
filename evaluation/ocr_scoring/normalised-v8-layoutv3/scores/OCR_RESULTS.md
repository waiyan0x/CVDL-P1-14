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
| EasyOCR | pretrained | valid | destination | 19 | 42.7 | 77.4 | 0.0 |
| EasyOCR | pretrained | valid | route | 17 | 49.0 | 88.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 79 | 41.7 | 70.5 | 32.9 |
| EasyOCR | pretrained | test | number | 24 | 7.5 | 16.7 | 83.3 |
| EasyOCR | pretrained | test | destination | 17 | 38.6 | 67.3 | 23.5 |
| EasyOCR | pretrained | test | route | 4 | 36.7 | 83.3 | 0.0 |
| EasyOCR | pretrained | test | all | 45 | 32.7 | 57.4 | 53.3 |
| EasyOCR | finetuned | train | number | 280 | 10.4 | 11.1 | 92.1 |
| EasyOCR | finetuned | train | destination | 62 | 24.1 | 47.8 | 46.8 |
| EasyOCR | finetuned | train | route | 42 | 20.8 | 46.3 | 45.2 |
| EasyOCR | finetuned | train | all | 384 | 18.6 | 29.7 | 79.7 |
| EasyOCR | finetuned | valid | number | 43 | 10.5 | 18.6 | 81.4 |
| EasyOCR | finetuned | valid | destination | 19 | 23.7 | 43.5 | 42.1 |
| EasyOCR | finetuned | valid | route | 17 | 34.0 | 76.5 | 11.8 |
| EasyOCR | finetuned | valid | all | 79 | 25.4 | 47.4 | 57.0 |
| EasyOCR | finetuned | test | number | 24 | 3.0 | 8.3 | 91.7 |
| EasyOCR | finetuned | test | destination | 17 | 22.7 | 51.9 | 29.4 |
| EasyOCR | finetuned | test | route | 4 | 34.2 | 77.8 | 0.0 |
| EasyOCR | finetuned | test | all | 45 | 21.6 | 45.7 | 60.0 |
| Public TrOCR | pretrained | train | number | 280 | 25.6 | 35.0 | 67.9 |
| Public TrOCR | pretrained | train | destination | 62 | 41.1 | 78.1 | 11.3 |
| Public TrOCR | pretrained | train | route | 42 | 30.4 | 63.6 | 28.6 |
| Public TrOCR | pretrained | train | all | 384 | 32.8 | 54.2 | 54.4 |
| Public TrOCR | pretrained | valid | number | 43 | 11.4 | 25.6 | 74.4 |
| Public TrOCR | pretrained | valid | destination | 19 | 13.7 | 46.8 | 31.6 |
| Public TrOCR | pretrained | valid | route | 17 | 15.0 | 41.2 | 29.4 |
| Public TrOCR | pretrained | valid | all | 79 | 13.8 | 39.1 | 54.4 |
| Public TrOCR | pretrained | test | number | 24 | 3.0 | 4.2 | 95.8 |
| Public TrOCR | pretrained | test | destination | 17 | 15.5 | 40.4 | 29.4 |
| Public TrOCR | pretrained | test | route | 4 | 38.0 | 72.2 | 25.0 |
| Public TrOCR | pretrained | test | all | 45 | 17.9 | 37.2 | 64.4 |
| Public TrOCR | finetuned | train | number | 280 | 11.0 | 10.0 | 93.2 |
| Public TrOCR | finetuned | train | destination | 62 | 25.1 | 53.9 | 30.6 |
| Public TrOCR | finetuned | train | route | 42 | 20.5 | 38.8 | 64.3 |
| Public TrOCR | finetuned | train | all | 384 | 19.1 | 29.5 | 79.9 |
| Public TrOCR | finetuned | valid | number | 43 | 5.3 | 9.3 | 90.7 |
| Public TrOCR | finetuned | valid | destination | 19 | 11.8 | 40.3 | 36.8 |
| Public TrOCR | finetuned | valid | route | 17 | 15.4 | 39.2 | 35.3 |
| Public TrOCR | finetuned | valid | all | 79 | 12.0 | 31.4 | 65.8 |
| Public TrOCR | finetuned | test | number | 24 | 4.5 | 8.3 | 91.7 |
| Public TrOCR | finetuned | test | destination | 17 | 15.5 | 44.2 | 29.4 |
| Public TrOCR | finetuned | test | route | 4 | 34.2 | 61.1 | 25.0 |
| Public TrOCR | finetuned | test | all | 45 | 17.4 | 38.3 | 62.2 |
| PaddleOCR | pretrained | train | number | 280 | 11.8 | 16.4 | 84.6 |
| PaddleOCR | pretrained | train | destination | 62 | 31.4 | 70.8 | 19.4 |
| PaddleOCR | pretrained | train | route | 42 | 23.5 | 59.5 | 31.0 |
| PaddleOCR | pretrained | train | all | 384 | 22.6 | 42.1 | 68.2 |
| PaddleOCR | pretrained | valid | number | 43 | 0.9 | 2.3 | 97.7 |
| PaddleOCR | pretrained | valid | destination | 19 | 8.8 | 29.0 | 57.9 |
| PaddleOCR | pretrained | valid | route | 17 | 17.0 | 54.9 | 29.4 |
| PaddleOCR | pretrained | valid | all | 79 | 10.6 | 30.1 | 73.4 |
| PaddleOCR | pretrained | test | number | 24 | 3.0 | 8.3 | 91.7 |
| PaddleOCR | pretrained | test | destination | 17 | 8.2 | 26.9 | 41.2 |
| PaddleOCR | pretrained | test | route | 4 | 29.1 | 72.2 | 0.0 |
| PaddleOCR | pretrained | test | all | 45 | 11.6 | 30.9 | 64.4 |
| PaddleOCR | finetuned | train | number | 280 | 8.9 | 9.3 | 93.2 |
| PaddleOCR | finetuned | train | destination | 62 | 9.2 | 16.3 | 82.3 |
| PaddleOCR | finetuned | train | route | 42 | 13.1 | 22.3 | 81.0 |
| PaddleOCR | finetuned | train | all | 384 | 10.2 | 14.2 | 90.1 |
| PaddleOCR | finetuned | valid | number | 43 | 0.9 | 2.3 | 97.7 |
| PaddleOCR | finetuned | valid | destination | 19 | 6.1 | 17.7 | 57.9 |
| PaddleOCR | finetuned | valid | route | 17 | 11.3 | 25.5 | 52.9 |
| PaddleOCR | finetuned | valid | all | 79 | 7.2 | 16.0 | 78.5 |
| PaddleOCR | finetuned | test | number | 24 | 0.0 | 0.0 | 100.0 |
| PaddleOCR | finetuned | test | destination | 17 | 5.2 | 15.4 | 70.6 |
| PaddleOCR | finetuned | test | route | 4 | 24.1 | 55.6 | 25.0 |
| PaddleOCR | finetuned | test | all | 45 | 8.2 | 19.1 | 82.2 |

## Table 2: detector crops

| Model | Version | Split | Field | Crops (n) | CER (%) | WER (%) | Exact match (%) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| EasyOCR | pretrained | valid | number | 33 | 14.9 | 24.2 | 75.8 |
| EasyOCR | pretrained | valid | destination | 6 | 57.7 | 81.2 | 16.7 |
| EasyOCR | pretrained | valid | route | 12 | 49.1 | 89.2 | 0.0 |
| EasyOCR | pretrained | valid | all | 51 | 41.8 | 62.8 | 51.0 |
| EasyOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| EasyOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | valid | number | 33 | 9.2 | 12.1 | 87.9 |
| EasyOCR | finetuned | valid | destination | 6 | 45.1 | 75.0 | 33.3 |
| EasyOCR | finetuned | valid | route | 12 | 30.9 | 70.3 | 16.7 |
| EasyOCR | finetuned | valid | all | 51 | 28.2 | 48.8 | 64.7 |
| EasyOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| EasyOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | valid | number | 33 | 9.2 | 18.2 | 81.8 |
| Public TrOCR | pretrained | valid | destination | 6 | 33.8 | 68.8 | 50.0 |
| Public TrOCR | pretrained | valid | route | 12 | 19.4 | 35.1 | 33.3 |
| Public TrOCR | pretrained | valid | all | 51 | 19.8 | 34.9 | 66.7 |
| Public TrOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| Public TrOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | valid | number | 33 | 3.4 | 6.1 | 93.9 |
| Public TrOCR | finetuned | valid | destination | 6 | 25.4 | 43.8 | 50.0 |
| Public TrOCR | finetuned | valid | route | 12 | 25.5 | 40.5 | 25.0 |
| Public TrOCR | finetuned | valid | all | 51 | 19.5 | 27.9 | 72.5 |
| Public TrOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| Public TrOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | valid | number | 33 | 0.0 | 0.0 | 100.0 |
| PaddleOCR | pretrained | valid | destination | 6 | 29.6 | 68.8 | 33.3 |
| PaddleOCR | pretrained | valid | route | 12 | 15.2 | 54.1 | 25.0 |
| PaddleOCR | pretrained | valid | all | 51 | 14.2 | 36.0 | 74.5 |
| PaddleOCR | pretrained | test | number | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | destination | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | route | 0 | Not run | Not run | Not run |
| PaddleOCR | pretrained | test | all | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | valid | number | 33 | 2.3 | 6.1 | 93.9 |
| PaddleOCR | finetuned | valid | destination | 6 | 21.1 | 43.8 | 50.0 |
| PaddleOCR | finetuned | valid | route | 12 | 8.5 | 21.6 | 50.0 |
| PaddleOCR | finetuned | valid | all | 51 | 9.6 | 19.8 | 78.4 |
| PaddleOCR | finetuned | test | number | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | destination | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | route | 0 | Not run | Not run | Not run |
| PaddleOCR | finetuned | test | all | 0 | Not run | Not run | Not run |
