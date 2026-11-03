# Seven-segment OCR baseline shortlist

**Scope:** A separate seven-segment reading dataset, not the bus EDS dataset.
This is a candidate selection, not a performance result. Compare each method on
the same reviewed single-reading crops and the split defined in
`docs/SEVEN_SEGMENT_EVALUATION.md`. The proposed scored alphabet is `0–9`, `.`,
`+`, and `-`; confirm the actual display alphabet before fixing any whitelist or
training dictionary.

**Source labels:** **Repository** means a fact observed in this checkout.
**External** means an official project document linked below, outside the supplied
repository/course material. **Inference** means an unmeasured suitability or
selection judgement. The supplied coursework brief and rubric are not present in
the checkout, so no model is claimed to be course-required.

## Recommend for the first comparison

### 1. OpenCV segment/template reference

- **Suitability — Inference:** A useful low-complexity control when the display has
  stable segment geometry. It may fail under blur, perspective, reflections, or
  damaged/unlit segments. Segment decoding or per-glyph template matching would
  be an implementation to build, not an existing trained OCR model.
- **Character set — Proposed:** Explicit templates for `0–9`, `.`, `+`, `-` and a
  blank/reject state. Unsupported symbols should be rejected, not guessed.
- **GPU — Proposed:** CPU reference implementation. A GPU is unnecessary for the
  baseline; do not describe its CPU timing as GPU inference timing.
- **Output / confidence — Proposed:** One reading string and per-glyph or
  aggregate template-similarity score. Similarity is not a calibrated probability.
- **Fine-tuning:** No neural fine-tuning; templates, segmentation thresholds and
  rejection threshold can be calibrated on training/validation data only.
- **Licence — External:** OpenCV library Apache-2.0; `opencv-python` packaging
  scripts MIT, with bundled third-party licence notices.
