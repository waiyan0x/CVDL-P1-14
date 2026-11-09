# Human verification batch 01

27 crops: nine service numbers, nine destinations and nine route-text crops. Each row is pending. No human labels or identity/date have been supplied.

Open sheet_01.png through sheet_03.png; native/ contains byte-identical crops with neutral IDs. Read each variant separately. Sheets and submission.template.csv hide the AI transcription; the supplied field label must also be checked. This small deterministic candidate batch is not an accuracy sample.

Copy submission.template.csv to a reviewer-named CSV. Keep review_id, review_sheet, native_crop, crop_sha256 and supplied_label unchanged. Enter visible text, actual newlines, field_status (present/blank/absent/wrong_field), label_confirmed (yes/no/uncertain), legibility (full/partial/illegible/not_applicable), review_status (reviewed/needs_resolution), your actual reviewer identity, reviewer_type=human, actual ISO review date, and any notes.

Follow repository docs/OCR_TRANSCRIPTION_RULES.md: preserve case, punctuation and abbreviations; one word space; actual line breaks. Read only this crop. Do not complete text using another variant, filenames, route knowledge or AI/OCR suggestions. Use [UNK] for each unresolved span: partial requires readable text plus [UNK]; illegible is exactly [UNK]. Blank/absent require explicit states and empty text. Uncertain field presence stays needs_resolution.

In chat, you may return reviewer name, actual review date, and each neutral ID's text/state instead of editing the CSV. Independent human verification is not established merely by preparing this batch. Full-photo grouping remains unresolved until the missing full dataset is restored; no batch row is training-ready.
