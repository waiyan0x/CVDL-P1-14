# Demo test cases

Rehearsal checklist for the web app demo. App at `http://127.0.0.1:8001/`.
Tick each box when it passes. If a case fails, note what happened, then
decide whether to fix it, avoid it in the demo, or explain it as a known
limitation.

Expected results describe how the app is designed to behave. They have not
all been confirmed on this machine yet, so the first rehearsal confirms them.

Legend: **Detect** = `/detect` (one image), **Live** = `/live` (camera or video).

---

## 0. Before the demo (5 minutes)

- [ ] **S1. Server starts.** `BUS_EDS_PORT=8001 bash scripts/run.sh` shows no
  errors, and `/live` loads.
- [ ] **S2. All models are available.** `/models` lists the YOLO11s detector
  and fine-tuned PaddleOCR as available, not "unavailable".
- [ ] **S3. Speech works.** On Detect, load a sample and press **Read result
  aloud**. You hear a voice. Check the laptop volume and output device first.
- [ ] **S4. Camera permission.** On Live, press **Start**. The browser asks
  for the camera once, and the preview appears.
- [ ] **S5. Speed is acceptable.** On Live, the status line shows a processing
  rate. One frame should take well under a second (median 284 ms was measured
  on a 2-core CPU).

---

## 1. Visually impaired user: blind, using a screen reader

Turn on VoiceOver (Cmd+F5) and close your eyes or look away from the screen.
Use only the keyboard.