- **Install — External:** `python -m pip install opencv-python` (already listed in
  this repository's `requirements.txt`).
- **Why retain — Inference:** It tests whether display-specific structure is
  enough before spending GPU time on a broad recognizer.

Sources: [OpenCV template matching](https://docs.opencv.org/4.11.0/d4/dc6/tutorial_py_template_matching.html),
[opencv-python installation and licences](https://github.com/opencv/opencv-python/blob/4.x/README.md).

### 2. Tesseract English LSTM

- **Suitability — Inference:** A quick general pretrained baseline for an isolated
  reading. Seven-segment glyphs are outside its ordinary printed-text emphasis;
  use a single-line page segmentation mode and measure rather than assume fit.
- **Character set — External:** English traineddata is broader than the task.
  Restrict output with `tessedit_char_whitelist=0123456789.+-`; verify that the
  allowed glyphs are really present in the dataset.
- **GPU — External:** Treat the normal install as CPU. Tesseract's OpenCL path is
  experimental and is not recommended for the baseline.
- **Output / confidence — External:** Plain UTF-8 text or TSV. TSV has word-level
  `conf` values; they are not directly comparable to other engines' scores.
- **Fine-tuning — External:** LSTM training via `tesstrain` exists but is more work
  than needed for the first pretrained baseline.
- **Licence — External:** Apache-2.0 for Tesseract; check language-data and other
  dependencies if redistributing them.
- **Install — External:** macOS: `brew install tesseract`; Colab/Linux:
  `apt-get update && apt-get install -y tesseract-ocr`. Example invocation:
  `tesseract crop.png stdout -l eng --oem 1 --psm 7 -c tessedit_char_whitelist=0123456789.+-`.
- **Why retain — Inference:** It is a low-effort general-engine comparator with
  an inspectable character restriction and CPU cost.

Sources: [Tesseract installation/licence](https://tesseract-ocr.github.io/tessdoc/Installation.html),
[output formats](https://tesseract-ocr.github.io/tessdoc/FAQ),
[single-line mode and whitelist](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html),
[OpenCL status](https://tesseract-ocr.github.io/tessdoc/TesseractOpenCL),
[training](https://tesseract-ocr.github.io/tessdoc/).

### 3. EasyOCR English recognizer

- **Suitability — Inference:** A GPU-capable general pretrained comparator for
  crops. Use recognition on the known crop rather than re-detecting a whole image;
  seven-segment performance remains to be measured.
- **Character set — External:** English model has a broader character set. Supply
  `allowlist='0123456789.+-'` at recognition time; this constrains decoding but
  does not make the pretrained weights seven-segment-specific.
- **GPU — External/Repository:** EasyOCR supports CUDA and Apple MPS when
  `gpu=True`; the current bus EDS adapter explicitly sets `gpu=False`, so a
  separate baseline runner must enable GPU rather than reuse that setting.
- **Output / confidence — External:** Standard `readtext` output is a list of
  `(bounding_box, text, confidence)` entries. A cropped-reading runner should
  reduce this to one declared reading and keep the original score definition.
- **Fine-tuning — External:** Custom recognition model training/loading is
  supported, with additional model/configuration files; this is a later experiment.
- **Licence — External:** Apache-2.0 for the EasyOCR project.
- **Install — External:** `python -m pip install easyocr==1.7.2`. Install a
  hardware-compatible PyTorch build first if the environment requires one.
- **Why retain — Inference:** It supplies a practical pretrained GPU comparison
  and a possible path to a task-specific recognizer.

Sources: [EasyOCR README, install, output and licence](https://github.com/JaidedAI/EasyOCR/blob/master/README.md),
[GPU selection and allowlist API](https://github.com/JaidedAI/EasyOCR/blob/master/easyocr/easyocr.py),
[custom recognition models](https://github.com/JaidedAI/EasyOCR/blob/master/custom_model.md).
Repository setting: `backend/app/services/ocr/easyocr.py`.

### 4. Supplied fine-tuned TrOCR — conditional diagnostic candidate

- **Suitability — Repository/Inference:** The project contains a TrOCR
  vision-encoder-decoder and tokenizer. It reads one text-line crop, but its
  training images, labels and split provenance are absent from the available
  history. Its seven-segment suitability is unknown; do not rank it on the
  existing validation/test set until independence is established.
- **Character set — Repository:** Its broad tokenizer is not limited to
  `0–9.+-`. Use output validation as a separate, declared step rather than
  pretending the checkpoint has a seven-segment alphabet.
- **GPU — Repository/External:** PyTorch supports CUDA or MPS. The current
  adapter selects MPS then CPU, so a Colab run needs an explicit CUDA path.
- **Output / confidence — Repository:** `batch_decode` gives one generated text
  string. The adapter computes a mean generated-token probability as a score;
  TrOCR does not supply a calibrated whole-reading correctness probability.
- **Fine-tuning — External:** Hugging Face documents TrOCR fine-tuning with a
  sequence-to-sequence trainer, provided reviewed crop/transcription pairs exist.
- **Licence:** Transformers software is Apache-2.0 (**External**). The licence
  and original base checkpoint of the supplied fine-tuned **weights are unknown**
  from the repository; do not infer them from the software licence.
- **Install — Repository/External:** `python -m pip install "transformers>=4.52,<5" torch safetensors pillow`,
  then `python scripts/fetch_trocr.py` from this repository with authenticated
  GitHub access to hydrate the LFS weight into `.cache/trocr/`.
- **Why retain — Inference:** It is already supplied and may be informative, but
  only as a diagnostic until training provenance or a genuinely new held-out test
  set resolves leakage risk.

Sources: `models/trocr-finetuned/config.json`,
`backend/app/services/ocr/trocr.py`, `scripts/fetch_trocr.py`, Git commit
`a5cead0`; [TrOCR documentation](https://huggingface.co/docs/transformers/en/model_doc/trocr),
[Transformers software licence](https://github.com/huggingface/transformers).

## Defer from the first comparison

### PaddleOCR text recognition

- **Suitability — Inference:** A plausible alternative recognizer, especially if
  a small custom dictionary is trained, but there is no measured advantage on
  this seven-segment dataset yet.
- **Character set — External:** The pretrained model's vocabulary depends on
  the selected checkpoint. Inspect its dictionary for `.`, `+`, and `-` before
  comparing it. Training supports a custom character dictionary.
- **GPU — External:** The official PaddlePaddle path supports NVIDIA CUDA with
  a wheel matched to the installed CUDA version. An Apple MPS path is not
  established by the cited installation guide.
- **Output / confidence — External:** Text-recognition results contain
  `rec_text` and `rec_score`; the latter is engine-specific, not a calibrated
  cross-engine correctness score.
- **Fine-tuning — External:** Recognition training and custom dictionaries are
  documented, but require the training setup and labelled data.
- **Licence — External:** PaddleOCR project Apache-2.0; verify the selected model
  artifact's terms separately when choosing a checkpoint.
- **Install — External:** `python -m pip install paddleocr`, plus the
  PaddlePaddle GPU wheel that matches the Colab/NVIDIA CUDA environment. For
  *Linux CUDA 11.8 specifically*, the official example is
  `python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/`.
- **Reason for deferral — Inference:** A second deep-learning runtime and CUDA
  setup add work before the simpler controls answer whether generic pretrained
  OCR works at all. Reconsider it if EasyOCR fails on reviewed validation crops
  or custom-dictionary training becomes a core requirement.

Sources: [PaddleOCR quick start, result shape and GPU install](https://www.paddleocr.ai/main/en/quick_start.html),
[recognition training/dictionaries](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version2.x/ppocr/model_train/recognition.en.md),
[project licence](https://github.com/PaddlePaddle/PaddleOCR).

## Decision and gate

The first comparison has **three unconditional candidates** (OpenCV reference,
Tesseract, EasyOCR) and **one conditional candidate** (supplied TrOCR). PaddleOCR
is the sole deferred candidate, for the reason above. Do not compare confidence
numbers across engines as if calibrated. Freeze the reviewed test split and
normalization rules before using it; select preprocessing and thresholds on
validation only. Publish raw reading accuracy, normalized accuracy, CER and
latency with hardware and timing boundaries, including failures and rejected
readings. Do not report a TrOCR validation/test score as independent until its
training corpus has been checked for overlap.
