#!/usr/bin/env bash
# Re-run all nine model versions (pretrained, fine-tuned round 1, fine-tuned
# round 2 synthetic) on validation with frozen layout v4-lines-v3. Commands
# match the -valid-layoutv2 runs exactly; only the layout manifest differs
# (A052, A094, P046, P087 now have one line each instead of no layout).
#
# Usage: scripts/run_valid_layoutv3.sh [easyocr|trocr|paddleocr ...]
# Outputs: .cache/ocr_runs/<model>-<version>-valid-layoutv3/ (full run folders).
# Existing outputs are skipped; the runners refuse an existing folder.
set -euo pipefail
cd "$(dirname "$0")/.."

TORCH_PY=.venv/bin/python
PADDLE_PY=.cache/paddle-baseline-env/bin/python
FROM="DRIVE/CVDL-OCR-finetune"
LAYOUT=evaluation/ocr_layouts/v4-lines-v3/manifest.json
VALID=(--workspace evaluation/ocr_annotations/v4-reviewed-01 --split valid --line-layout "$LAYOUT")

run() {  # model version
  local model=$1 version=$2 out=.cache/ocr_runs/$1-$2-valid-layoutv3 best="" run_id=""
  if [ -d "$out" ]; then echo "Exists, skipping: $out"; return; fi
  case "$version" in
    finetuned)    best=.cache/finetuned/$model;     run_id=20261117-031848 ;;
    finetunedsyn) best=.cache/finetuned-syn/$model; run_id=20261118-084149 ;;
  esac
  local ft=()
  [ -n "$best" ] && ft=(--finetuned-from "$FROM/$model/$run_id")
  case "$model" in
    easyocr)
      local net=()
      [ -n "$best" ] && net=(--cache "$best" --recog-network eds_english_g2)
      "$TORCH_PY" scripts/run_easyocr_crops.py --engine easyocr ${net[@]+"${net[@]}"} ${ft[@]+"${ft[@]}"} \
        --device mps --seed 0 --warmup 3 "${VALID[@]}" --output "$out" ;;
    trocr)
      local cache=()
      [ -n "$best" ] && cache=(--cache "$best")
      "$TORCH_PY" scripts/run_easyocr_crops.py --engine trocr ${cache[@]+"${cache[@]}"} ${ft[@]+"${ft[@]}"} \
        --device mps --seed 0 --warmup 3 "${VALID[@]}" --output "$out" ;;
    paddleocr)
      "$PADDLE_PY" scripts/run_paddle_crops.py --model-dir "${best:-.cache/paddle-en-v5}" ${ft[@]+"${ft[@]}"} \
        --warmup 3 "${VALID[@]}" --output "$out" ;;
  esac
  echo "Done: $out"
}

for model in ${@:-paddleocr easyocr trocr}; do
  for version in pretrained finetuned finetunedsyn; do run "$model" "$version"; done
done
