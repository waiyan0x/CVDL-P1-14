# Spoken announcement evaluation

The app reads each matched display aloud. The backend matcher writes a one-line
message such as `Bus 92B to Ghim Moh Terminal.` (`backend/app/services/announcement.py`);
the frontend rewrites it for speech (`spokenAnnouncement` in
`frontend/assets/js/core/bus-announcements.js`) and speaks it with the browser's
`speechSynthesis`. This folder measures how well those announcements are understood
and how the wording was improved over two rounds of testing.

A speech recogniser (Whisper) stands in for the listener. Nothing here is trained:
the voices and Whisper stay fixed, and only the text the app speaks changes. This is
not a user study and does not establish accessibility for visually impaired commuters.

## Summary

The app's announcements went through two rounds of testing:
- **Round 1** (`announcements-v2`) checked whether rewriting the matcher's message
  helps. Destinations became much clearer, but spelling out the service code made
  services that end in a letter worse (`6 3 A to` was heard as "638").
- **Round 2** (`service-wording-v3`) tested four ways of saying those codes. The best
  wording, `Bus 63A, to …`, is what the app says now.

All three voices, faster-whisper large-v3:

| Measure | Clips (n) | Matcher message read as is | App after round 1 | App now |
| --- | ---: | ---: | ---: | ---: |
| Destination exact, routes the rewrite changes | 783 | 20.4% | 62.2% | 62.2% |
| Destination word error rate, same routes | 783 | 29.5% | 12.2% | 12.2% |
| Service heard: plain number (`174`) | 489 | 100.0% | 99.4% | 99.4% |
| Service heard: number + A (`63A`) | 333 | 91.0% | 59.5% | **99.7%** |
| Service heard: number + other letter (`92B`, `10E`) | 354 | 98.6% | 83.6% | **99.2%** |
| Service heard: lettered shuttle (`CW1`) | 27 | 74.1% | 85.2% | 85.2% |

Sources:
- The destination, plain-number and shuttle rows come from round 1.
- The two lettered rows come from round 2, which covers all 229 lettered routes. Its
  `written` wording is the matcher's own wording of the service, and its `spelled`
  wording is what the app said after round 1.
- Round 2 changed only the service wording. The destination rows therefore carry over:
  round 2 measured 58–62% destination exact under every wording.

The current app is best, or tied for best, on every row except plain numbers, which
are heard correctly either way (100.0% vs 99.4%).

## How it is measured (both rounds)

1. **Text.** Each set is built from the cleaned route table
   `data/reference/bus_information.cleaned.csv` (the names the matcher returns).
   Each route is worded the way the matcher announces a confirmed service and
   destination: `Bus <service> to <destination>.` The same route is spoken in every
   wording being compared, so the comparisons are paired. Named shuttles
   (`Giant/IKEA Bedok`) are left out. The "via" road part is left out too, because it
   comes from OCR, not from the reference.
2. **Voices.** `scripts/synthesize_tts_windows.ps1` speaks each clip with the Windows
   OneCore voices David, Zira and Mark, at the app's rate (0.95). These are the local
   voices Chrome and Edge offer to `speechSynthesis` on Windows. No Singapore English
   voice was installed on the test machine.
3. **Listener.** `colab/tts_eval/tts_whisper_eval.ipynb` transcribes every clip with
   faster-whisper `large-v3` on a Colab T4 GPU: no prompt, no vocabulary hints,
   deterministic decoding, each clip on its own.
4. **Scoring.** `scripts/score_tts_transcripts.py` compares each transcript with the
   intended meaning of the route:

   | Measure | Meaning | Better |
   | --- | --- | --- |
   | WER | Word error rate over the whole announcement | lower |
   | Service heard | The word after "bus" is exactly the service | higher |
   | Destination WER | Word error rate over the words after "to" | lower |
   | Destination exact | Every destination word right | higher |

   Written and spelled forms count as the same: `92B` = `9 2 B` = `9-2B`, and `MRT` = `M R T`.
   Whisper's US spelling `Center` counts as `Centre`. If "to" is lost (heard as part of
   the number, `Bus 17442`), the service counts as wrong, and the destination is taken
   from after the number.

