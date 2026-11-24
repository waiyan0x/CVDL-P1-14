# Tidy-up, 17 November 2026

1. **Absolute paths in CSVs.** Six tracked CSVs had `crop_local_path` values
   starting `/Users/tanyilin/Downloads/CVDL-P1-14/`; the prefix was removed, so
   paths are repo-relative (`.cache/...`). Every file recording one of their
   SHA-256 hashes was updated, following chains; `hash_updates.json` lists each
   file's old and new hash. Snapshot `ocr_scoring/normalised-v5-step6-20261117/`
   was rebuilt with `scripts/build_step6_scoring.py`; its scores, tables and
   per-crop records are byte-identical (only the manifest fingerprint changed).
   Untracked artifacts made earlier (Colab bundle, Drive copies) still carry the
   old hashes. Non-CSV files (52, mostly JSON run reports) were not changed.
2. **Segmentation previews.** Removed `segmentation_previews/` (1,084 PNGs) from
   four superseded EasyOCR runs (`easyocr-v4-mps-baseline-01/-02`,
   `easyocr-v4-mps-fixed-lines-01/-02`). Kept: latest EasyOCR run
   (`easyocr-v4-mps-fixed-lines-20261112-01`, also the scored pretrained run) and
   both TrOCR runs (`-20261112-01` scored, `-20261112-02` latest). Recover with
   `git checkout 63f80ba -- <run>/segmentation_previews`.
3. **Docs.** The 12 `docs/OCR_*.md` documents moved unchanged to
   `docs/archive/ocr/`; `docs/OCR_README.md` is the short current summary. Links
   in 15 files (READMEs, `docs/EVALUATION.md`, five scripts) were repointed.
