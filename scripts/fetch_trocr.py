"""Hydrate the supplied private-repository LFS checkpoint into an ignored cache."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'models/trocr-finetuned'
metadata = dict(line.split(' ', 1) for line in (source / 'model.safetensors').read_text().splitlines())
oid = metadata['oid'].split(':', 1)[1]
size = int(metadata['size'])
cache = ROOT / '.cache/trocr'
cache.mkdir(parents=True, exist_ok=True)
output = cache / 'model.safetensors'
if output.exists() and output.stat().st_size == size:
    print('TrOCR checkpoint already cached.')
else:
    # Credentials stay in process memory and are never printed or written to disk.
    token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=True).stdout.strip()
    response = requests.post('https://github.com/waiyan0x/CVDL-P1-14.git/info/lfs/objects/batch',
        auth=('x-access-token', token), headers={'Accept': 'application/vnd.git-lfs+json'},
        json={'operation': 'download', 'transfers': ['basic'], 'objects': [{'oid': oid, 'size': size}]}, timeout=30)
    response.raise_for_status()
    obj = response.json()['objects'][0]
    if 'error' in obj:
        raise RuntimeError('LFS download unavailable: ' + obj['error']['message'])
    action = obj['actions']['download']
    downloaded = 0
    digest = hashlib.sha256()
    part = output.with_suffix('.part')
    with requests.get(action['href'], headers=action.get('header', {}), stream=True, timeout=(30, 60)) as data:
        data.raise_for_status()
        with part.open('wb') as stream:
            last_report = 0
            for chunk in data.iter_content(1024 * 1024):
                stream.write(chunk); digest.update(chunk); downloaded += len(chunk)
                if downloaded - last_report >= 128 * 1024 * 1024:
                    print(f'TrOCR download: {downloaded / size:.0%}', flush=True); last_report = downloaded
    if downloaded != size or digest.hexdigest() != oid:
        part.unlink(missing_ok=True)
        raise RuntimeError('Checkpoint integrity check failed.')
    part.replace(output)
    print('TrOCR weights downloaded and SHA-256 verified.')
for config in source.glob('*.json'):
    shutil.copy2(config, cache / config.name)
for filename in ['merges.txt', 'vocab.json']:
    shutil.copy2(source / filename, cache / filename)
