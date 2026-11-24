# Fixed 5,000-example training subset — 20 November 2026

This limit counts actual exported line-image/text training pairs: 366 original
real pairs + 4,634 new pairs = 5,000 per model. It is not 5,000 original field
boxes. The pairs come from 363 usable real source crops (24 of the original 387
were skipped by the existing exporter) and 4,548 selected new source crops.
Source crops can contribute more than one line. The original real pairs are
unchanged. All 100 user-confirmed review source crops are retained.

Seed 0; synthetic line quotas number 1,854, destination 1,854, route 926. Whole
source-crop line groups are retained. Selection includes the reviewed sample,
then seeded field-stratified fill; it is not an independent random test sample.
selection.json records every selected source ID; bundle.lock.json freezes hashes.

Notebook: colab/ocr_finetune/ocr_finetune_5k.ipynb.
Upload unchanged filenames to My Drive/DRIVE:
- ocr_finetune_bundle-20261120-5k.zip
- ocr_finetune_code-20261120-earlystop.zip
- synthetic_v2_human_spotcheck.csv (the previously completed CSV)

T4, batch 32, maximum 20 epochs, validation CER patience 3 for all three models.
Maximum 157 steps/epoch, 3,140 steps per model. CPU smoke checks must use this
new input/code combination. They do not establish full batch-32 GPU memory fit.
Paddle early-stop/export integration still needs Colab execution verification.

Validation remains 130 eligible real crops with frozen v3 line geometry;
validation image bytes, text, and weights lock are unchanged. No test images or
labels are in training. The 175 held-out scoring references remain separately
available in evaluation/ocr_dataset/reviewed-20261119/.

No 5k weights, accuracy or improvement is claimed. Return best/ ZIPs, configs,
epoch logs, selection files, RUN_ID and input receipt for actual evaluation.
Only a benchmark-qualified model can replace the current selected model, with
new matching_inputs.jsonl and weight hashes. The current verified round 1
PaddleOCR delivery is .runtime/ocr-verified-selected-model-20261120.zip, not a
5k-trained checkpoint. Nothing has been pushed.