The set names continue from `v1`, an earlier set built for the app's first wording
(`Bus service 9 2 B. Reference destination: …`). That wording was replaced when the
app moved to the matcher's message, so v1 is not kept.

## Round 1: rewriting the message for speech (announcements-v2)

**Question:** does the frontend rewrite help, compared with speaking the matcher's
message as written?

**Set** (`scripts/build_tts_manifest.mjs`):
- **Changed:** all 261 routes whose destination the rewrite changes.
- **Controls:** 60 routes whose destination it leaves alone; there only the service
  wording differs (`174` vs `1 7 4`).
- Each route is spoken in two wordings and three voices: 641 unique clips, 1,923
  transcribed.

| Wording | Example |
| --- | --- |
| raw (matcher message as written) | `Bus 3A to Pasir Ris Drive 12 (Blk 747A).` |
| normalised (app at the time) | `Bus 3 A to Pasir Ris Drive 12, Block 7 4 7 A.` |

The rewrite (`spokenPlace`):
- expands abbreviations (`Blk` → Block, `Opp` → Opposite, `Ave` → Avenue);
- spells out acronyms and block numbers (`M R T`, `7 4 7 A`);
- turns brackets into pauses;
- spells out the service.

Since round 2, the app no longer spells out lettered services, so rebuilding this set
today gives `Bus 3A, to …` in the normalised wording.

**Results** (full tables: [announcements-v2/TTS_RESULTS.md](announcements-v2/TTS_RESULTS.md)):

| Routes | Wording | n | WER | Service heard | Destination WER | Destination exact |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| changed (261) | raw | 783 | 19.0 | 96.3 | 29.5 | 20.4 |
| changed (261) | normalised | 783 | 9.3 | 88.6 | 12.2 | 62.2 |
| control (60) | raw | 180 | 7.3 | 98.3 | 13.4 | 71.7 |
| control (60) | normalised | 180 | 8.8 | 89.4 | 12.4 | 73.3 |

- **Destinations: the rewrite helps a lot.**
  - On the routes it changes, destination exact match rises from 20% to 62%, and
    destination WER falls from 30% to 12%.
  - Per route and voice, 334 of 783 pairs improve and 7 get worse.
  - Read as written, abbreviations and brackets are lost or misread (`Blk`, `Opp`,
    `(Loop)`).
  - The controls barely move (72% → 73%), so the gain comes from the rewrite, not the
    voice.
- **Services: spelling out a trailing letter hurts.** Service heard, by code shape:

  | Service code | n | raw | normalised |
  | --- | ---: | ---: | ---: |
  | digits (`174`) | 489 | 100.0 | 99.4 |
  | digits + A (`63A`) | 228 | 89.9 | 65.4 |
  | digits + other letter (`92B`, `10E`) | 219 | 99.1 | 90.0 |
  | letter prefix (`CW1`, `TS8`) | 27 | 74.1 | 85.2 |

  Spelled-out digits are fine. A spelled-out trailing letter is not:
  - **A runs into "to" and is heard as 8.** `6 3 A to` sounds like "eight to", giving
    `Bus 638`. This accounts for 78 of the 108 service misses, and the Mark voice is the
    worst. The raw wording has the same problem only after round tens: `60A`, said
    "sixty A", is heard as `68`.
  - **E and W are heard as directions.** `10 E to` is heard as "10, east to", and `84 W`
    as "84, west".

  Lettered shuttles do better spelled out (`C W 1`), though C is still often heard as E
  (`EW1`).
- **Most remaining destination errors are local names the voices mispronounce.** The
  voices are US English:

  | Name | Heard as |
  | --- | --- |
  | Clementi | "Claymanty" |
  | Hougang | "Hugong" |
  | Dhoby Ghaut | "Dubai got" |
  | Yishun | "Yashun" |
  | Kranji | "Cranji" |

  No text rewrite fixes these. A pronunciation respelling or a Singapore English voice
  might. Some count as errors only because of spelling: `JB Sentral` is said, and heard,
  as "JB Central".

## Round 2: saying services that end in a letter (service-wording-v3)

