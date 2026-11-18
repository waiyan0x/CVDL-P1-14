"""Import round 2 (synthetic-bundle) best/ ZIPs into .cache/finetuned-syn/<model>/.

Drive downloads arrive as best-<timestamp>.zip; the model is identified from
its files (inference.pdiparams -> paddleocr, eds_english_g2.pth -> easyocr,
model.safetensors -> trocr). Files are extracted flat, never over an existing
folder, and hashed into .cache/finetuned-syn/import_manifest.json, mirroring
the round 1 import in .cache/finetuned/.

Usage: python3 scripts/import_synthetic_finetuned.py RUN_ID ZIP [ZIP ...]
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.cache/finetuned-syn'
MARKERS = {'inference.pdiparams': 'paddleocr', 'eds_english_g2.pth': 'easyocr', 'model.safetensors': 'trocr'}
REQUIRED = {'paddleocr': {'inference.json', 'inference.pdiparams', 'inference.yml'},
            'easyocr': {'eds_english_g2.pth', 'eds_english_g2.yaml', 'eds_english_g2.py'},
            'trocr': {'model.safetensors', 'config.json', 'preprocessor_config.json', 'vocab.json', 'merges.txt'}}


def main(run_id, *archives):
    manifest_path = DEST / 'import_manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for archive in map(Path, archives):
        with zipfile.ZipFile(archive) as z:
            if z.testzip():
                raise SystemExit(f'CRC failure: {archive}')
            files = {Path(n).name: n for n in z.namelist() if not n.endswith('/') and '__MACOSX' not in n}
            models = {MARKERS[f] for f in files if f in MARKERS}
            if len(models) != 1:
                raise SystemExit(f'{archive.name}: cannot identify one model from {sorted(files)}')
            model = models.pop()
            missing = REQUIRED[model] - set(files)
            if missing:
                raise SystemExit(f'{archive.name} ({model}) is missing {sorted(missing)}')
            target = DEST / model
            if target.exists():
                raise SystemExit(f'Refusing to overwrite {target}')
            target.mkdir(parents=True)
            hashes = {}
            for name, member in sorted(files.items()):
                data = z.read(member)
                (target / name).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
        provenance = target / 'provenance.json'
        if provenance.exists() and run_id not in provenance.read_text():
            print(f'WARNING: {model} provenance.json does not mention run {run_id}; check the ZIP is from that run')
        manifest[model] = dict(archive=str(archive), run_id=run_id,
                               source_drive_folder=f'DRIVE/CVDL-OCR-finetune/{model}/{run_id}/best',
                               training_bundle='ocr_finetune_bundle-20261117-syn.zip', files_sha256=hashes)
        print(f'Imported {model} -> {target} ({len(hashes)} files)')
    manifest_path.write_text(json.dumps(manifest, indent=1) + '\n')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
