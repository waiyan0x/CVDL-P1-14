#!/usr/bin/env bash
# Round 2 step 6: run models fine-tuned on the synthetic bundle
# (ocr_finetune_bundle-20261117-syn.zip) on exactly the same crops and frozen
# layouts as the round 1 models, so only the training data differs.
#
# Usage: scripts/run_synthetic_finetuned_ocr.sh RUN_ID [easyocr|trocr|paddleocr ...]
#   RUN_ID   Colab run folder name, e.g. 20261118-0930xx
#   Needs the run's best/ folders imported to .cache/finetuned-syn/<model>/
#   (same file layout as .cache/finetuned/<model>/).
#
# Outputs: evaluation/ocr_runs/<model>-finetunedsyn-{valid-layoutv2,test}/ (published),
#          .cache/ocr_runs/<model>-finetunedsyn-{train,routeholdout,routeholdout-partial}/.
# Existing outputs are never overwritten; the runners refuse an existing folder.
set -euo pipefail
cd "$(dirname "$0")/.."

RUN=${1:?RUN_ID required}; shift
FROM="DRIVE/CVDL-OCR-finetune"
TORCH_PY=.venv/bin/python
PADDLE_PY=.cache/paddle-baseline-env/bin/python
ANNOTATIONS=evaluation/ocr_annotations/v4-reviewed-01
TRAIN_SOURCE=.cache/ocr_training/v4-reviewed-01-ai-01/source
HOLD=.runtime/route-holdout-20261117
HOLD_REVIEW=evaluation/ocr_review/route-holdout-20261117

split_args() {
  case "$1" in
    valid-layoutv2) echo --workspace "$ANNOTATIONS" --split valid \
             --line-layout evaluation/ocr_layouts/v4-lines-v2/manifest.json ;;
    test)  echo --workspace "$ANNOTATIONS" --crop-root .runtime/ocr-text-dataset-20261116 \
             --review-manifest evaluation/ocr_review/test-20261116/test.source.csv \
             --split test --line-layout evaluation/ocr_layouts/v4-test-automatic-v1/manifest.json ;;
    train) echo --workspace "$TRAIN_SOURCE" --crop-root "$TRAIN_SOURCE" \
             --review-manifest evaluation/ocr_review/human-verification-20261113/training.source.csv \
             --split train --line-layout .cache/ocr_layouts/train-auto-20261115-01/manifest.json ;;
    routeholdout) echo --workspace "$HOLD" --crop-root "$HOLD" \
             --review-manifest $HOLD_REVIEW/route_holdout.source.csv \
             --split train --line-layout evaluation/ocr_layouts/route-holdout-automatic-v1/manifest.json ;;
    routeholdout-partial) echo --workspace "$HOLD" --crop-root "$HOLD" \
             --review-manifest $HOLD_REVIEW/route_holdout_partial.inventory.csv \
             --split train --line-layout evaluation/ocr_layouts/route-holdout-partial-automatic-v1/manifest.json ;;
  esac
}

run_model() {
  local model=$1 best=.cache/finetuned-syn/$1
  [ -d "$best" ] || { echo "Missing $best: import $FROM/$model/$RUN/best first" >&2; exit 1; }
  for split in valid-layoutv2 test routeholdout routeholdout-partial train; do
    local name=$model-finetunedsyn-$split out=.cache/ocr_runs/$model-finetunedsyn-$split
    if [ -d "$out" ]; then echo "Exists, skipping: $out"; continue; fi
    # shellcheck disable=SC2046
    case "$model" in
      easyocr) "$TORCH_PY" scripts/run_easyocr_crops.py --engine easyocr --cache "$best" \
                 --recog-network eds_english_g2 --finetuned-from "$FROM/easyocr/$RUN" \
                 --device mps --seed 0 --warmup 3 $(split_args $split) --output "$out" ;;
      trocr)   "$TORCH_PY" scripts/run_easyocr_crops.py --engine trocr --cache "$best" \
                 --finetuned-from "$FROM/trocr/$RUN" \
                 --device mps --seed 0 --warmup 3 $(split_args $split) --output "$out" ;;
      paddleocr) "$PADDLE_PY" scripts/run_paddle_crops.py --model-dir "$best" \
                 --finetuned-from "$FROM/paddleocr/$RUN" \
                 --warmup 3 $(split_args $split) --output "$out" ;;
    esac
    case "$split" in
      valid-layoutv2|test)
        mkdir evaluation/ocr_runs/"$name"
        cp "$out"/predictions.jsonl "$out"/report.json evaluation/ocr_runs/"$name"/
        echo "Saved evaluation/ocr_runs/$name" ;;
    esac
  done
}

for model in "${@:-paddleocr trocr easyocr}"; do
  for m in $model; do run_model "$m"; done
done
