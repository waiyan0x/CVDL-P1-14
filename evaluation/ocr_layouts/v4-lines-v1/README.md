# Frozen OCR line layout: v4-lines-v1

Reviewer: **Codex (AI)**; review date **2026-11-08**. No independent human review is attested.

All 271 crops visually inspected. Accepted layout: 251; unresolved: 20; multiline crops: 29; accepted line regions: 280; changed from v2 proposals: 50.

`manifest.json` is the shared geometry contract; verify `manifest.sha256` before use. `review_decisions.json` records every explicit decision. `previews/` preserves native-size overlays; `lines/` holds diagnostic extracted regions. `unresolved.csv` lists exclusions and reasons.

This is manually reviewed layout information for a recognition-only diagnostic. It does not establish automatic line-detection performance, correct text, dataset independence or accuracy. Reuse the same manifest/regions across engines and report layout coverage separately. Unresolved crops must not fall back to automatic segmentation or full-crop recognition.

Source images, crops, transcriptions, model weights, previous OCR runs and reference matching are unchanged. No recognition, scoring or training was run during this freeze. Use a new version/directory for corrections; never overwrite this version.