**Question:** how should the app say `63A`, `92B` or `10E` so that the letter is heard?

**Set** (`scripts/build_tts_service_manifest.mjs`):
- All 229 lettered routes in the reference: 111 end in A and 118 in another letter.
- Each route is spoken four ways. The destination is the same in all four (as the app
  speaks it), so only the service wording differs.
- 916 unique clips, 2,748 transcribed.

| Wording | Example |
| --- | --- |
| spelled (app after round 1) | `Bus 6 3 A to Bishan M R T station.` |
| spelled_pause | `Bus 6 3 A, to Bishan M R T station.` |
| written (as the matcher writes it) | `Bus 63A to Bishan M R T station.` |
| written_pause | `Bus 63A, to Bishan M R T station.` |

**Results** (full tables: [service-wording-v3/TTS_RESULTS.md](service-wording-v3/TTS_RESULTS.md)).
Service heard (%), all three voices:

| Service code | n | spelled | spelled_pause | written | written_pause |
| --- | ---: | ---: | ---: | ---: | ---: |
| digits + A (`63A`) | 333 | 59.5 | 98.8 | 91.0 | **99.7** |
| digits + other letter (`92B`, `10E`) | 354 | 83.6 | 97.5 | 98.6 | **99.2** |

Service heard (%) by voice, comparing the app's old wording (spelled) with its new one
(written_pause):

| Voice | Ends in A: spelled → written_pause | Other letter: spelled → written_pause |
| --- | --- | --- |
| David | 83.8 → 99.1 | 83.1 → 99.2 |
| Mark | 30.6 → 100.0 | 83.9 → 99.2 |
| Zira | 64.0 → 100.0 | 83.9 → 99.2 |

Whole-announcement WER falls too: from 16.6% to 12.1% for A codes, and from 14.0% to 10.3%
for other letters.

- **The pause before "to" does most of the work.** With either pause wording, every
  voice hears at least 95% of services correctly.
- **written_pause is the best wording.**
  - Paired by route and voice against `spelled`, it fixes 192 of 687 announcements and
    breaks 3.
  - Against `spelled_pause`, it fixes 12 and breaks 3.
  - The spelled pause still loses a letter after a repeated digit: `8 9 E,` is heard as
    `890`, `8 8 A,` as `888`, and `3 6 T,` as `360`.
- **Written without a pause fails after round tens.** "Sixty A to" is heard as
  "sixty-eight": `60A` becomes `68`, and `190A` becomes `198`.
- **Four misses remain** with written_pause: `80A` heard as `ADA`, `812T` as `A12T`
  (twice), and `89E` as `8090`.
- **Cost:** the pause adds 0.4 s (median 4.1 s → 4.5 s). Destinations are unaffected:
  58–62% exact under every wording.

## What the app says now

`spokenAnnouncement`, `spokenService` and `spokenPlace` in
`frontend/assets/js/core/bus-announcements.js`; tests in
`tests/frontend/bus-announcements.test.mjs`.

| Part | Rule | Example |
| --- | --- | --- |
| Plain number | spelled out (round 1: 99.4% heard) | `Bus 1 7 4 to …` |
| Number + letter | as written, pause before "to" (round 2) | `Bus 63A, to …` |
| Lettered shuttle | spelled out (round 1: better than as written) | `Bus C W 1 to …` |
| Destination | abbreviations expanded, acronyms and block numbers spelled, brackets turned into pauses (round 1) | `Pasir Ris Drive 12, Block 7 4 7 A` |
| "via" road | the same rewrite (not measured) | `via Upper Serangoon Road` |

For all 229 lettered routes, the app's text is exactly the measured written_pause clip.

## Announcement length

From the synthesis logs (audio length per clip, all voices):

| Set | Wording | Median | p95 | Max |
| --- | --- | ---: | ---: | ---: |
| v2 | raw | 4.2 s | 6.1 s | 8.0 s |
| v2 | normalised | 4.2 s | 6.0 s | 7.7 s |
| v3 | spelled | 4.1 s | 5.9 s | 7.7 s |
| v3 | written_pause (app now, lettered services) | 4.5 s | 6.3 s | 8.3 s |

