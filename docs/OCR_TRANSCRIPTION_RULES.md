# EDS crop transcription rules

Status: **proposal**, 5 November 2026. These rules are for human-reviewed LED
dot-matrix OCR ground truth, not seven-segment text. They contain no measured
results or coursework requirements. Field names and views follow the user's
current project context; the conventions below are proposed project decisions.
The worked examples are synthetic, not observations of supplied crops.

## CSV format and metadata

Use UTF-8 CSV with exactly these columns:

`crop_id,source_image,group_id,view,field,bbox,text,legibility,lighting,split`

| Column | Convention |
| --- | --- |
| `crop_id` | Unique crop path relative to a separately recorded crop root, including extension and subfolders. Keep paths stable. |
| `source_image` | Original uncropped image path relative to a separately recorded source root. Do not substitute the crop filename or guess parentage. |
| `group_id` | Reviewed original-source/burst group. All field crops, augmented variants and confirmed related frames in a group must share one split. A timestamp alone proposes a group; it does not confirm the same bus. |
| `view` | `front`, `side`, or `rear`, based on the bus surface carrying this display. An angled front remains `front`; an angled side remains `side`. |
| `field` | `front_eds_num`, `front_eds_destination`, or `front_eds_route`. These are dataset identifiers; the `front_` prefix does not override `view`. Service identifier, destination and route text remain distinct. |
| `bbox` | JSON array `[x1,y1,x2,y2]` in pixels of the upright, EXIF-oriented **source image**, with inclusive top-left and exclusive bottom-right. It describes the source region used to make the crop, not the crop's own dimensions. Use the documented transform for resized/rectified crops; leave blank if source coordinates are unavailable. CSV quotes this cell because it contains commas. |
| `text` | Human transcription under the rules below. Blank means unannotated, never an unreadable label. |
| `legibility` | `full`, `partial`, or `illegible`; blank until reviewed. |
| `lighting` | `day` or `night` from reliable image/context evidence. Leave blank if undetermined; do not infer night merely from a dark crop. |
| `split` | `train`, `valid`, or `test`. Preserve known dataset assignments initially; resolve duplicate/burst leakage before evaluation. Blank means unassigned. |

`front_eds_route` provisionally means the separately labelled route-information
region, including intermediate road/stop or VIA text where applicable. Confirm
this interpretation against the incoming annotation guide. Do not merge it with
the service number or destination. Flag wrong-field crops for correction or
exclusion outside this fixed-column CSV; never silently relabel them.

The requested schema has no source-dataset, augmentation, review, or quality-tag
columns. Keep a companion audit register keyed by `crop_id` for those facts,
reviewer/date, exclusions, original/variant relationships, transformations and
root paths. A filled CSV alone does not certify review or evaluation eligibility.

## Transcription conventions

Character repertoire: no closed alphabet is established yet. Preserve any
reliably readable displayed letter, digit or symbol, including non-Latin text;
do not restrict labels to characters seen in these examples. Use Unicode NFC
for stored text. Review unfamiliar characters rather than transliterating them.

1. **Visible text only.** Read the crop; consult the parent image to establish
   metadata and clipping, but never fill crop text from another frame, a route
   CSV, a filename, or knowledge of the bus route. Do not correct spelling or
   expand abbreviations. Natural spaces between LED dots are not text spaces.
2. **Letter case.** Preserve clearly visible uppercase/lowercase. Do not convert
   everything to uppercase. If case cannot be resolved, use an unreadable marker
   for that character/span instead of guessing.
3. **Spaces.** Use one ASCII space between visible words; collapse layout padding
   and repeated word-spacing to one space. No leading/trailing spaces per line.
   Do not insert spaces inside a service identifier because its glyphs are far
   apart. Ambiguous word boundaries require review rather than automatic repair.
4. **Punctuation.** Preserve visible punctuation, including periods, slashes,
   hyphens and parentheses. Use ordinary ASCII forms for ordinary LED glyphs
   (`-`, `'`, etc.); preserve a distinctly different readable Unicode symbol.
   Do not add punctuation from conventional spelling. An ambiguous punctuation
   mark is unreadable, not silently omitted.
5. **Multiple lines.** Read top to bottom, left to right within each line. Preserve
   each visible line break using an actual newline inside the quoted CSV `text`
   cell. Do not join lines or write the literal two characters `\n`. This applies
   to multiline destinations and route text. Ignore empty layout-only lines.
6. **Scrolling or cut-off text.** Label only the captured instant. If a word or
   field continuation is visibly clipped at either edge, place `[UNK]` at that
   edge and use `partial` when any text remains readable. Do not reconstruct the
   hidden suffix/prefix from another instant. An intact abbreviation is not
   automatically partial. A clearly blank field is not automatically scrolling.
