"""Install the fine-tuned TrOCR model into the app's local cache (.cache/trocr), so the "trocr" engine is available.

The weights (~1.3 GB) are too large for Git. Download the round 1 model folder from the team Drive,
DRIVE/CVDL-OCR-finetune/trocr/20261117-031848/ (or just its best/ folder), then run:

    .venv/bin/python scripts/install_trocr.py --from ~/Downloads/20261117-031848-....zip
    .venv/bin/python scripts/install_trocr.py --from ~/Downloads/20261117-031848/best

--from accepts the Drive zip download or an unzipped folder; the folder holding model.safetensors is found inside.
The files are checked (the Hugging Face files the app loads, a TrOCR vision-encoder-decoder config, and a
full-size model.safetensors), copied into the cache, loaded once and run on a blank crop. Each installed file's
SHA-256 is written to .cache/trocr/installed.json. Restart the app afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Files TrOCRProcessor / VisionEncoderDecoderModel.from_pretrained read in backend/app/services/ocr/trocr.py.
REQUIRED = ('config.json', 'generation_config.json', 'model.safetensors', 'preprocessor_config.json',
            'special_tokens_map.json', 'tokenizer_config.json', 'vocab.json', 'merges.txt')
OPTIONAL = ('tokenizer.json', 'added_tokens.json', 'provenance.json')
MIN_WEIGHTS = 1_000_000_000  # trocr-base is ~1.3 GB; a smaller file is a Git LFS pointer or an incomplete download


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def model_folder(root):
    found = sorted({p.parent for p in root.rglob('model.safetensors')}, key=lambda p: ('best' not in p.parts, len(p.parts)))
    if not found:
        raise SystemExit(f'No model.safetensors under {root}. Download the TrOCR run folder (with best/) from Drive.')
    return found[0]


def check(folder):
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        raise SystemExit(f'{folder} is missing {", ".join(missing)}; download the complete best/ folder.')
    size = (folder / 'model.safetensors').stat().st_size
    if size < MIN_WEIGHTS:
        raise SystemExit(f'model.safetensors is only {size:,} bytes: a Git LFS pointer or an incomplete download.')
    config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
    if config.get('model_type') != 'vision-encoder-decoder':
        raise SystemExit(f"config.json is a {config.get('model_type')!r} model, not TrOCR (vision-encoder-decoder).")


def smoke_test(cache):
    import numpy as np
    from backend.app.services.ocr.trocr import TrOCRAdapter

    class Settings:
        trocr_dir = cache
    started = time.perf_counter()
    text, confidence = TrOCRAdapter(Settings()).read(np.full((48, 160, 3), 255, np.uint8), 'bus_number')
    print(f'Loaded and ran TrOCR in {time.perf_counter() - started:.1f} s (blank crop read as {text!r}).')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--from', dest='source', type=Path, required=True, help='Drive zip or folder with best/')
    parser.add_argument('--cache', type=Path, default=None, help='install folder (default: the app setting, .cache/trocr)')
    args = parser.parse_args()
    from backend.app.config import Settings
    cache = (args.cache or Settings.from_env().trocr_dir).resolve()
    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f'{source} does not exist.')

    with tempfile.TemporaryDirectory(dir=cache.parent if cache.parent.exists() else None) as temporary:
        if source.is_file():
            if not zipfile.is_zipfile(source):
                raise SystemExit(f'{source} is not a zip or a folder.')
            print(f'Extracting {source.name} ...', flush=True)
            with zipfile.ZipFile(source) as archive:
                target = Path(temporary).resolve()
                for entry in archive.infolist():
                    if not (target / entry.filename).resolve().is_relative_to(target):
                        raise SystemExit('Unsafe path in zip: ' + entry.filename)
                archive.extractall(target)
            source = target
        folder = model_folder(source)
        check(folder)
        staging = cache.with_name(cache.name + '.installing')
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        names = [n for n in REQUIRED + OPTIONAL if (folder / n).is_file()]
        for name in names:
            print(f'Copying {name} ...', flush=True)
            shutil.copy2(folder / name, staging / name)
        record = {'installed': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'source': args.source.name,
                  'files_sha256': {name: sha256(staging / name) for name in names}}
        (staging / 'installed.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        if cache.exists():
            shutil.rmtree(cache)
        staging.replace(cache)
    smoke_test(cache)
    print(f"Installed TrOCR in {cache} (model.safetensors SHA-256 {record['files_sha256']['model.safetensors'][:12]}...). "
          'Restart the app; "trocr" now appears in /api/health backends.')


if __name__ == '__main__':
    main()
