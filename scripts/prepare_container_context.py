"""Stage only the EDS Reader application and its model assets for a container build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DETECTOR_CONFIG = Path(
    'evaluation/object_detection/01760a841333/runs/v4-reviewed-01/detector_config.json'
)
# Hash of the project's fine-tuned TrOCR LFS artifact in commit a5cead0.
TROCR_CHECKPOINT_SHA256 = '3783be7c23cd38e84cc2215ca678f63aae59af665e3b164f97c7bf1e07b10fe4'
APP_PATHS = (
    'backend/app', 'frontend', 'data/samples', 'data/bus_information.csv', 'data/reference',
    'models/paddleocr-finetuned', 'models/paddleocr-pretrained', 'evaluation/reports',
)
OCR_ASSETS = {
    '.cache/easyocr': ('craft_mlt_25k.pth', 'english_g2.pth'),
    '.cache/trocr': (
        'model.safetensors', 'config.json', 'generation_config.json', 'preprocessor_config.json',
        'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'merges.txt', 'vocab.json',
    ),
}


def verify_checkpoint(path, expected):
    with (ROOT / path).open('rb') as weights:
        if hashlib.file_digest(weights, 'sha256').hexdigest() != expected:
            raise ValueError(f'{path} does not match the recorded checkpoint hash.')


def prepare(destination):
    detector = json.loads((ROOT / DETECTOR_CONFIG).read_text(encoding='utf-8'))
    checkpoint = Path(detector['checkpoint_install_path'])
    verify_checkpoint(checkpoint, detector['checkpoint_sha256'])
    verify_checkpoint(Path('.cache/trocr/model.safetensors'), TROCR_CHECKPOINT_SHA256)

    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', *APP_PATHS], cwd=ROOT)
    sources = [Path(name) for name in tracked.decode().split('\0') if name]
    sources.extend((Path('Dockerfile'), Path('.dockerignore'), Path('requirements-app.txt'), DETECTOR_CONFIG, checkpoint))
    sources.extend(Path(folder) / name for folder, names in OCR_ASSETS.items() for name in names)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.eds-stage-', dir=destination.parent) as temporary:
        staged = Path(temporary) / 'context'
        for source in sources:
            target = staged / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, target)
        staged.rename(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='Path to a new directory for the build context')
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        parser.error('Choose a build context directory that does not exist.')
    try:
        prepare(destination)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Could not prepare container context: {error}\n')
    print(destination)


if __name__ == '__main__':
    main()
