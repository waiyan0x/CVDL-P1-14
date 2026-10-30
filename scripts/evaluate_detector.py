"""Reproduce field-detection metrics on the deduplicated bundled test subset."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.evaluation.provenance import file_hash
from scripts.detection_dataset import prepare_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/reports/detection.json')
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    import torch
    import ultralytics
    from ultralytics import YOLO
    import yaml

    torch.set_num_threads(4)
    runtime = ROOT / '.runtime'
    runtime.mkdir(exist_ok=True)
    checkpoint = ROOT / 'models/yolo-v6-finetuned/best_v6.pt'
    settings = {'imgsz': 640, 'batch': 1, 'classes': [1, 2], 'conf': .001,
                'iou': .7, 'device': args.device, 'workers': 0, 'plots': False,
                'verbose': False, 'save': False, 'save_json': False, 'split': 'test'}
    with tempfile.TemporaryDirectory(prefix='detector-evaluation-', dir=runtime) as directory:
        staging = Path(directory)
        dataset = prepare_dataset(ROOT, staging)
        yaml_path = staging / 'data.yaml'
        yaml_path.write_text(yaml.safe_dump({'path': str(staging), 'train': 'images/test',
            'val': 'images/test', 'test': 'images/test',
            'names': {0: 'bus_front', 1: 'bus_number', 2: 'destination', 3: 'eds'}}))
        model = YOLO(str(checkpoint))
        processed = {}
        model.add_callback('on_val_end', lambda validator: processed.update(images=validator.seen))
        metrics = model.val(data=str(yaml_path), project=str(runtime / 'validation'),
                            name='field-detector', exist_ok=True, **settings)
        if processed.get('images') != dataset['image_count']:
            raise RuntimeError('The validator skipped evaluation images; no report was published. Check image/label diagnostics.')
        dataset['processed_images'] = processed['images']
    source = metrics.results_dict
    report = {'schema_version': 1, 'report_type': 'detection_benchmark',
        'run_id': 'field-detector-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'created_at': datetime.now(timezone.utc).isoformat(), 'dataset': dataset,
        'detector': {'path': str(checkpoint.relative_to(ROOT)), 'sha256': file_hash(checkpoint),
                     'architecture': 'YOLO11n', 'classes': [1, 2]},
        'protocol': {'settings': settings,
            'metrics': 'Ultralytics detection validation; AP over IoU 0.50:0.95.',
            'speed': 'Validator-reported mean milliseconds/image; not sustained application FPS.'},
        'hardware': {'platform': platform.platform(), 'machine': platform.machine(),
                     'processor': platform.processor(), 'torch_threads': 4,
                     'torch': torch.__version__, 'ultralytics': ultralytics.__version__},
        'metrics': {'precision': float(source['metrics/precision(B)']),
                    'recall': float(source['metrics/recall(B)']),
                    'map_50': float(source['metrics/mAP50(B)']),
                    'map_50_95': float(source['metrics/mAP50-95(B)']),
                    'whole_eds_map': None, 'speed_ms_per_image': metrics.speed},
        'limitations': [
            'Only service-number and destination classes [1,2] are evaluated; no whole-EDS accuracy claim.',
            'Exact training/test duplicates and unlabelled images excluded; near-duplicate and original training provenance are unverified.',
            'Small bundled image subset; does not establish performance on unseen video or other EDS formats.',
            'Original bundled detection annotations have not been independently reviewed.',
            'One .jpg contains AVIF data and is explicitly transcoded to JPEG for validator compatibility; original file is unchanged.',
            'OCR accuracy is not measured by this detector validation.'],
        'method_source': 'https://docs.ultralytics.com/modes/val/'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Wrote {args.output}: {dataset["image_count"]} labelled images.')


if __name__ == '__main__':
    main()
