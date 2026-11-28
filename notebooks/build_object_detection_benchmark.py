"""Build the self-contained EDS detector research notebook."""
import os
from pathlib import Path
import json

def md(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source.strip()}


def code(source):
    return {'cell_type': 'code', 'metadata': {}, 'source': source.strip(),
            'execution_count': None, 'outputs': []}


cells = [
    md(r"""
# EDS object detection: YOLO11n, YOLO11s, and DETR

**V9 result (28 November 2026):** seven candidates trained on the verified 6,858/294/299-image v9 split. Validation selected `yolo11s-gentle_aug` (mAP50:95 `0.6842`); its single held-out test scored `0.6819`. See the [v9 results and artifact index](../Object-Detection-v9/RESULTS.md). The v4 tables below use different data and remain historical. Human source and annotation review remains open.

This notebook implements the object detection allocation: dataset/label audit, pretrained model selection, fine-tuning, validation, per-class mAP, speed/failure comparison, threshold selection, and a final held-out test. It retains train/valid/test separation and records settings and hashes. Run from the repo's `notebooks/` folder or repo root.

Sources: task allocation PDF (external to this repository), [training inventory](../data/training/README.md), [readiness handoff](../docs/data_preparation/TRAINING_READINESS.md), [annotation guide](../docs/annotation/guide.md), [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11), [Hugging Face DETR](https://huggingface.co/docs/transformers/v4.51.1/en/model_doc/detr).

## Environment and run controls

Use the local `venv/detector` CUDA kernel in VS Code. Published `yolo11n.pt` and `yolo11s.pt` belong in `.runtime/object_detection_benchmark/pretrained/`; DETR downloads its published weights on first use. The saved reports and checkpoints are linked from the v9 results index. All execution switches default to off. Re-run training or evaluation only under a new, explicitly named experiment; the held-out v9 test is closed for further selection.
"""),
    code(r"""
from pathlib import Path
import hashlib, importlib.util, json, os, platform, sys, time
import re
from collections import Counter

ROOT = Path.cwd().resolve()
if not (ROOT / 'src').is_dir():
    ROOT = next((p for p in Path.cwd().resolve().parents if (p / 'src').is_dir()), ROOT)
if not (ROOT / 'src').is_dir():
    raise RuntimeError(f'Repo not found from {Path.cwd()}. Open the notebook from the repo root or notebooks/ folder.')
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from object_detection_artifacts import archive_benchmark

DATASET_ROOT = (ROOT / 'data/training/2026-11-25-roboflow-v9-stem-isolated').resolve()
OUTPUT_ROOT = (ROOT / 'Object-Detection-v9/object_detection').resolve()
os.environ['EDS_OUTPUT_ROOT'] = str(OUTPUT_ROOT)
os.environ['EDS_ARCHIVE_ROOT'] = str(OUTPUT_ROOT)
os.environ['EDS_YOLO_VIEW_ROOT'] = str(ROOT / '.runtime/object_detection_benchmark')
os.environ['EDS_PRETRAINED_ROOT'] = str(ROOT / '.runtime/object_detection_benchmark/pretrained')
os.environ['EDS_YOLO_BACKUP_ROOT'] = str(ROOT / 'YOLO_Weights' / 'v9')
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.runtime/object_detection_benchmark/ultralytics'))
os.environ.setdefault('USE_TF', '0')  # Keep this detector kernel on the PyTorch backend.
os.environ.setdefault('HF_HOME', str(ROOT / '.runtime/object_detection_benchmark/huggingface'))
RUN_PREPARE_YOLO = False  # Optional dataset conversion; training CLI prepares it too.
RUN_TRAINING = False     # Enable manually after reviewing the v9 split audit and verified manifest.
TRAIN_MODEL = 'yolo11n'   # Choose: 'yolo11n', 'yolo11s', or 'detr-resnet-50'.
RUN_BENCHMARK = False     # Existing v9 validation/test reports are saved; enable only for a new experiment.
RUN_FINAL_TEST = False    # The selected v9 held-out test is complete; keep this off.
RUN_ID = 'v9-local-01'  # Baseline/report group; A/B checkpoints use TUNING_RUN_ID.
BENCHMARK_MODELS = ('yolo11n', 'yolo11s', 'detr-resnet-50')
BENCHMARK_MODEL_RUNS = {}  # Optional per-candidate run IDs, e.g. {'detr-resnet-50': 'v9-local-02'}.
YOLO_EPOCHS, DETR_EPOCHS, IMAGE_SIZE, BATCH_SIZE, SEED = 60, 60, 640, 32, 42
YOLO_WORKERS, DETR_MICRO_BATCH_SIZE = 4, 2
RUN_TUNING = False  # Run one fresh YOLO A/B variant; never enable with baseline training or benchmark.
TUNING_MODEL = 'yolo11n'  # 'yolo11n' or 'yolo11s'.
TUNING_VARIANT = 'gentle_aug'  # A: 'gentle_aug'; B: 'localization'.
TUNING_RUN_ID = 'v9-tuning-01'  # Separate from the baseline RUN_ID.
TUNING_BATCH_SIZE = BATCH_SIZE  # Match the model's baseline if it fits; B at 800 may need less.
OPERATING_CONF, YOLO_NMS_IOU = 0.50, 0.70  # Frozen v9 final-test settings selected on validation.
DEVICE = 'cuda' if importlib.util.find_spec('torch') and __import__('torch').cuda.is_available() else 'cpu'
CLASS_NAMES = ('front_eds', 'front_eds_num', 'front_eds_route', 'front_eds_destination')
COCO_TO_INDEX = {1: 0, 3: 1, 4: 2, 2: 3}  # Explicit IDs from the readiness handoff.
INDEX_TO_NAME = dict(enumerate(CLASS_NAMES))
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', RUN_ID):
    raise ValueError('RUN_ID may contain only letters, digits, underscores and hyphens.')
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', TUNING_RUN_ID):
    raise ValueError('TUNING_RUN_ID may contain only letters, digits, underscores and hyphens.')
if TRAIN_MODEL not in ('yolo11n', 'yolo11s', 'detr-resnet-50'):
    raise ValueError(f'Unsupported TRAIN_MODEL: {TRAIN_MODEL!r}')
if TUNING_MODEL not in ('yolo11n', 'yolo11s') or TUNING_VARIANT not in ('gentle_aug', 'localization'):
    raise ValueError('Select YOLO11n/s and either gentle_aug (A) or localization (B).')
if TUNING_BATCH_SIZE < 1:
    raise ValueError('TUNING_BATCH_SIZE must be positive.')
if (RUN_TRAINING and RUN_TUNING) or ((RUN_TRAINING or RUN_TUNING) and (RUN_BENCHMARK or RUN_FINAL_TEST)):
    raise ValueError('Run baseline training, A/B training, and benchmark/test in separate Run All executions.')
if RUN_FINAL_TEST and (not RUN_BENCHMARK or len(BENCHMARK_MODELS) != 1):
    raise ValueError('Final test requires benchmarking exactly one validation-selected candidate.')
if (RUN_TRAINING or RUN_TUNING) and DEVICE != 'cuda':
    raise RuntimeError('Select a CUDA GPU kernel before starting training.')
print({'repo': str(ROOT), 'dataset': str(DATASET_ROOT), 'device': DEVICE,
       'output': str(OUTPUT_ROOT),
       'run_id': RUN_ID, 'train_model': TRAIN_MODEL, 'training': RUN_TRAINING,
       'tuning': RUN_TUNING, 'tuning_model': TUNING_MODEL if RUN_TUNING else None,
       'tuning_variant': TUNING_VARIANT if RUN_TUNING else None,
       'tuning_run_id': TUNING_RUN_ID if RUN_TUNING else None,
       'prepare_yolo': RUN_PREPARE_YOLO, 'benchmark': RUN_BENCHMARK, 'final_test': RUN_FINAL_TEST})
"""),
    md(r"""
## 1. Data and class audit

The four foreground classes are **whole front/side panel**, **service number**, **intermediate route or landmark text**, and **final destination**. `front_eds` is the historical name for both front and side panels. The unused COCO category `0: front-eds` is not a fifth foreground class. The guide distinguishes route from destination by meaning and typography, not by whether text appears above or below another line. A sign with several labelled parts can contain several boxes, including a containing whole-panel box.

An image with zero **reviewed** bounding boxes is a negative example and remains in every relevant split with an empty target. An image merely missing annotations must be reviewed before being declared negative. Rear signs and unrelated bus-stop text are negatives under the current scope.

**Application contract:** the deployed v4 adapter maps the four training labels to stable API labels. Verify a new v9 checkpoint's class order and hash before changing the deployed model. Keep the training taxonomy stable rather than renaming labels inside the training data.

This notebook uses only the manifest-backed v9 stem-isolated export selected in the first code cell. The old v4 and earlier baseline figures later in this notebook are historical context; they are not v9 measurements.
"""),
    code(r"""
def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

DATA_READY, splits, inventory, data_error = False, None, {}, None
try:
    if not DATASET_ROOT.is_dir():
        raise FileNotFoundError(f'Full training export is absent: {DATASET_ROOT}')
    from data_preparation.manifests import verify_export
    from data_preparation.datasets import load_coco_splits
    manifest = verify_export(DATASET_ROOT)
    if manifest is None:
        raise ValueError('No verified export manifest. Use a new manifest-backed version; do not synthesize one from counts.')
    splits = load_coco_splits(DATASET_ROOT)
    for split_name, split in splits.items():
        categories = {c['id']: c['name'] for c in split['data']['categories']}
        for coco_id, index in COCO_TO_INDEX.items():
            if categories.get(coco_id) != CLASS_NAMES[index]:
                raise ValueError(f'{split_name}: COCO category {coco_id} is {categories.get(coco_id)!r}, expected {CLASS_NAMES[index]!r}')
        used = {a['category_id'] for a in split['data']['annotations']}
        if not used <= set(COCO_TO_INDEX):
            raise ValueError(f'{split_name}: unexpected labelled category IDs {used - set(COCO_TO_INDEX)}')
        inventory[split_name] = {'images': len(split['rows']),
                                 'negative_images': sum(not r['annotations'] for r in split['rows']),
                                 'boxes_by_class': {CLASS_NAMES[i]: sum(a['category_id'] == coco_id for a in split['data']['annotations'])
                                                    for coco_id, i in COCO_TO_INDEX.items()},
                                 'coco_sha256': sha256(split['folder'] / '_annotations.coco.json')}
    manifest_path = next(p for p in (DATASET_ROOT / 'augmentation_manifest.json', DATASET_ROOT / 'preparation_manifest.json') if p.is_file())
    DATA_FINGERPRINT = sha256(manifest_path)
    DATA_READY = True
except (FileNotFoundError, ValueError, ImportError) as exc:
    data_error = str(exc)

print(json.dumps({'data_ready': DATA_READY, 'reason_if_not_ready': data_error,
                  'inventory': inventory}, indent=2))
"""),
    md(r"""
### Existing measured result (historical context only)

The branch includes one prior YOLO11n field-detector report. Its 13-image deduplicated subset evaluated only service-number and destination classes from a different bundled YOLO dataset, on a Mac CPU. It is not the four-class EDS benchmark below. The next cell reads the recorded values and limitations directly, rather than transcribing them as new measurements.
"""),
    code(r"""
historical_path = ROOT / 'evaluation/reports/detection.json'
if historical_path.is_file():
    historical = json.loads(historical_path.read_text(encoding='utf-8'))
    print(json.dumps({'run_id': historical['run_id'], 'images': historical['dataset']['image_count'],
                      'classes': historical['detector']['classes'],
                      'metrics': historical['metrics'], 'hardware': historical['hardware'],
                      'limitations': historical['limitations']}, indent=2))
else:
    print('No historical detector report in this checkout.')
"""),
    md(r"""
**Audit gate:** inspect the printed inventory and confirm `data_ready: true` before training. Do not treat `-1` AP (no ground truth for a class) as zero. Capture/recording grouping and semantic review of small, distant signs still require human evidence.

## 2. Convert only the verified export for YOLO; keep original COCO for DETR

The conversion copies images into ignored `.runtime/`, writes one YOLO label file per image (empty for a reviewed negative), and creates an explicit class-name YAML. It does not mutate source COCO files. Conversion is blocked while `DATA_READY` is false.
"""),
    code(r"""
def make_yolo_view():
    import shutil, yaml
    from PIL import Image
    view = Path(os.environ.get('EDS_YOLO_VIEW_ROOT', OUTPUT_ROOT)).resolve() / DATA_FINGERPRINT[:12] / 'yolo'
    if view.exists():
        yaml_path = view / 'data.yaml'
        if not yaml_path.is_file():
            raise FileExistsError(f'Incomplete existing conversion: {view}. Inspect it before rerunning.')
        print('Reusing existing conversion:', yaml_path)
        return yaml_path
    for split_name, split in splits.items():
        image_dir, label_dir = view / 'images' / split_name, view / 'labels' / split_name
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        for row in split['rows']:
            src = row['path']
            with Image.open(src) as opened:
                format_name = opened.format
                needs_png = format_name == 'AVIF' or src.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')
                dest_name = src.stem + '.png' if needs_png else src.name
                if (image_dir / dest_name).exists() or (label_dir / (src.stem + '.txt')).exists():
                    raise ValueError(f'Duplicate output stem in {split_name}: {src.stem}')
                if needs_png:
                    opened.convert('RGB').save(image_dir / dest_name, format='PNG')
                else:
                    shutil.copy2(src, image_dir / dest_name)
            width, height = row['image']['width'], row['image']['height']
            lines = []
            for annotation in row['annotations']:
                x, y, w, h = annotation['bbox']
                index = COCO_TO_INDEX[annotation['category_id']]
                lines.append(f'{index} {(x + w/2)/width:.8f} {(y + h/2)/height:.8f} {w/width:.8f} {h/height:.8f}')
            (label_dir / (src.stem + '.txt')).write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    yaml_path = view / 'data.yaml'
    yaml_path.write_text(yaml.safe_dump({'path': str(view), 'train': 'images/train', 'val': 'images/valid',
                                          'test': 'images/test', 'names': INDEX_TO_NAME}, sort_keys=False), encoding='utf-8')
    return yaml_path

YOLO_DATA_YAML = None
if DATA_READY and RUN_PREPARE_YOLO:
    YOLO_DATA_YAML = make_yolo_view()
    print('Converted verified COCO export:', YOLO_DATA_YAML)
else:
    print('YOLO conversion skipped; training CLI can prepare it when needed.')
"""),
    md(r"""
## Manual model training

The three v9 baselines completed under `v9-local-01`. This cell remains a reusable trainer for a **new** run ID. Select one `TRAIN_MODEL` and set `RUN_TRAINING=True` with all other execution switches off. Training starts from published weights, creates a model-specific folder, and refuses an existing run. It does not resume a checkpoint. Keep this switch off when reading the recorded v9 results.
"""),
    code(r"""
if DATA_READY and RUN_TRAINING:
    import subprocess
    training_epochs = YOLO_EPOCHS if TRAIN_MODEL.startswith('yolo') else DETR_EPOCHS
    # The trainer checks the manifest and refuses an existing model folder.
    command = [sys.executable, str(ROOT / 'scripts/train_object_detection.py'),
               '--model', TRAIN_MODEL, '--run-id', RUN_ID,
               '--dataset', str(DATASET_ROOT), '--epochs', str(training_epochs),
               '--batch-size', str(BATCH_SIZE), '--workers', str(YOLO_WORKERS),
               '--micro-batch-size', str(DETR_MICRO_BATCH_SIZE),
               '--image-size', str(IMAGE_SIZE),
               '--seed', str(SEED)]
    print('Starting fresh model training:', ' '.join(command))
    subprocess.run(command, cwd=ROOT, check=True)
else:
    print('Training paused. Set RUN_TRAINING=True when the model and run ID are ready.')
"""),
    md(r"""
## 3B. Fresh YOLO11n and YOLO11s A/B experiments

Four A/B runs completed under `v9-tuning-01`; see the [plan and measured comparison](../docs/OBJECT_DETECTION_YOLO_TUNING_PLAN.md). Each started from its published COCO weight and updated the full network. This cell is retained for a new tuning run ID and checks for a completed baseline. All variants used the same v9 split, four classes, seed 42, 60-epoch cap, patience 15, deterministic training, and disabled mosaic, MixUp, copy-paste, rotations, flips, hue and saturation changes.

| Candidate | `TUNING_MODEL` | `TUNING_VARIANT` | Changes from that model's baseline | Starting weight |
| --- | --- | --- | --- | --- |
| YOLO11n-A | `yolo11n` | `gentle_aug` | `translate=0.02`, `scale=0.10`, `hsv_v=0.08`; input 640 | `yolo11n.pt` |
| YOLO11n-B | `yolo11n` | `localization` | input 800, `box=8.5`; A transforms off | `yolo11n.pt` |
| YOLO11s-A | `yolo11s` | `gentle_aug` | same gentle changes as n-A | `yolo11s.pt` |
| YOLO11s-B | `yolo11s` | `localization` | same localization changes as n-B | `yolo11s.pt` |

**A: gentle variation.** Translation, scale, and brightness changes affect training images and boxes only. V9 already contains saved augmentation; the measured validation comparison determines whether this extra variation helped.

**B: localization package.** Input size 800 and box gain 8.5 target small EDS fields. Both B runs used batch 16, versus batch 32 for their baselines and A runs; this is an additional optimization difference. B was benchmarked at 800 pixels.

**For a new A/B experiment:** keep baseline training, benchmark, and final test off; enable `RUN_TUNING` for one model and variant. Use a new `TUNING_RUN_ID`. Each variant has separate settings, epoch CSV, checkpoints, and completion marker; the trainer also backs up its weights under `YOLO_Weights/v9/`. Existing runs are not overwritten.

The common evaluator reads each completed candidate's saved input size. The seven-model validation comparison and one selected-model final test are recorded below. Do not use the held-out test to reselect a model or tune thresholds.
"""),
    code(r"""
if DATA_READY and RUN_TUNING:
    import subprocess
    import yaml
    # Tuning must start from published weights in a separate run, after its baseline.
    if TUNING_RUN_ID == RUN_ID:
        raise ValueError('Keep the A/B tuning run ID separate from the baseline run ID.')
    baseline_dir = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs' / RUN_ID / TUNING_MODEL
    if not (baseline_dir / 'complete.txt').is_file():
        raise FileNotFoundError(f'Complete local baseline required before A/B: {baseline_dir}')
    baseline_args = yaml.safe_load((baseline_dir / 'args.yaml').read_text(encoding='utf-8'))
    if int(baseline_args['batch']) != TUNING_BATCH_SIZE:
        print('Comparison note: variant batch differs from baseline:',
              {'baseline': baseline_args['batch'], 'variant': TUNING_BATCH_SIZE})
    tuning_name = f'{TUNING_MODEL}-{TUNING_VARIANT}'
    tuning_dir = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs' / TUNING_RUN_ID / tuning_name
    if tuning_dir.exists():
        raise FileExistsError(f'Variant run already exists and will not be overwritten: {tuning_dir}')
    tuning_size = 800 if TUNING_VARIANT == 'localization' else 640
    command = [sys.executable, str(ROOT / 'scripts/train_object_detection.py'),
               '--model', TUNING_MODEL, '--variant', TUNING_VARIANT,
               '--run-id', TUNING_RUN_ID, '--dataset', str(DATASET_ROOT),
               '--epochs', str(YOLO_EPOCHS), '--batch-size', str(TUNING_BATCH_SIZE),
               '--workers', str(YOLO_WORKERS), '--image-size', str(tuning_size),
               '--seed', str(SEED)]
    print('Starting fresh A/B run:', ' '.join(command))
    subprocess.run(command, cwd=ROOT, check=True)
else:
    print('A/B training paused. Set RUN_TUNING=True only for one selected YOLO variant.')
"""),
    md(r"""
## 4. Common evaluation: all four classes, all splits, and negatives

Measure box mAP@0.50 and mAP@0.50:0.95 per class using the same COCO targets and TorchMetrics implementation for each selected candidate. Include zero-box images: predictions on them are false positives. Also report false positives per negative image at the v4 operating score ≥ 0.50, median/p95 end-to-end detector inference milliseconds per image, and sample count. Train metrics describe fit and are optimistic; validation is for selection; test is held out. `RUN_BENCHMARK=True` evaluates train+valid for `BENCHMARK_MODELS`, even if only one checkpoint exists. Each selection writes a separate JSON report. `RUN_FINAL_TEST=True` evaluates test after validation-based model and thresholds are frozen. The small historical YOLO report in `evaluation/reports/detection.json` is separate: it covers two field classes on 13 images from another dataset and cannot fill this table.
"""),
    code(r"""
MODEL_PATHS, TRAINING_HISTORY, MODEL_RUN_IDS, MODEL_IMAGE_SIZES = {}, {}, {}, {}
if DATA_READY:
    import yaml
    # Resolve each completed candidate from its own run ID; B uses its saved 800px size.
    yolo_candidates = tuple(
        f'{base}{suffix}' for base in ('yolo11n', 'yolo11s')
        for suffix in ('', '-gentle_aug', '-localization'))
    for candidate in yolo_candidates:
        default_run_id = TUNING_RUN_ID if '-' in candidate else RUN_ID
        candidate_run_id = BENCHMARK_MODEL_RUNS.get(candidate, default_run_id)
        run_dir = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs' / candidate_run_id / candidate
        checkpoint = run_dir / 'weights/best.pt'
        args_path = run_dir / 'args.yaml'
        # A partial epoch log is not an eligible benchmark checkpoint.
        if checkpoint.is_file() and args_path.is_file() and (run_dir / 'complete.txt').is_file():
            saved_args = yaml.safe_load(args_path.read_text(encoding='utf-8'))
            MODEL_PATHS[candidate] = str(checkpoint)
            MODEL_RUN_IDS[candidate] = candidate_run_id
            MODEL_IMAGE_SIZES[candidate] = int(saved_args['imgsz'])
            TRAINING_HISTORY[candidate] = {'history_csv': str(run_dir / 'results.csv'),
                                           'run_id': candidate_run_id,
                                           'image_size': MODEL_IMAGE_SIZES[candidate]}
    detr_run_id = BENCHMARK_MODEL_RUNS.get('detr-resnet-50', RUN_ID)
    detr_dir = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs' / detr_run_id / 'detr-resnet-50'
    if (detr_dir / 'config.json').is_file() and (detr_dir / 'complete.txt').is_file():
        MODEL_PATHS['detr-resnet-50'] = str(detr_dir)
        MODEL_RUN_IDS['detr-resnet-50'] = detr_run_id
        MODEL_IMAGE_SIZES['detr-resnet-50'] = IMAGE_SIZE
print('Completed runs for evaluation:', MODEL_PATHS)
"""),
    code(r"""
BENCHMARK = {}
if RUN_BENCHMARK:
    if not BENCHMARK_MODELS or len(set(BENCHMARK_MODELS)) != len(BENCHMARK_MODELS):
        raise ValueError('BENCHMARK_MODELS must list each selected model once.')
    missing = set(BENCHMARK_MODELS) - set(MODEL_PATHS)
    if missing:
        raise FileNotFoundError(f'Complete checkpoint required for: {sorted(missing)}')
if DATA_READY and RUN_BENCHMARK:
    import numpy as np
    import torch
    from PIL import Image
    from torchmetrics.detection.mean_ap import MeanAveragePrecision
    from transformers import DetrForObjectDetection, DetrImageProcessor
    from ultralytics import YOLO

    def target_for(row):
        boxes = [[a['bbox'][0], a['bbox'][1], a['bbox'][0]+a['bbox'][2], a['bbox'][1]+a['bbox'][3]]
                 for a in row['annotations']]
        labels = [COCO_TO_INDEX[a['category_id']] for a in row['annotations']]
        return {'boxes': torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4),
                'labels': torch.tensor(labels, dtype=torch.int64)}

    def make_predictor(name, location):
        if name.startswith('yolo'):
            model = YOLO(location)
            def predict(image):
                bgr = np.asarray(image)[:, :, ::-1].copy()  # Ultralytics NumPy input expects OpenCV BGR.
                # The low cutoff supplies AP's score sweep; OPERATING_CONF is reported separately.
                out = model.predict(bgr, imgsz=MODEL_IMAGE_SIZES[name], conf=0.001,
                                    iou=YOLO_NMS_IOU, device=DEVICE, verbose=False)[0]
                b = out.boxes
                return {'boxes': b.xyxy.cpu().float(), 'scores': b.conf.cpu().float(),
                        'labels': b.cls.cpu().long()}
            return predict
        proc = DetrImageProcessor.from_pretrained(location)
        model = DetrForObjectDetection.from_pretrained(location).to(DEVICE).eval()
        def predict(image):
            inputs = proc(images=image, size={'shortest_edge': IMAGE_SIZE, 'longest_edge': IMAGE_SIZE},
                          return_tensors='pt')
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            with torch.inference_mode():
                out = model(**inputs)
            pred = proc.post_process_object_detection(out, threshold=0.001,
                target_sizes=torch.tensor([[image.height, image.width]], device=DEVICE))[0]
            return {k: v.cpu() for k, v in pred.items() if k in ('boxes', 'scores', 'labels')}
        return predict

    def evaluate_split(predict, rows):
        # All candidates use the same COCO targets, including empty targets on negatives.
        metric = MeanAveragePrecision(box_format='xyxy', class_metrics=True)
        metric50 = MeanAveragePrecision(box_format='xyxy', iou_thresholds=[0.5], class_metrics=True)
        latencies, negative_fp, negatives = [], 0, 0
        if rows:
            with Image.open(rows[0]['path']) as opened:
                warm_image = opened.convert('RGB')
            for _ in range(3): predict(warm_image)  # Keep cold model/cache startup out of timing.
        for row in rows:
            with Image.open(row['path']) as opened:
                image = opened.convert('RGB')
            if DEVICE == 'cuda': torch.cuda.synchronize()
            started = time.perf_counter()
            pred = predict(image)
            if DEVICE == 'cuda': torch.cuda.synchronize()
            latencies.append(1000 * (time.perf_counter() - started))
            target = target_for(row)
            metric.update([pred], [target])
            metric50.update([pred], [target])
            if not row['annotations']:
                negatives += 1
                negative_fp += int((pred['scores'] >= OPERATING_CONF).sum())
        result, result50 = metric.compute(), metric50.compute()
        by_class = {}
        for i, class_id in enumerate(result['classes'].tolist()):
            j = result50['classes'].tolist().index(class_id)
            ap50, ap = float(result50['map_per_class'][j]), float(result['map_per_class'][i])
            by_class[CLASS_NAMES[class_id]] = {
                'map50': None if ap50 < 0 else ap50,
                'map50_95': None if ap < 0 else ap,
                'mar_100': float(result['mar_100_per_class'][i])}
        return {'images': len(rows), 'negatives': negatives,
                'map50': float(result50['map_50']), 'map50_95': float(result['map']),
                'mar_100': float(result['mar_100']),
                'by_class': by_class, 'false_positives_on_negatives_at_operating_conf': negative_fp,
                'median_inference_ms': float(np.median(latencies)),
                'p95_inference_ms': float(np.percentile(latencies, 95))}

    for name in BENCHMARK_MODELS:
        location = MODEL_PATHS[name]
        predict = make_predictor(name, location)
        BENCHMARK[name] = {'train': evaluate_split(predict, splits['train']['rows']),
                           'valid': evaluate_split(predict, splits['valid']['rows'])}
        if RUN_FINAL_TEST:
            # Open test only after the model and threshold are fixed on validation.
            BENCHMARK[name]['test'] = evaluate_split(predict, splits['test']['rows'])
        print(name, json.dumps(BENCHMARK[name], indent=2))
else:
    print('Benchmark paused. Enable RUN_BENCHMARK and choose completed BENCHMARK_MODELS.')
"""),
    md(r"""
## 5. Validation threshold and overlap suppression

mAP sweeps confidence thresholds internally, so evaluate it with a low prediction cutoff (`0.001`). Separately choose the **operating** confidence threshold using validation only. The following code counts class-correct matches at IoU ≥ 0.50 (one prediction per ground-truth box), along with false positives on reviewed negative images. It reports a threshold sweep for the highest-validation-mAP candidate. Inspect the precision/recall tradeoff and OCR crops before freezing the setting. For YOLO, repeat the validation sweep with NMS IoU 0.50 and 0.70 if duplicate boxes are a problem; DETR does not require NMS by design.
"""),
    code(r"""
THRESHOLD_SWEEP = []
if DATA_READY and BENCHMARK:
    import torch
    from PIL import Image
    from torchvision.ops import box_iou

    # Selection uses validation only, even in the one-model final-test execution.
    selected = max(BENCHMARK, key=lambda name: BENCHMARK[name]['valid']['map50_95'])
    predict = make_predictor(selected, MODEL_PATHS[selected])
    cached = []
    for row in splits['valid']['rows']:
        with Image.open(row['path']) as opened:
            pred = predict(opened.convert('RGB'))
        cached.append((pred, target_for(row)))

    for threshold in (0.10, 0.20, 0.30, 0.50, 0.70):
        tp = fp = fn = negative_fp = 0
        for pred, target in cached:
            keep = (pred['scores'] >= threshold).nonzero(as_tuple=True)[0]
            keep = keep[torch.argsort(pred['scores'][keep], descending=True)]
            assigned = set()
            for index in keep.tolist():
                same = (target['labels'] == pred['labels'][index]).nonzero(as_tuple=True)[0]
                same = [j for j in same.tolist() if j not in assigned]
                if same:
                    ious = box_iou(pred['boxes'][index:index+1], target['boxes'][same])[0]
                    best = int(torch.argmax(ious))
                    if float(ious[best]) >= 0.50:
                        tp += 1
                        assigned.add(same[best])
                        continue
                fp += 1
                if not len(target['labels']): negative_fp += 1
            fn += len(target['labels']) - len(assigned)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        THRESHOLD_SWEEP.append({'model': selected, 'threshold': threshold,
                                'precision_iou50': precision, 'recall_iou50': recall,
                                'f1_iou50': 2*precision*recall/(precision+recall) if precision+recall else 0.0,
                                'negative_false_positives': negative_fp})
    print(json.dumps(THRESHOLD_SWEEP, indent=2))
else:
    print('Threshold selection pending validation predictions.')
"""),
    md(r"""
## 6. Measured v9 comparison and final test

All seven candidates finished training on the same verified v9 export. The separate [three-model baseline report](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11n_yolo11s_detr-resnet-50_validation.json) and [six-model YOLO comparison](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11n_yolo11s_yolo11n-gentle_aug_yolo11n-localization_yolo11s-gentle_aug_yolo11s-localization_validation.json) record per-class train/validation AP, negative-image detections, and latency. These are results from best checkpoints, not each model's final epoch.

| Candidate | Validation mAP50:95 | Negative-image FP at 0.50 | Median inference |
| --- | ---: | ---: | ---: |
| YOLO11n | 63.5% | 9 | 14.9 ms |
| YOLO11s | 63.9% | 11 | 15.0 ms |
| DETR-ResNet50 | 54.3% | 51 | 41.2 ms |
| YOLO11n-A, gentle augmentation | 66.8% | 7 | 15.2 ms |
| YOLO11n-B, localization | 67.4% | 3 | 15.8 ms |
| **YOLO11s-A, gentle augmentation** | **68.4%** | 13 | 16.4 ms |
| YOLO11s-B, localization | 65.3% | 6 | 16.3 ms |

Validation mAP50:95 selected YOLO11s-A. At confidence `0.50` and NMS IoU `0.70`, its [one held-out test](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test.json) scored mAP50 `90.5%`, mAP50:95 `68.2%`, and mAR@100 `74.3%` on 299 images. Test mAP50:95 by class was panel `52.0%`, number `74.9%`, route `68.9%`, and destination `76.9%`. There were 17 detections on 20 negative test images at the frozen operating threshold; median inference was `16.3 ms` on the tested CUDA laptop. The [split tables](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test_tables.md), [selected checkpoint](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-tuning-01/yolo11s-gentle_aug/weights/best.pt), and [v9 result index](../Object-Detection-v9/RESULTS.md) preserve the evidence. The test is closed for model selection. Bus type, lighting, angle, and OCR crop quality still need a separate qualitative review.
"""),
    md(r"""
## 7. Historical detector results

### Recorded `v4-reviewed-01` benchmark and final test

The reviewed v4 export has 735 train, 53 validation and 53 test images. All three models trained for up to 60 epochs with seed 42, 640-pixel input and CUDA. The validation comparison selected YOLO11s by mAP50:95; only it received a final held-out test.

| Model | Validation mAP50 / mAP50:95 | Final test mAP50 / mAP50:95 |
| --- | --- | --- |
| YOLO11n | 0.6250 / 0.3383 | Not tested |
| **YOLO11s** | **0.6131 / 0.3510** | **0.6314 / 0.3270** |
| DETR-ResNet50 | 0.4377 / 0.1746 | Not tested |

YOLO11s test AP50 / AP50:95 by class: panel `0.7467 / 0.3158`, number `0.7934 / 0.5246`, route `0.4116 / 0.2027`, destination `0.5739 / 0.2651`. At the validation-selected confidence `0.50`, one false positive occurred across 12 zero-box test images; median / p95 inference was `26.46 / 36.57 ms`. Full training settings, per-class validation AP, hashes and evidence paths are in the [v4 results report](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md). The older result below uses a different dataset and is historical.

**Validation-only follow-up:** NMS IoU `0.50` scored mAP50:95 `0.3532` versus `0.3510` at the recorded `0.70` setting. The final test belongs to `0.70`; the later [NMS and crop review](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/validation_review/REVIEW.md) is exploratory. The [v4 configuration](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/detector_config.json) preserves the tested settings. Jy/Brendan human annotation review is on hold.

### Recorded `baseline-01` benchmark results

The following measurements were saved on 2 November 2026 using dataset manifest `bf938f526d2c01f1960b9af018f1fd1dc78a431e725037c84d1707dfcc5b826c`, CUDA, 640-pixel input, seed 42, and the best validation-selected checkpoint from each training run.

| Candidate | Train mAP50 / mAP50:95 | Valid mAP50 / mAP50:95 | Test mAP50 / mAP50:95 | Test median / p95 ms | Test negative FP |
|---|---|---|---|---|---:|
| YOLO11n | 0.8910 / 0.7451 | 0.5709 / 0.3466 | 0.7165 / 0.4139 | 40.21 / 123.25 | 0 |
| **YOLO11s** | **0.9140 / 0.8024** | **0.6734 / 0.4274** | 0.7077 / 0.3938 | **34.22** / 128.14 | 0 |
| DETR-ResNet50 | 0.3446 / 0.1504 | 0.3127 / 0.1359 | 0.2873 / 0.1251 | 83.79 / 191.24 | 7 |

Test per-class AP:

| Candidate | EDS panel | Number | Route / landmark | Destination |
|---|---|---|---|---|
| YOLO11n | 0.7088 / 0.3928 | 0.8356 / 0.5593 | 0.6677 / 0.3455 | 0.6539 / 0.3578 |
| **YOLO11s** | **0.8478 / 0.3865** | 0.7950 / **0.5704** | 0.6310 / **0.3476** | 0.5573 / 0.2706 |
| DETR-ResNet50 | 0.5560 / 0.2707 | 0.3446 / 0.1508 | 0.1168 / 0.0347 | 0.1317 / 0.0441 |

Each per-class entry is `mAP50 / mAP50:95`. YOLO11s remains the selected model because selection was based on the highest validation mAP50:95 (`0.4274`), before opening the held-out test. Its validation threshold sweep had the highest F1 at confidence `0.20` (`0.7032`) with no false positives on four reviewed validation negatives. NMS IoU remained `0.70`.

**Recorded execution deviation:** the final Run All used `BENCHMARK_MODELS=('yolo11n', 'yolo11s', 'detr-resnet-50')` and `OPERATING_CONF=0.30`, so the test report contains all three models and negative false-positive counts at `0.30`. The mAP calculation used predictions from score `0.001`, but the test did not measure the validation-selected operating threshold `0.20`. Do not use the test results to reselect a model or tune settings, and do not rerun the test to optimize them.

**Quantitative interpretation:** YOLO11s provides the strongest validation result and lowest median test latency. Number detection is its strongest localized class. DETR is slower, has substantially lower AP, and produced false positives on reviewed negatives. The 20-image test split is small, including only two reviewed negatives.

**Validation qualitative review:** the ten highest-priority YOLO11s cases were inspected at the validation-selected confidence `0.20`. The ranked cases contained 61 GT boxes: 52 occupied less than 1% of the image and 36 less than 0.25%. Diagnostic class-correct matching counted 109 TP, 47 FP and 45 FN across all 39 validation images, with 17 destination-to-route and 10 route-to-destination confusion candidates. Blur, glare, oblique perspective, crowding and partial occlusion also made several crops unsuitable for OCR. None of four reviewed validation negatives produced a prediction. These counts are diagnostics, not COCO mAP. The review package is under `evaluation/object_detection/bf938f526d2c/runs/baseline-01/yolo11s/qualitative_validation/`.

**Task 3 annotation/split audit:** a human-review packet now covers the 137 original training, 39 validation and 20 test images. Structural heuristics flag 15 images containing 17 panels without associated content boxes, and the packet inventories all 22 original zero-box images. Twelve timestamp-derived filename groups cross splits, including same-minute screenshot/image sequences. This is a recording-level isolation warning, not proof of leakage; source/capture records are required to decide it. No labels or splits were changed, and the checklist remains open pending Brendan/Jy decisions. Evidence is under `evaluation/object_detection/bf938f526d2c/runs/baseline-01/data_review/`.

**Application handoff status:** the selected YOLO11s checkpoint was installed and SHA-256 verified locally. The app now requests all four model classes and explicitly maps them to stable API labels: `front_eds→eds`, `front_eds_num→bus_number`, `front_eds_route→route`, and `front_eds_destination→destination`. Real CUDA verification detected two displays and all four field types in a multi-bus image (five-run detector median `35.249 ms`). A four-frame uploaded-video fixture verified decode, timestamps, association and detector flow (`73.706 ms` median / `145.758 ms` p95 total); a labelled still exercised the simulated camera response path. Production OCR/reference matching and a physical-camera field run remain open because local OCR assets, Tesseract, the route CSV and camera evidence are unavailable. Evidence is under `evaluation/object_detection/bf938f526d2c/runs/baseline-01/deployment/`.

**EasyOCR integration status:** English EasyOCR assets were installed locally and the real CPU adapter processed YOLO11s number/route/destination crops. Across six diagnostic runs, OCR latency was `184.363 ms` median / `382.270 ms` p95 and total processing was `231.409 ms` median / `558.472 ms` p95. Raw readings on the small/distant cases were often wrong or below the `0.25` acceptance threshold, consistent with the qualitative crop review. No accuracy is claimed without reviewed transcriptions. Missing route-reference data now degrades to an unmatched raw-OCR result rather than disabling the app. Tesseract, fine-tuned TrOCR and a physical-camera moving-bus field run remain open.
"""),
    code((Path(__file__).parents[1] / 'scripts/object_detection_tables.py').read_text(encoding='utf-8')),
    code(r"""
if DATA_READY and BENCHMARK:
    import importlib.metadata as metadata
    report = {'dataset_root': str(DATASET_ROOT), 'dataset_manifest_sha256': DATA_FINGERPRINT,
              'inventory': inventory, 'class_map': {str(k): v for k, v in COCO_TO_INDEX.items()},
              'run_id': RUN_ID, 'models': MODEL_PATHS,
              'model_run_ids': MODEL_RUN_IDS, 'model_image_sizes': MODEL_IMAGE_SIZES,
              'training_history': TRAINING_HISTORY,
              'benchmark': BENCHMARK, 'validation_threshold_sweep': THRESHOLD_SWEEP,
              'settings': {'yolo_epochs': YOLO_EPOCHS,
              'detr_epochs': DETR_EPOCHS, 'image_size': IMAGE_SIZE, 'batch_size': BATCH_SIZE,
              'workers': YOLO_WORKERS, 'detr_micro_batch_size': DETR_MICRO_BATCH_SIZE,
              'seed': SEED, 'device': DEVICE, 'operating_conf': OPERATING_CONF,
              'yolo_nms_iou': YOLO_NMS_IOU, 'final_test_run': RUN_FINAL_TEST},
              'environment': {'platform': platform.platform(), 'python': sys.version,
              'torch': metadata.version('torch'), 'ultralytics': metadata.version('ultralytics'),
              'transformers': metadata.version('transformers'), 'torchmetrics': metadata.version('torchmetrics')}}
    suffix = '_'.join(BENCHMARK_MODELS)
    phase = 'test' if RUN_FINAL_TEST else 'validation'
    destination = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs' / RUN_ID / f'benchmark_{suffix}_{phase}.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    # Keep the combined comparison and a per-model copy alongside that checkpoint.
    for name in BENCHMARK_MODELS:
        archive_benchmark(ROOT, DATA_FINGERPRINT, name, phase, report, MODEL_RUN_IDS[name])
    from IPython.display import Markdown, display
    comparison_runs = ', '.join(sorted({MODEL_RUN_IDS[name] for name in BENCHMARK_MODELS}))
    tables = render_split_tables(BENCHMARK, inventory, CLASS_NAMES, comparison_runs)
    table_path = destination.with_name(destination.stem + '_tables.md')
    table_path.write_text(tables, encoding='utf-8')
    display(Markdown(tables))
    print('Evidence saved:', destination)
    print('Split tables saved:', table_path)
else:
    print('No measured benchmark report was written. The table remains pending.')
"""),
    md(r"""
## 8. YOLO loss research and how to apply it

The supplied slides illustrate three YOLO detection-loss parts. The pinned Ultralytics YOLO11 implementation uses **CIoU box loss**, **BCE classification loss**, and **distribution focal loss (DFL)** for the four box-edge distance distributions. In shorthand, `L = box_gain × L_CIoU + cls_gain × L_BCE + dfl_gain × L_DFL`; the trainer logs `train/box_loss`, `train/cls_loss`, `train/dfl_loss` and corresponding validation losses. CIoU accounts for overlap, centre distance and aspect ratio. DFL is a box-distance regression term, *not* the same as classification focal loss. The slide's BCE-to-focal arrow is an optional experiment, not the default YOLO11 loss. DETR has a different matching/classification/box objective, so do not compare raw loss values across architectures.

**Project application:** keep YOLO11 defaults for the controlled baseline and record all three curves. Inspect per-class AP and negative-image false positives first. If small EDS or route boxes remain poorly localized, change one documented parameter at a time (`box` or `dfl`) and compare validation mAP50:95 and crop quality. If a verified class imbalance causes route/destination mistakes, test `cls` gain and sampling before considering a separately implemented focal-loss ablation. Do not claim focal loss is active merely because DFL appears in the logs. Retain the same test split and class mapping across ablations.

Primary references: [Ultralytics detection loss source](https://docs.ultralytics.com/reference/utils/loss), [Ultralytics training settings](https://docs.ultralytics.com/modes/train), [CIoU paper](https://arxiv.org/abs/1911.08287), [Focal Loss paper](https://arxiv.org/abs/1708.02002), [Generalized Focal Loss paper](https://arxiv.org/abs/2006.04388), [DETR paper](https://arxiv.org/abs/2005.12872).

## 9. Remaining v9 review

- [x] Train YOLO11n, YOLO11s, DETR, and four YOLO A/B variants with saved settings and checkpoints.
- [x] Compare the seven candidates on validation and run one final test for the selected YOLO11s-A checkpoint.
- [x] Preserve per-class AP, negative-image detections, latency, hashes, and split tables in the [v9 results index](../Object-Detection-v9/RESULTS.md).
- [ ] Review source scenes and annotation completeness with the data owners; the automated manifest and split checks do not prove every box is correct.
- [ ] Describe v9 successes and failures by bus type, lighting, angle, distance, and OCR crop quality. Inspect the 17 test-set detections on negative images.
- [ ] Decide separately whether to replace the deployed v4 detector; the measured v9 checkpoint has not been installed or tested in the application path.
"""),
]

notebook = {'nbformat': 4, 'nbformat_minor': 5, 'cells': cells, 'metadata': {
    'kernelspec': {'display_name': 'CVDL Detector (CUDA)', 'language': 'python', 'name': 'cvdl-detector'},
    'language_info': {'name': 'python'},
}}
v9_result_index = next(i for i, cell in enumerate(notebook['cells'])
                       if cell['cell_type'] == 'markdown'
                       and cell['source'].startswith('## 6. Measured v9 comparison'))
for index, cell in enumerate(notebook['cells']):
    # Keep existing cell IDs stable so executed notebook outputs can be retained.
    cell['id'] = ('eds-detector-v9-results' if index == v9_result_index
                  else f'eds-detector-{index + 1 if index < v9_result_index else index:02d}')
destination = Path(os.environ.get(
    'EDS_NOTEBOOK_DESTINATION', Path(__file__).with_name('object_detection_benchmark.ipynb')))
destination.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(destination)
