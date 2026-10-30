"""Build the self-contained EDS detector research notebook."""
from pathlib import Path
from contextlib import redirect_stdout
import json
from io import StringIO

def md(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source.strip()}


def code(source):
    return {'cell_type': 'code', 'metadata': {}, 'source': source.strip(),
            'execution_count': None, 'outputs': []}


cells = [
    md(r"""
# EDS object detection: YOLO11n, YOLO11s, and DETR

**Status (30 October 2026): the uploaded source has been audited and a manifest-backed `2026-10-30-torchvision` export is available locally; no new model was trained or measured yet.** Results below stay **pending** until the experiment cells are run. Do not copy the historical 13-image YOLO result into this comparison.

This notebook implements the object detection allocation: dataset/label audit, pretrained model selection, fine-tuning, validation, per-class mAP, speed/failure comparison, threshold selection, and a final held-out test. It retains train/valid/test separation and records settings and hashes. Run from the repo's `notebooks/` folder or repo root.

Sources: [task allocation PDF](file:///C:/Users/brend/Downloads/CVDL_Task_Allocation.pdf), [training inventory](../data/training/README.md), [readiness handoff](../docs/data_preparation/TRAINING_READINESS.md), [annotation guide](../docs/annotation/guide.md), [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11), [Hugging Face DETR](https://huggingface.co/docs/transformers/v4.51.1/en/model_doc/detr).

## Environment and run controls

Use a dedicated Python environment. Install a PyTorch build appropriate to this machine, then `ultralytics==8.3.158 transformers>=4.52,<5 timm torchmetrics pycocotools pyyaml pillow nbformat ipykernel`. Keep it separate from the pinned data-preparation environment, which uses Transformers 5.x. Pretrained weights may download when training is enabled. The first run is a safe preflight: set the three switches below deliberately after the dataset is available.
"""),
    code(r"""
from pathlib import Path
import hashlib, importlib.util, json, os, platform, statistics, sys, time
from collections import Counter

ROOT = Path.cwd().resolve()
if not (ROOT / 'src').is_dir():
    ROOT = ROOT.parent
assert (ROOT / 'src').is_dir(), 'Run from the repository root or notebooks/ folder.'
sys.path.insert(0, str(ROOT / 'src'))

DATASET_ROOT = Path(os.environ.get('EDS_DATASET_ROOT', ROOT / 'data/training/2026-10-30-torchvision')).resolve()
OUTPUT_ROOT = ROOT / '.runtime/object_detection_benchmark'
os.environ.setdefault('YOLO_CONFIG_DIR', str(OUTPUT_ROOT / 'ultralytics'))
os.environ.setdefault('USE_TF', '0')  # Keep this detector kernel on the PyTorch backend.
os.environ.setdefault('HF_HOME', str(OUTPUT_ROOT / 'huggingface'))
RUN_TRAINING = False       # Explicitly enable only after the verified-data preflight passes.
RUN_YOLO11N = False
RUN_YOLO11S = False
RUN_DETR = False
RUN_BENCHMARK = False      # Train/valid mAP and latency for BENCHMARK_MODELS.
RUN_FINAL_TEST = False     # Enable once, after settings/model selection on validation.
BENCHMARK_MODELS = ('yolo11n',)  # Choose one completed model per run, or list all three.
YOLO_EPOCHS, DETR_EPOCHS, IMAGE_SIZE, BATCH_SIZE, SEED = 30, 30, 640, 4, 42
OPERATING_CONF, YOLO_NMS_IOU = 0.30, 0.70  # Freeze from validation before opening test.
DEVICE = 'cuda' if importlib.util.find_spec('torch') and __import__('torch').cuda.is_available() else 'cpu'
CLASS_NAMES = ('front_eds', 'front_eds_num', 'front_eds_route', 'front_eds_destination')
COCO_TO_INDEX = {1: 0, 3: 1, 4: 2, 2: 3}  # Explicit IDs from the readiness handoff.
INDEX_TO_NAME = dict(enumerate(CLASS_NAMES))
print({'repo': str(ROOT), 'dataset': str(DATASET_ROOT), 'device': DEVICE,
       'training': RUN_TRAINING, 'benchmark': RUN_BENCHMARK, 'final_test': RUN_FINAL_TEST})
"""),
    md(r"""
## 1. Data and class audit

The four foreground classes are **whole front/side panel**, **service number**, **intermediate route or landmark text**, and **final destination**. `front_eds` is the historical name for both front and side panels. The unused COCO category `0: front-eds` is not a fifth foreground class. The guide distinguishes route from destination by meaning and typography, not by whether text appears above or below another line. A sign with several labelled parts can contain several boxes, including a containing whole-panel box.

An image with zero **reviewed** bounding boxes is a negative example and remains in every relevant split with an empty target. An image merely missing annotations must be reviewed before being declared negative. Rear signs and unrelated bus-stop text are negatives under the current scope.

**Integration gap to resolve:** the current reader adapter filters model class IDs `[1, 2, 3]`, and its association service recognises labels `eds`, `bus_number`, and `destination`. A new four-class checkpoint trained with the indices below would emit `front_eds` at index 0 and `front_eds_route` at index 2. Update the adapter's ID/name mapping and the association/output contract before deploying it; otherwise the whole-panel class can be dropped and route boxes can be ignored. Keep the training taxonomy stable rather than renaming labels inside the training data to match legacy app labels.

The uploaded `2026-10-24` Roboflow export has 420/39/20 images but no manifest. The separately built `2026-10-30-torchvision` export contains 411/39/20 images with a manifest; this notebook uses the latter by default. These are distinct dataset versions and their results must not be mixed. Do not overwrite the Roboflow folder or claim it was produced by the torchvision recipe.
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
**Audit finding:** automated checks pass for the labelled source and the new export's manifest, images, boxes and class IDs. Inspect per-class box counts and negative counts in the output above. Do not treat `-1` AP (no ground truth for a class) as zero. Capture/recording grouping and semantic review of small, distant signs still require human evidence. The 420-image Roboflow snapshot is not certified by this notebook.

## 2. Convert only the verified export for YOLO; keep original COCO for DETR

The conversion copies images into ignored `.runtime/`, writes one YOLO label file per image (empty for a reviewed negative), and creates an explicit class-name YAML. It does not mutate source COCO files. Conversion is blocked while `DATA_READY` is false.
"""),
    code(r"""
def make_yolo_view():
    import shutil, yaml
    from PIL import Image
    view = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'yolo'
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
if DATA_READY and RUN_TRAINING and (RUN_YOLO11N or RUN_YOLO11S):
    YOLO_DATA_YAML = make_yolo_view()
    print('Converted verified COCO export:', YOLO_DATA_YAML)
else:
    print('YOLO conversion pending verified data and RUN_TRAINING=True.')
"""),
    md(r"""
## 3. Pretrained candidates and training protocol

Candidates: official COCO-pretrained `yolo11n.pt`, `yolo11s.pt`, and `facebook/detr-resnet-50`. Their pretrained COCO class scores are **not EDS benchmark scores**; all three require a four-class head fine-tuned on the same EDS train split. YOLO11n and YOLO11s use the same Ultralytics recipe, seed, input size, and offline augmented data. Additional online geometric/color augmentation is disabled for this first controlled comparison to avoid silently augmenting an already augmented export. DETR uses its own optimizer and Hungarian-matching loss; equal epoch counts do not mean equal compute, so record wall time and hardware. Validation selects checkpoints; test remains closed until the protocol is frozen.

The notebook defaults to no training. To train one model, set `RUN_TRAINING=True` and only that model's `RUN_YOLO11N`, `RUN_YOLO11S`, or `RUN_DETR` switch to `True`, then run its own cell. Training can take hours, especially DETR. For a completed model, set `RUN_TRAINING=False`, `RUN_BENCHMARK=True`, and `BENCHMARK_MODELS` to a one-model tuple such as `('yolo11n',)` to calculate train/valid metrics and save its report. Compare validation results for all three, freeze model/threshold settings, then set `RUN_FINAL_TEST=True` for the selected model's one-time held-out measurement.
"""),
    code(r"""
MODEL_PATHS, TRAINING_HISTORY = {}, {}
if DATA_READY:
    saved_runs = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs'
    for candidate in ('yolo11n', 'yolo11s'):
        checkpoint = saved_runs / candidate / 'weights/best.pt'
        if checkpoint.is_file() and (saved_runs / candidate / 'complete.txt').is_file():
            MODEL_PATHS[candidate] = str(checkpoint)
    detr_checkpoint = saved_runs / 'detr-resnet-50'
    if (detr_checkpoint / 'config.json').is_file() and (detr_checkpoint / 'complete.txt').is_file():
        MODEL_PATHS['detr-resnet-50'] = str(detr_checkpoint)
def train_yolo(candidate):
    from ultralytics import YOLO
    if candidate in MODEL_PATHS:
        print('Reusing checkpoint:', candidate, MODEL_PATHS[candidate])
        return
    started = time.perf_counter()
    run_dir = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs' / candidate
    last = run_dir / 'weights/last.pt'
    if last.is_file() and not (run_dir / 'complete.txt').is_file():
        print('Resuming interrupted run from:', last)
        model = YOLO(str(last))
        model.train(resume=True, device=DEVICE)
    else:
        pretrained = OUTPUT_ROOT / 'pretrained' / (candidate + '.pt')
        model = YOLO(str(pretrained))
        model.train(data=str(YOLO_DATA_YAML), epochs=YOLO_EPOCHS, imgsz=IMAGE_SIZE,
                batch=BATCH_SIZE, seed=SEED, deterministic=True,
                project=str(OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs'), name=candidate,
                exist_ok=False, device=DEVICE, workers=0, patience=10,
                mosaic=0.0, mixup=0.0, copy_paste=0.0, degrees=0.0,
                translate=0.0, scale=0.0, fliplr=0.0,
                hsv_h=0.0, hsv_s=0.0, hsv_v=0.0)
    run_dir = Path(model.trainer.save_dir)
    checkpoint = run_dir / 'weights/best.pt'
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    MODEL_PATHS[candidate] = str(checkpoint)
    TRAINING_HISTORY[candidate] = {'seconds': time.perf_counter() - started,
                                   'checkpoint_sha256': sha256(checkpoint),
                                   'history_csv': str(run_dir / 'results.csv')}
    (run_dir / 'complete.txt').write_text('Finished training; best.pt is selected by validation.\n', encoding='utf-8')
    print(candidate, TRAINING_HISTORY[candidate])
print('Discovered checkpoints:', MODEL_PATHS)
"""),
    md(r"""
### 3a. YOLO11n

Run this cell on its own to train or load YOLO11n. The checkpoint and epoch history are saved under `.runtime/`.
"""),
    code(r"""
if DATA_READY and RUN_TRAINING and RUN_YOLO11N:
    train_yolo('yolo11n')
else:
    print('YOLO11n training paused; checkpoint:', MODEL_PATHS.get('yolo11n'))
"""),
    md(r"""
### 3b. YOLO11s

Run this cell separately when ready. It uses the same split and hyperparameters as YOLO11n.
"""),
    code(r"""
if DATA_READY and RUN_TRAINING and RUN_YOLO11S:
    train_yolo('yolo11s')
else:
    print('YOLO11s training paused; checkpoint:', MODEL_PATHS.get('yolo11s'))
"""),
    md(r"""
### 3c. DETR

Run this cell separately when ready. Validation loss selects its checkpoint.
"""),
    code(r"""
if DATA_READY and RUN_TRAINING and RUN_DETR and 'detr-resnet-50' not in MODEL_PATHS:
    import torch
    from PIL import Image
    from transformers import DetrForObjectDetection, DetrImageProcessor

    processor = DetrImageProcessor.from_pretrained('facebook/detr-resnet-50')
    detr = DetrForObjectDetection.from_pretrained(
        'facebook/detr-resnet-50', num_labels=4,
        id2label=INDEX_TO_NAME, label2id={name: i for i, name in INDEX_TO_NAME.items()},
        ignore_mismatched_sizes=True).to(DEVICE)
    optimizer = torch.optim.AdamW(detr.parameters(), lr=1e-5, weight_decay=1e-4)

    def detr_item(row):
        with Image.open(row['path']) as opened:
            image = opened.convert('RGB')
        annotations = []
        for ann in row['annotations']:
            annotations.append({'id': ann['id'], 'image_id': row['image']['id'],
                                'category_id': COCO_TO_INDEX[ann['category_id']],
                                'bbox': ann['bbox'], 'area': ann['bbox'][2] * ann['bbox'][3], 'iscrowd': 0})
        item = processor(images=image,
                         annotations={'image_id': row['image']['id'], 'annotations': annotations},
                         size={'shortest_edge': IMAGE_SIZE, 'longest_edge': IMAGE_SIZE},
                         return_tensors='pt')
        return {'pixel_values': item['pixel_values'].to(DEVICE),
                'pixel_mask': item['pixel_mask'].to(DEVICE),
                'labels': [{k: v.to(DEVICE) for k, v in item['labels'][0].items()}]}

    best_loss, history = float('inf'), []
    detr_dir = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / 'runs/detr-resnet-50'
    if detr_dir.exists():
        raise FileExistsError(f'Existing DETR run: {detr_dir}; choose a new experiment directory.')
    started = time.perf_counter()
    for epoch in range(1, DETR_EPOCHS + 1):
        detr.train()
        train_losses = []
        for row in splits['train']['rows']:
            batch = detr_item(row)
            optimizer.zero_grad(set_to_none=True)
            loss = detr(**batch).loss
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))
        detr.eval()
        valid_losses = []
        with torch.inference_mode():
            for row in splits['valid']['rows']:
                valid_losses.append(float(detr(**detr_item(row)).loss.detach().cpu()))
        record = {'epoch': epoch, 'train_loss': statistics.mean(train_losses),
                  'valid_loss': statistics.mean(valid_losses)}
        history.append(record)
        print(record)
        if record['valid_loss'] < best_loss:
            best_loss = record['valid_loss']
            detr_dir.mkdir(parents=True, exist_ok=True)
            detr.save_pretrained(detr_dir)
            processor.save_pretrained(detr_dir)
    MODEL_PATHS['detr-resnet-50'] = str(detr_dir)
    TRAINING_HISTORY['detr-resnet-50'] = {'seconds': time.perf_counter() - started,
                                         'best_valid_loss': best_loss, 'epochs': history}
    (detr_dir / 'complete.txt').write_text('Finished DETR fine-tuning; checkpoint selected by validation loss.\n', encoding='utf-8')
else:
    print('DETR fine-tuning pending.')
"""),
    md(r"""
## 4. Common evaluation: all four classes, all splits, and negatives

Measure box mAP@0.50 and mAP@0.50:0.95 per class using the same COCO targets and TorchMetrics implementation for each selected candidate. Include zero-box images: predictions on them are false positives. Also report false positives per negative image at score ≥ 0.30, median/p95 end-to-end detector inference milliseconds per image, and sample count. Train metrics describe fit and are optimistic; validation is for selection; test is held out. `RUN_BENCHMARK=True` evaluates train+valid for `BENCHMARK_MODELS`, even if only one checkpoint exists. Each selection writes a separate JSON report. `RUN_FINAL_TEST=True` evaluates test after validation-based model and thresholds are frozen. The small historical YOLO report in `evaluation/reports/detection.json` is separate: it covers two field classes on 13 images from another dataset and cannot fill this table.
"""),
    code(r"""
BENCHMARK = {}
EXPECTED_MODELS = {'yolo11n', 'yolo11s', 'detr-resnet-50'}
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
                out = model.predict(bgr, imgsz=IMAGE_SIZE, conf=0.001,
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
                'by_class': by_class, 'false_positives_on_negatives_at_operating_conf': negative_fp,
                'median_inference_ms': float(np.median(latencies)),
                'p95_inference_ms': float(np.percentile(latencies, 95))}

    for name in BENCHMARK_MODELS:
        location = MODEL_PATHS[name]
        predict = make_predictor(name, location)
        BENCHMARK[name] = {'train': evaluate_split(predict, splits['train']['rows']),
                           'valid': evaluate_split(predict, splits['valid']['rows'])}
        if RUN_FINAL_TEST:
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
### Result and interpretation log

| Candidate | Train mAP50 / mAP50:95 | Valid mAP50 / mAP50:95 | Test mAP50 / mAP50:95 | EDS panel | Number | Route | Destination | Median / p95 ms | Negatives FP |
|---|---|---|---|---|---|---|---|---|---|
| YOLO11n | Pending | Pending | Held out | Pending | Pending | Pending | Pending | Pending | Pending |
| YOLO11s | Pending | Pending | Held out | Pending | Pending | Pending | Pending | Pending | Pending |
| DETR-ResNet50 | Pending | Pending | Held out | Pending | Pending | Pending | Pending | Pending | Pending |

**Findings to fill after the run:** Which class is weakest? Does the whole-panel box contain its fields? Are route and final destination confused? How many rear signs, unrelated text, blurred/distant displays or zero-box images produce false positives? Compare crop readability with OCR and inspect at least ten worst misses and ten false positives. Record validation threshold and NMS choices before opening test. A class with no reviewed ground truth in a split has undefined AP; do not report it as 0.
"""),
    code(r"""
if DATA_READY and BENCHMARK:
    import importlib.metadata as metadata
    report = {'dataset_root': str(DATASET_ROOT), 'dataset_manifest_sha256': DATA_FINGERPRINT,
              'inventory': inventory, 'class_map': {str(k): v for k, v in COCO_TO_INDEX.items()},
              'models': MODEL_PATHS, 'training_history': TRAINING_HISTORY,
              'benchmark': BENCHMARK, 'validation_threshold_sweep': THRESHOLD_SWEEP,
              'settings': {'yolo_epochs': YOLO_EPOCHS,
              'detr_epochs': DETR_EPOCHS, 'image_size': IMAGE_SIZE, 'batch_size': BATCH_SIZE,
              'seed': SEED, 'device': DEVICE, 'operating_conf': OPERATING_CONF,
              'yolo_nms_iou': YOLO_NMS_IOU, 'final_test_run': RUN_FINAL_TEST},
              'environment': {'platform': platform.platform(), 'python': sys.version,
              'torch': metadata.version('torch'), 'ultralytics': metadata.version('ultralytics'),
              'transformers': metadata.version('transformers'), 'torchmetrics': metadata.version('torchmetrics')}}
    suffix = '_'.join(BENCHMARK_MODELS)
    phase = 'test' if RUN_FINAL_TEST else 'validation'
    destination = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / f'benchmark_{suffix}_{phase}.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Evidence saved:', destination)
else:
    print('No measured benchmark report was written. The table remains pending.')
"""),
    md(r"""
## 6. YOLO loss research and how to apply it

The supplied slides illustrate three YOLO detection-loss parts. The pinned Ultralytics YOLO11 implementation uses **CIoU box loss**, **BCE classification loss**, and **distribution focal loss (DFL)** for the four box-edge distance distributions. In shorthand, `L = box_gain × L_CIoU + cls_gain × L_BCE + dfl_gain × L_DFL`; the trainer logs `train/box_loss`, `train/cls_loss`, `train/dfl_loss` and corresponding validation losses. CIoU accounts for overlap, centre distance and aspect ratio. DFL is a box-distance regression term, *not* the same as classification focal loss. The slide's BCE-to-focal arrow is an optional experiment, not the default YOLO11 loss. DETR has a different matching/classification/box objective, so do not compare raw loss values across architectures.

**Project application:** keep YOLO11 defaults for the controlled baseline and record all three curves. Inspect per-class AP and negative-image false positives first. If small EDS or route boxes remain poorly localized, change one documented parameter at a time (`box` or `dfl`) and compare validation mAP50:95 and crop quality. If a verified class imbalance causes route/destination mistakes, test `cls` gain and sampling before considering a separately implemented focal-loss ablation. Do not claim focal loss is active merely because DFL appears in the logs. Retain the same test split and class mapping across ablations.

Primary references: [Ultralytics detection loss source](https://docs.ultralytics.com/reference/utils/loss), [Ultralytics training settings](https://docs.ultralytics.com/modes/train), [CIoU paper](https://arxiv.org/abs/1911.08287), [Focal Loss paper](https://arxiv.org/abs/1708.02002), [Generalized Focal Loss paper](https://arxiv.org/abs/2006.04388), [DETR paper](https://arxiv.org/abs/2005.12872).

## 7. Outstanding task-allocation checklist

- [x] Obtain the labelled source, run the automated audit, and build a separate manifest-backed training export. The uploaded Roboflow export still lacks provenance; source permissions and capture groups remain to be documented.
- [ ] Review all four class definitions and negative examples with Jy; inspect route/destination ambiguity and missing boxes. Confirm source/recording groups do not cross splits.
- [ ] Fine-tune YOLO11n, YOLO11s and DETR on identical reviewed splits; save checkpoints, settings, versions and training curves.
- [ ] Validate all four classes, negatives and speed on target hardware; inspect small, distant, blurred, angled and occluded failures and OCR crop quality.
- [ ] Select model, confidence threshold and NMS setting using validation. Freeze settings, run held-out test once and record remaining limitations.
- [ ] Deliver selected detector checkpoint/configuration and label/box contract to the app/OCR team; verify multiple displays and camera/uploaded-video latency in the integrated system.

The historical 13-image field-detector report and sample gallery are useful references, but they do not replace this four-class, held-out evaluation.
"""),
]

notebook = {'nbformat': 4, 'nbformat_minor': 5, 'cells': cells, 'metadata': {
    'kernelspec': {'display_name': 'CVDL Detector (CUDA)', 'language': 'python', 'name': 'cvdl-detector'},
    'language_info': {'name': 'python'},
}}
for index, cell in enumerate(notebook['cells'], 1):
    cell['id'] = f'eds-detector-{index:02d}'
# Save the observed preflight status in notebook outputs. Run controls are false,
# so this cannot train, download weights, or publish benchmark figures.
state = {'__name__': '__main__'}
execution_count = 0
for cell in notebook['cells']:
    if cell['cell_type'] != 'code':
        continue
    execution_count += 1
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(cell['source'], cell['id'], 'exec'), state)
    cell['execution_count'] = execution_count
    if output.getvalue():
        cell['outputs'] = [{'output_type': 'stream', 'name': 'stdout',
                            'text': output.getvalue()}]
destination = Path(__file__).with_name('object_detection_benchmark.ipynb')
destination.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(destination)
