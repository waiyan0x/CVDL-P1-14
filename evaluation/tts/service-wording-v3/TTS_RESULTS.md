# Spoken announcement intelligibility: service-wording-v3

Speech recognition: faster-whisper large-v3. Voices: Microsoft David, Microsoft Mark, Microsoft Zira. Each route is announced in 4 wordings (spelled, spelled_pause, written, written_pause); all are scored against the same meaning. WER and destination WER: lower is better. Service heard and destination exact: higher is better. All in %.

| Voice | Group | Wording | n | WER | Service heard | Destination WER | Destination exact |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Microsoft David | other suffix | spelled | 118 | 13.8 | 83.1 | 16.2 | 59.3 |
| Microsoft David | other suffix | spelled_pause | 118 | 11.1 | 98.3 | 16.8 | 61.0 |
| Microsoft David | other suffix | written | 118 | 10.0 | 99.2 | 16.8 | 59.3 |
| Microsoft David | other suffix | written_pause | 118 | 10.8 | 99.2 | 16.6 | 61.0 |
| Microsoft David | suffix A | spelled | 111 | 13.3 | 83.8 | 19.0 | 58.6 |
| Microsoft David | suffix A | spelled_pause | 111 | 11.5 | 98.2 | 18.7 | 60.4 |
| Microsoft David | suffix A | written | 111 | 11.7 | 94.6 | 19.0 | 59.5 |
| Microsoft David | suffix A | written_pause | 111 | 11.9 | 99.1 | 19.0 | 59.5 |
| Microsoft Mark | other suffix | spelled | 118 | 14.0 | 83.9 | 16.0 | 62.7 |
| Microsoft Mark | other suffix | spelled_pause | 118 | 10.4 | 95.8 | 15.4 | 63.6 |
| Microsoft Mark | other suffix | written | 118 | 10.4 | 96.6 | 16.2 | 62.7 |
| Microsoft Mark | other suffix | written_pause | 118 | 10.1 | 99.2 | 16.2 | 62.7 |
| Microsoft Mark | suffix A | spelled | 111 | 20.8 | 30.6 | 18.1 | 58.6 |
| Microsoft Mark | suffix A | spelled_pause | 111 | 11.7 | 99.1 | 18.3 | 59.5 |
| Microsoft Mark | suffix A | written | 111 | 12.2 | 86.5 | 17.4 | 60.4 |
| Microsoft Mark | suffix A | written_pause | 111 | 12.8 | 100.0 | 19.8 | 56.8 |
| Microsoft Zira | other suffix | spelled | 118 | 14.2 | 83.9 | 16.6 | 57.6 |
| Microsoft Zira | other suffix | spelled_pause | 118 | 10.6 | 98.3 | 16.8 | 61.0 |
| Microsoft Zira | other suffix | written | 118 | 9.8 | 100.0 | 16.6 | 57.6 |
| Microsoft Zira | other suffix | written_pause | 118 | 9.8 | 99.2 | 15.6 | 62.7 |
| Microsoft Zira | suffix A | spelled | 111 | 15.7 | 64.0 | 18.3 | 57.7 |
| Microsoft Zira | suffix A | spelled_pause | 111 | 11.5 | 99.1 | 18.7 | 56.8 |
| Microsoft Zira | suffix A | written | 111 | 11.2 | 91.9 | 17.4 | 57.7 |
| Microsoft Zira | suffix A | written_pause | 111 | 11.6 | 100.0 | 19.0 | 58.6 |
| all voices | other suffix | spelled | 354 | 14.0 | 83.6 | 16.2 | 59.9 |
| all voices | other suffix | spelled_pause | 354 | 10.7 | 97.5 | 16.3 | 61.9 |
| all voices | other suffix | written | 354 | 10.1 | 98.6 | 16.5 | 59.9 |
| all voices | other suffix | written_pause | 354 | 10.3 | 99.2 | 16.1 | 62.1 |
| all voices | suffix A | spelled | 333 | 16.6 | 59.5 | 18.4 | 58.3 |
| all voices | suffix A | spelled_pause | 333 | 11.6 | 98.8 | 18.6 | 58.9 |
| all voices | suffix A | written | 333 | 11.7 | 91.0 | 17.9 | 59.2 |
| all voices | suffix A | written_pause | 333 | 12.1 | 99.7 | 19.2 | 58.3 |

Service heard by code shape, all routes and voices (%):

| Service code | n | spelled | spelled_pause | written | written_pause |
| --- | ---: | ---: | ---: | ---: | ---: |
| digits + A (63A) | 333 | 59.5 | 98.8 | 91.0 | 99.7 |
| digits + other letter (92B, 10E) | 354 | 83.6 | 97.5 | 98.6 | 99.2 |

- spelled_pause vs spelled, paired by route and voice: service heard improved in 184 and worsened in 4 of 687 pairs.
- written vs spelled, paired by route and voice: service heard improved in 178 and worsened in 20 of 687 pairs.
- written_pause vs spelled, paired by route and voice: service heard improved in 192 and worsened in 3 of 687 pairs.

| Wording | Announcement length median / p95 (s) | Synthesis time median / p95 (ms) |
| --- | ---: | ---: |
| spelled | 4.1 / 5.9 | 14 / 21 |
| spelled_pause | 4.5 / 6.3 | 15 / 22 |
| written | 4.1 / 5.9 | 14 / 21 |
| written_pause | 4.5 / 6.3 | 15 / 22 |

Synthesis time is Windows OneCore offline synthesis to a file, not browser start-of-speech latency. Speech recognition stands in for a listener; it is not evidence of accessibility for visually impaired commuters.
