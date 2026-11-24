# Spoken announcement intelligibility: announcements-v2

Speech recognition: faster-whisper large-v3. Voices: Microsoft David, Microsoft Mark, Microsoft Zira. Each route is announced with the matcher message as written (raw) and as the app speaks it (normalised); both are scored against the same normalised meaning. WER and destination WER: lower is better. Service heard and destination exact: higher is better. All in %.

| Voice | Group | Wording | n | WER | Service heard | Destination WER | Destination exact |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Microsoft David | changed | raw | 261 | 18.7 | 95.8 | 28.9 | 19.2 |
| Microsoft David | changed | normalised | 261 | 8.7 | 92.7 | 12.0 | 62.5 |
| Microsoft David | control | raw | 60 | 5.8 | 100.0 | 11.2 | 75.0 |
| Microsoft David | control | normalised | 60 | 7.7 | 91.7 | 10.7 | 75.0 |
| Microsoft Mark | changed | raw | 261 | 18.0 | 95.8 | 27.9 | 21.5 |
| Microsoft Mark | changed | normalised | 261 | 10.3 | 82.4 | 12.3 | 61.7 |
| Microsoft Mark | control | raw | 60 | 8.5 | 96.7 | 15.2 | 70.0 |
| Microsoft Mark | control | normalised | 60 | 10.3 | 85.0 | 14.2 | 71.7 |
| Microsoft Zira | changed | raw | 261 | 20.2 | 97.3 | 31.9 | 20.7 |
| Microsoft Zira | changed | normalised | 261 | 8.9 | 90.8 | 12.1 | 62.5 |
| Microsoft Zira | control | raw | 60 | 7.4 | 98.3 | 13.7 | 70.0 |
| Microsoft Zira | control | normalised | 60 | 8.2 | 91.7 | 12.2 | 73.3 |
| all voices | changed | raw | 783 | 19.0 | 96.3 | 29.5 | 20.4 |
| all voices | changed | normalised | 783 | 9.3 | 88.6 | 12.2 | 62.2 |
| all voices | control | raw | 180 | 7.3 | 98.3 | 13.4 | 71.7 |
| all voices | control | normalised | 180 | 8.8 | 89.4 | 12.4 | 73.3 |

Service heard by code shape, all routes and voices (%):

| Service code | n | raw | normalised |
| --- | ---: | ---: | ---: |
| digits (174) | 489 | 100.0 | 99.4 |
| digits + A (63A) | 228 | 89.9 | 65.4 |
| digits + other letter (92B, 10E) | 219 | 99.1 | 90.0 |
| letter prefix (CW1, TS8) | 27 | 74.1 | 85.2 |

Changed routes, paired by voice: destination exact improved in 334 and worsened in 7 of 783 pairs.

| Wording | Announcement length median / p95 (s) | Synthesis time median / p95 (ms) |
| --- | ---: | ---: |
| raw | 4.2 / 6.1 | 15 / 23 |
| normalised | 4.2 / 6.0 | 15 / 23 |

Synthesis time is Windows OneCore offline synthesis to a file, not browser start-of-speech latency. Speech recognition stands in for a listener; it is not evidence of accessibility for visually impaired commuters.
