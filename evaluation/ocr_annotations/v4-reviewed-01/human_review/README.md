# Human transcription batches

All 271 crops are pending. No text labels, reviewer identities or review dates were supplied by this export.

A = annotation crops (157); P = prediction crops (114). Each numbered sheet contains up to nine crops. Only neutral IDs and supplied field names appear on sheets; filenames and IoU candidates are not transcription prompts.

Read repository-root `docs/OCR_TRANSCRIPTION_RULES.md` and `docs/OCR_ANNOTATION_PACKAGE.md` before labelling. Sheets use nearest-neighbour display scaling only; inspect the native crop or same-image panel context if a thumbnail is insufficient. Missing context stays unresolved.

Copy the appropriate submission template to a new reviewer-named CSV. Keep review_id, crop identity, source metadata and review_sheet unchanged. Supply visible transcription (actual line breaks in quoted CSV cells), field_status, legibility, actual reviewer/date and exclusions. Uncertain cases need independent review; never guess from the route CSV or filenames. Predicted crops require their own transcription and correspondence review.

For review in chat, return reviewer name, actual review date and each ID's visible text, line breaks, field status, legibility and any exclusion. Use [UNK] for unresolved spans; say blank or absent explicitly. Do not type a guessed completion. The assistant can record submitted labels as a new review export; it cannot claim to be a human reviewer. Group and image review remain separate requirements before scoring.
