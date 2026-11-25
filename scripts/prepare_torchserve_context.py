"""Verify and package the reviewed YOLO checkpoint for a TorchServe rollout."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from prepare_container_context import DETECTOR_CONFIG, ROOT, verify_checkpoint


def prepare(destination, archiver):
    contract = json.loads((ROOT / DETECTOR_CONFIG).read_text(encoding='utf-8'))
    checkpoint = Path(contract['checkpoint_install_path'])
    verify_checkpoint(checkpoint, contract['checkpoint_sha256'])
    destination.mkdir(parents=True, exist_ok=False)

    source = ROOT / 'deploy/torchserve'
    for filename in ('Dockerfile', 'config.properties'):
        shutil.copy2(source / filename, destination / filename)
    subprocess.run([
        archiver, '--model-name', 'eds-detector', '--version', '1.0',
        '--serialized-file', str(ROOT / checkpoint),
        '--handler', str(source / 'eds_handler.py'),
        '--extra-files', str(ROOT / 'backend/app/services/detection.py'),
        '--export-path', str(destination),
    ], check=True)

    shutil.copytree(ROOT / 'backend/app', destination / 'backend/app',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--archiver', default='torch-model-archiver')
    args = parser.parse_args()
    prepare(args.destination.resolve(), args.archiver)


if __name__ == '__main__':
    main()