7. **Unreadable characters.** Use `[UNK]` for each contiguous unresolved span,
   regardless of its unknown length. Use `1[UNK]A` when only the middle is
   uncertain; do not write `?`, `_`, or an invented character count. Preserve
   known spaces around an unresolved word; add no spaces when the span is inside
   a word. The marker is annotation syntax, not displayed text. If no character
   is reliably readable, use exactly `[UNK]` and `illegible`.
8. **Legibility.** `full`: all text in a complete field is readable, without
   `[UNK]`. `partial`: some text is readable but another span/continuation is
   unresolved or clipped; include at least one `[UNK]`. `illegible`: no text can
   be reliably transcribed; use exactly `[UNK]`. A damaged glyph that remains
   unambiguous may still be `full`; record the damage in the quality register.
9. **Blank or absent fields.** This template targets text-bearing crops. Leave
   such cases pending, record `blank_field`/`absent_field` in the companion
   register, and exclude them until a missing-field policy is agreed. Do not
   misuse `illegible` for a genuinely empty region or use blank `text` as truth.

Normal viewing and nearest-neighbour enlargement are permitted. Do not use
generative enhancement or OCR suggestions to decide ambiguous characters.
Have a second person review uncertainty and field assignments; disagreement
remains `[UNK]` until resolved from visible evidence.

## Worked examples (synthetic)

Each field has one full, one partial and one illegible example. `↵` below denotes
an actual newline in the CSV; the companion example CSV contains real newlines.
Boxes and timestamps in these examples are illustrative metadata only.

| Example crop | Field | Visible situation | Stored text | Legibility |
| --- | --- | --- | --- | --- |
| `examples/num_full.png` | `front_eds_num` | Every glyph in service identifier is clear. | `96B` | full |
| `examples/num_partial.png` | `front_eds_num` | First digit and suffix clear; middle digit unresolved. | `1[UNK]A` | partial |
| `examples/num_illegible.png` | `front_eds_num` | Lit field, but no reliable characters. | `[UNK]` | illegible |
| `examples/destination_full.png` | `front_eds_destination` | Two complete visible lines; abbreviation includes a period. | `ANG MO KIO↵INT.` | full |
| `examples/destination_partial.png` | `front_eds_destination` | `WOOD` is clear; remaining letters obscured. | `WOOD[UNK]` | partial |
| `examples/destination_illegible.png` | `front_eds_destination` | Glare prevents every character from being read. | `[UNK]` | illegible |
| `examples/route_full.png` | `front_eds_route` | Complete route-information line with slash. | `VIA A / B RD` | full |
| `examples/route_partial.png` | `front_eds_route` | Scrolling line: readable centre, visibly clipped at both edges. | `[UNK]SERANGOON[UNK]` | partial |
| `examples/route_illegible.png` | `front_eds_route` | Blur prevents every character from being read. | `[UNK]` | illegible |

## Scoring boundary

Primary raw-text CER and field exact match use reviewed, eligible `full` crops
only, before reference matching. Preserve case, punctuation and line breaks;
apply the same declared whitespace convention to references and predictions.
If normalized scores are also reported, label them separately. Report sample
counts and excluded partial/illegible counts per field to expose coverage.

Keep partial cases as a separate challenge set. Do not pass `[UNK]` through CER,
train it as literal text, or score guessed completions as ground truth. Scoring
readable partial spans requires a separate reviewed span/alignment protocol.
Illegible crops have no textual accuracy target; retain them for failure and
abstention review. No OCR scores can be claimed from this template alone.

This CSV is a crop annotation format. It is **not directly accepted** by the
existing whole-image JSON benchmark described in
`backend/app/evaluation/MANIFEST_FORMAT.md`, which currently handles service
number and destination. Conversion and route-field scoring need explicit work.

## Create an unannotated CSV

From the repository root:

```sh
python3 scripts/create_ocr_ground_truth.py /path/to/crops --output evaluation/ocr_ground_truth.draft.csv
```

The script recursively lists supported image extensions, keeps distinct relative
paths (even identical basenames), skips hidden paths and symlinks, and fills only
`crop_id`. It does not decode images, establish provenance, deduplicate, infer
fields/views, assign groups, calculate source boxes, or run OCR. Verify that files
are real images during the crop audit. All annotation cells start blank.
The output parent directory must already exist; existing CSVs are never overwritten.

Only for a folder whose shared metadata you have independently confirmed:

```sh
python3 scripts/create_ocr_ground_truth.py /path/to/side-test-crops --output evaluation/side_test.draft.csv --view side --split test
```

Optional `--field` and `--lighting` also apply to **every** row. Do not use them
for mixed folders. Split membership and duplicate/burst isolation must still be
reviewed; nothing is automatically ready for evaluation.