The first wording (`Bus service 9 2 B. Reference destination: …`) took 6.7 s median
and 8.4 s p95.

The live page waits 6 s between automatic announcements (`AnnouncementGate`), and
automatic mode never starts a new announcement while one is still being spoken. A
longer one is therefore never cut off; the next one waits for it to finish.

Offline synthesis to a file takes about 15 ms per clip (p95 23 ms). That is not the
browser's start-of-speech delay.

## Files

Each set folder (`announcements-v2/`, `service-wording-v3/`) holds:

| File | Contents |
| --- | --- |
| `manifest.csv` | One row per route and wording: service, destination, group, wording, clip id, spoken text, reference meaning |
| `clips.csv` | Unique texts to synthesise |
| `synthesis_<voice>.csv` | Audio length and synthesis time per clip |
| `transcripts.csv` | Whisper's transcript per clip and voice (from Colab) |
| `scores.csv` | Every measure per clip and voice |
| `TTS_RESULTS.md` | The full result tables |

Scripts:

| Script | Purpose |
| --- | --- |
| `scripts/build_tts_manifest.mjs` | Builds the round 1 set |
| `scripts/build_tts_service_manifest.mjs` | Builds the round 2 set |
| `scripts/synthesize_tts_windows.ps1` | Speaks the clips (Windows only) |
| `scripts/package_tts_eval.py` | Packs the audio as lossless 16 kHz FLAC in a zip, plus 10 MB parts and a checksum |
| `scripts/score_tts_transcripts.py` | Writes `scores.csv` and `TTS_RESULTS.md` |
| `tests/evaluation/test_tts_scoring.py` | Tests for the scoring rules |

The audio itself stays in the ignored `.runtime/tts-eval/` folder.

## Reproduce

On Windows, from the repo root. Build one set:

```powershell
.cache\tools\node\node.exe scripts\build_tts_manifest.mjs evaluation\tts\announcements-v2
.cache\tools\node\node.exe scripts\build_tts_service_manifest.mjs evaluation\tts\service-wording-v3
```

Then, for that set (`$set` is `announcements-v2` or `service-wording-v3`):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\synthesize_tts_windows.ps1 `
  -ManifestDir evaluation\tts\$set -AudioDir .runtime\tts-eval\$set
.venv\Scripts\python.exe scripts\package_tts_eval.py evaluation\tts\$set `
  .runtime\tts-eval\$set .runtime\tts-eval\$set.zip
```

Synthesis takes about a minute. The zips are 135 MB (v2) and 190 MB (v3). Then:

1. Open the notebook on a Colab GPU runtime (browser, or VS Code with the Colab
   extension).
2. Upload the audio:
   - **VS Code:** right-click `.runtime/tts-eval/<set>-parts` > Upload to Colab. A single
     large upload fails there, which is why the zip is also written in parts.
   - **Browser:** drag the zip into the Files panel.
3. Run all cells. The notebook uses the set uploaded most recently. Transcription takes
   about 18 minutes (v2) or 26 minutes (v3) on a T4.
4. Download `transcripts.csv` (VS Code: Colab sidebar > Contents > right-click >
   Download) and save it in `evaluation/tts/<set>/`.
5. Score it:

```powershell
.venv\Scripts\python.exe scripts\score_tts_transcripts.py evaluation\tts\<set>
```

## Limitations

- **Whisper is not a listener.** It knows Singapore place names only as well as its
  training data does, and it is scored on spelling, so a correct pronunciation with an
  unusual spelling counts as an error (`Sentral` / "Central"). Results compare wordings
  with each other; they do not say how many commuters would understand an announcement.
- **Only the three Windows voices were tested.** macOS, Android and other browser
  voices may read `63A` or spelled letters differently.
- **Local place names are still often misheard** (see round 1). They would need a
  pronunciation respelling or a Singapore English voice.
- **Not measured:**
  - the browser's start-of-speech delay (`speak()` to first sound);
  - the "via" road part of messages;
  - messages other than "Bus <service> to <destination>" (for example
    "Bus 64 is approaching. Destination could not be read.").
