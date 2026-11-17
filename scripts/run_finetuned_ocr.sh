#!/usr/bin/env bash
# Step 6: run the three fine-tuned OCR models on the same train/valid/test crops,
# frozen layouts and settings as the pretrained runs in evaluation/ocr_runs/.
# Full run folders go to .cache/ocr_runs/<name>/; predictions.jsonl and
# report.json are then copied to evaluation/ocr_runs/<name>/ for Git.
#
# Usage: scripts/run_finetuned_ocr.sh [easyocr|trocr|paddleocr|pretrained-test ...]
#        (default: the three fine-tuned models; pretrained-test only when named)
# Needs best/ folders from Drive in .cache/finetuned/{easyocr,trocr,paddleocr}/.
# Existing outputs are never overwritten; the runners refuse an existing folder.
set -euo pipefail
cd "$(dirname "$0")/.."

RUN=20261117-031848
FROM="DRIVE/CVDL-OCR-finetune"
TORCH_PY=.venv/bin/python
PADDLE_PY=.cache/paddle-baseline-env/bin/python
ANNOTATIONS=evaluation/ocr_annotations/v4-reviewed-01
TRAIN_SOURCE=.cache/ocr_training/v4-reviewed-01-ai-01/source

# Same split inputs as the pretrained runs' command.json.
split_args() {
  case "$1" in
    train) echo --workspace "$TRAIN_SOURCE" --crop-root "$TRAIN_SOURCE" \
             --review-manifest evaluation/ocr_review/human-verification-20261113/training.source.csv \
             --split train --line-layout .cache/ocr_layouts/train-auto-20261115-01/manifest.json ;;
    valid) echo --workspace "$ANNOTATIONS" --split valid \
             --line-layout evaluation/ocr_layouts/v4-lines-v1/manifest.json ;;
    test)  echo --workspace "$ANNOTATIONS" --crop-root .runtime/ocr-text-dataset-20261116 \
             --review-manifest evaluation/ocr_review/test-20261116/test.source.csv \
             --split test --line-layout evaluation/ocr_layouts/v4-test-automatic-v1/manifest.json ;;
  esac
}

publish() {
  local name=$1
  mkdir evaluation/ocr_runs/"$name"
  cp .cache/ocr_runs/"$name"/predictions.jsonl .cache/ocr_runs/"$name"/report.json evaluation/ocr_runs/"$name"/
  echo "Saved evaluation/ocr_runs/$name"
}

run_model() {
  local model=$1 best=.cache/finetuned/$1
  [ -d "$best" ] || { echo "Missing $best: download $FROM/$model/$RUN/best from Drive" >&2; exit 1; }
  for split in train valid test; do
    local name=$model-finetuned-$split
    # shellcheck disable=SC2046
    case "$model" in
      easyocr) "$TORCH_PY" scripts/run_easyocr_crops.py --engine easyocr --cache "$best" \
                 --recog-network eds_english_g2 --finetuned-from "$FROM/easyocr/$RUN" \
                 --device mps --seed 0 --warmup 3 $(split_args $split) --output .cache/ocr_runs/$name ;;
      trocr)   "$TORCH_PY" scripts/run_easyocr_crops.py --engine trocr --cache "$best" \
                 --finetuned-from "$FROM/trocr/$RUN" \
                 --device mps --seed 0 --warmup 3 $(split_args $split) --output .cache/ocr_runs/$name ;;
      paddleocr) "$PADDLE_PY" scripts/run_paddle_crops.py --model-dir "$best" \
                 --finetuned-from "$FROM/paddleocr/$RUN" \
                 --warmup 3 $(split_args $split) --output .cache/ocr_runs/$name ;;
    esac
    publish "$name"
  done
}

# Pretrained TrOCR/Paddle test runs (EasyOCR's already exists), same inputs and caches
# as their pretrained valid/train runs.
run_pretrained_test() {
  "$TORCH_PY" scripts/run_easyocr_crops.py --engine trocr --device mps --seed 0 --warmup 3 \
    $(split_args test) --output .cache/ocr_runs/trocr-pretrained-test
  publish trocr-pretrained-test
  "$PADDLE_PY" scripts/run_paddle_crops.py --model-dir .cache/paddle-en-v5 --warmup 3 \
    $(split_args test) --output .cache/ocr_runs/paddleocr-pretrained-test
  publish paddleocr-pretrained-test
}

for model in "${@:-easyocr trocr paddleocr}"; do
  for m in $model; do
    if [ "$m" = pretrained-test ]; then run_pretrained_test; else run_model "$m"; fi
  done
done