| ID | Scenario | Steps | Expected | Pass |
| --- | --- | --- | --- | --- |
| B1 | Reach the main content | Load `/live` and press Tab once | "Skip to content" is announced. Enter jumps past the navigation | [ ] |
| B2 | Find and start the camera | Tab to **Start** and press Space | Each button is announced by name. The camera starts | [ ] |
| B3 | Turn on hands-free announcements | Tab to **Automatic announcements** and press Space | You hear "Automatic bus announcements enabled." | [ ] |
| B4 | Hear a bus | Hold a sample photo or phone image of a bus sign up to the camera | After 2 matching frames you hear e.g. "Bus 1 7 4 to Kampong Bahru Bus Terminal" | [ ] |
| B5 | No repeat spam | Keep the same bus in view for 20 s | It is announced once, not on every frame | [ ] |
| B6 | Second bus | Swap to a different bus image | The new bus is announced (at least 6 s after the first) | [ ] |
| B7 | Repeat on demand | Tab to **Read result aloud** and press it | The latest result is spoken again | [ ] |
| B8 | Silence it | Press **Stop speech** | Speech stops at once and automatic announcements turn off | [ ] |
| B9 | Voices clash (known issue) | With VoiceOver on, let an announcement play | Check whether VoiceOver and the app voice talk over each other. If they do, demo with VoiceOver off and mention it as a planned fix | [ ] |
| B10 | Error is heard | Deny the camera permission and press Start | An error is spoken or readable. (Live's status line has no `role="status"`, so this may be silent: known gap) | [ ] |

## 2. Visually impaired user: low vision

| ID | Scenario | Steps | Expected | Pass |
| --- | --- | --- | --- | --- |
| L1 | 200% zoom | Cmd + several times on `/detect` and `/live` | No text cut off, no horizontal scrolling, buttons still reachable | [ ] |
| L2 | Result is readable | Look at a result card at normal zoom from 1 m away | Bus number and destination are readable. Note any small grey text (13px notices) | [ ] |
| L3 | Focus is visible | Tab through Live | A clear outline shows on every focused control | [ ] |
| L4 | Boxes can be hidden | Press **Hide detection boxes** | Boxes disappear and the image is clearer | [ ] |

## 3. Computer-vision scenarios (Detect, sample images)

Use the sample picker on Detect, or upload from `data/samples/`. For each, note
what the app says and whether it is right.

**The key rule for every case: the app may withhold an answer, but must not
show a wrong bus number.** Withholding is a correct, safe outcome.

| ID | Sample (`data/samples/…`) | What it tests | Expected | Pass |
| --- | --- | --- | --- | --- |
| C1 | `distance-and-image-quality/close-readable-eds.jpg` | Easy case | Correct number and destination | [ ] |
| C2 | `eds-text-and-layout/number-with-a-letter-suffix.jpg` | Letter suffix (e.g. 63A) | Letter kept; spoken as "63A, to …" | [ ] |
| C3 | `eds-text-and-layout/destination-via-route-number.jpg` | Multi-line sign with route | Destination plus "via …" road | [ ] |
| C4 | `eds-text-and-layout/number-only.jpg` | No destination on sign | Number only; destination not invented | [ ] |
| C5 | `eds-text-and-layout/red-pink-led-text.jpg` | Unusual LED colour | Reads or withholds; no wrong number | [ ] |
| C6 | `lighting-and-environment/night-with-headlight-glare.jpg` | Glare | Reads or withholds | [ ] |
| C7 | `lighting-and-environment/backlit-sunset.jpg` | Backlight | Reads or withholds | [ ] |
| C8 | `distance-and-image-quality/motion-blur.jpg` | Blur | Likely withholds; no wrong number | [ ] |
| C9 | `distance-and-image-quality/distant-small-bus.jpg` | Far bus | Small box detected, or nothing; no wrong number | [ ] |
| C10 | `viewing-angle-and-display-location/side-eds.jpg` | Side display | Side text such as a road is **not** shown as the destination | [ ] |
| C11 | `viewing-angle-and-display-location/three-quarter-front.jpg` | Angled view | Correct, or withheld | [ ] |
| C12 | `crowded-or-obstructed-scenes/multiple-buses-in-one-image.jpg` | Two buses | Separate numbered results; nearest announced first | [ ] |
| C13 | `crowded-or-obstructed-scenes/photographed-through-glass.jpg` | Reflections | Reads or withholds | [ ] |
| C14 | `distracting-text-and-hard-negatives/advertising-text-on-the-bus-body.jpg` | Advert text | Advert text not read as the destination | [ ] |
| C15 | `distracting-text-and-hard-negatives/bus-stop-sign-with-service-numbers.avif` | Numbers on a bus-stop pole | **No bus announced** | [ ] |
| C16 | `distracting-text-and-hard-negatives/interchange-signage-no-bus.jpg` | No bus | "No bus display detected" | [ ] |
| C17 | `distracting-text-and-hard-negatives/rear-eds.jpg` | Back of a bus | Ideally no destination announced (rear signs are out of scope) | [ ] |
| C18 | `special-display-messages/off-service.jpg` | Not in service | "Bus not in service", not a route | [ ] |
| C19 | `special-display-messages/terminate-at.jpg` | Short trip | Handled without a wrong destination | [ ] |
| C20 | `special-display-messages/non-english-text.jpg` | Chinese text | Not garbled into a wrong destination. Good for the scalability point | [ ] |

Pick the 3 or 4 cleanest passes for the live demo, plus **one** safe failure
(e.g. C8 or C15) to show that the app withholds rather than guesses.

## 4. Aiming hints (Live, camera)

Only applies if the uncommitted aiming-hint change is kept. Turn on automatic
announcements.

| ID | Scenario | Steps | Expected | Pass |
| --- | --- | --- | --- | --- |
| A1 | Nothing in view | Point the camera at a wall for 6 s | "No bus sign in view." with a centred hint on screen | [ ] |
| A2 | Cut off left | Show a bus image with its sign at the left edge of the camera view | ← "Sign cut off on the left. Turn slightly left." | [ ] |
| A3 | Cut off right | Same at the right edge | → hint on the right | [ ] |
| A4 | Far | Show a small bus image in the middle | "Bus sign is small. The bus may still be far away." | [ ] |
| A5 | No hint over a bus | Show a clear, readable bus | Bus is announced; no hint is spoken | [ ] |
| A6 | Not repetitive | Leave A1 running for 30 s | Hint repeats at most every 15 s | [ ] |

## 5. Recovery and robustness

| ID | Scenario | Steps | Expected | Pass |
| --- | --- | --- | --- | --- |
| R1 | Stop keeps result | Press **Stop** on Live | Last result stays on screen | [ ] |
| R2 | Reset clears | Press **Reset** | Results and hint clear | [ ] |
| R3 | Restart | Stop, then **Start** again | Works without reloading the page | [ ] |
| R4 | Video input | Upload a short bus video | Frames are processed in order; announcements work | [ ] |
| R5 | Unsupported file | Upload a non-video file | Clear error, app still usable | [ ] |
| R6 | Room lighting | Run Live under the demo room's lights with a bus image on a phone or tablet | Screen glare doesn't stop detection. If it does, use a printed photo | [ ] |

---

## Suggested 3-minute live demo flow

1. **Detect, C1:** an easy read, with boxes, crops, OCR text and the matched
   destination. Press **Read result aloud**.
2. **Detect, C12 or C3:** a harder layout, read correctly.
3. **Detect, C15 or C8:** the app withholds instead of guessing. Say: "it
   would rather stay silent than send someone to the wrong bus."
4. **Live with the camera:** turn on automatic announcements, look away from
   the screen, and hold up a bus photo. If the aiming hints are kept, start
   with the photo cut off at the edge so the audience hears the hint first.
5. **Evaluation page (optional):** all three OCR pipelines on the same
   detections, connecting back to the results slide.

Backup plan: keep screenshots or a screen recording of steps 1–4 in case the
camera, speech or Wi-Fi fails on the day.
