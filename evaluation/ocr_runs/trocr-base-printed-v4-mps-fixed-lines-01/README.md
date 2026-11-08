# Failed TrOCR attempt

The public pretrained checkpoint loaded onto `mps:0`, but writing the environment file failed with `OSError: [Errno 28] No space left on device`. No crop predictions or timings were collected. The failure record was reconstructed from captured stderr because the initial failure-record write also failed. This is an execution failure, not an OCR accuracy result.

The user chose to run TrOCR on another machine later. See `docs/OCR_MODEL_SELECTION.md` for the portable command and pinned checkpoint revision.
