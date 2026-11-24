"""Freeze 5,000 training line/image pairs, preserving real data and evaluation."""
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.runtime/ocr_finetune_bundle-20261119-synv2-candidate.zip'
OUTPUT = ROOT / '.runtime/ocr_finetune_bundle-20261120-5k.zip'
AUDIT = ROOT / 'evaluation/ocr_training/5k-20261120'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if OUTPUT.exists() or AUDIT.exists():
        raise SystemExit('Refusing to overwrite a frozen bundle or audit')
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        files = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    manifest = json.loads(files['bundle_manifest.json'])
    assert all(digest(files[n]) == h for n, h in manifest['payload_sha256'].items())
    assert manifest['test_used'] is False
    original = files['train.tsv'].decode().splitlines()
    real = [s for s in original if not Path(s.partition('\t')[0]).stem.startswith('SYN2-')]
    assert len(real) == 366
    entries = {r['review_id']: r for r in manifest['synthetic']['crops']}
    reviewed = {r['review_id'] for r in csv.DictReader(
        (ROOT/'evaluation/ocr_training/synthetic-v2-audit-20261119/synthetic_v2_human_spotcheck.csv').open())}
    assert len(reviewed) == 100 and reviewed <= entries.keys()
    selected = set()
    quotas = {'bus_number': 1854, 'destination': 1854, 'route_text': 926}
    rng = random.Random(0)
    for field, quota in quotas.items():
        fixed = sorted(rid for rid in reviewed if entries[rid]['field'] == field)
        selected.update(fixed)
        remaining = quota - sum(entries[rid]['lines'] for rid in fixed)
        candidates = sorted(rid for rid, r in entries.items() if r['field'] == field and rid not in reviewed)
        rng.shuffle(candidates)
        for rid in candidates:
            n = entries[rid]['lines']
            if n <= remaining:
                selected.add(rid)
                remaining -= n
            if remaining == 0:
                break
        assert remaining == 0, field
    kept = []
    for s in original:
        path = s.partition('\t')[0]
        rid = Path(path).stem.rsplit('_', 1)[0]
        if not Path(path).stem.startswith('SYN2-') or rid in selected:
            kept.append(s)
    assert len(kept) == 5000
    assert [s for s in kept if s in real] == real
    train_names = {s.partition('\t')[0] for s in kept}
    assert len(train_names) == 5000
    result = {n: b for n, b in files.items() if not n.startswith('lines/train/') or n in train_names}
    result['train.tsv'] = ('\n'.join(kept)+'\n').encode()
    result['charset.txt'] = ''.join(sorted(set(''.join(s.partition('\t')[2] for s in kept)))).encode()
    for name in ['joined.csv', 'skipped.csv']:
        reader = csv.DictReader(io.StringIO(files[name].decode()))
        columns = reader.fieldnames
        rows = [r for r in reader if not r['review_id'].startswith('SYN2-') or r['review_id'] in selected]
        buf = io.StringIO();w = csv.DictWriter(buf, columns, lineterminator='\n');w.writeheader();w.writerows(rows)
        result[name] = buf.getvalue().encode()
    manifest['counts'].update(train_pairs=5000, synthetic_pairs=4634, synthetic_crops_used=len(selected))
    manifest['synthetic']['crops'] = [r for r in manifest['synthetic']['crops'] if r['review_id'] in selected]
    for name in ['joined', 'skipped']:
        manifest[name] = [r for r in manifest[name] if not r['review_id'].startswith('SYN2-') or r['review_id'] in selected]
    selection = dict(seed=0, unit='exported training line-image/text pairs',
                     parent_bundle=SOURCE.name, parent_bundle_sha256=digest(SOURCE.read_bytes()),
                     real_pairs=366, synthetic_pairs=4634, total_pairs=5000,
                     synthetic_line_quotas=quotas, selected_synthetic_source_crops=len(selected),
                     original_real_source_crops=387, usable_real_source_crops=363,
                     reviewed_source_crops_retained=100,
                     policy='Whole synthetic crop groups retained; include all 100 user-reviewed sample crops, then seeded field-stratified fill. Validation/test policy unchanged.',
                     selected_review_ids=sorted(selected))
    manifest['selection_5k'] = selection
    manifest['payload_sha256'] = {n:digest(b) for n,b in result.items() if n != 'bundle_manifest.json'}
    result['bundle_manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    assert all(result[n] == files[n] for n in files if n.startswith('lines/valid/') or n in ['valid.tsv','valid_crops.jsonl','weights.lock.json'])
    assert not any('test' in Path(n).parts for n in result)
    with zipfile.ZipFile(OUTPUT,'x',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for n,b in sorted(result.items()):z.writestr(n,b)
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        assert all(digest(z.read(n)) == h for n,h in manifest['payload_sha256'].items())
    AUDIT.mkdir(parents=True)
    (AUDIT/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    (AUDIT/'bundle.lock.json').write_text(json.dumps(dict(bundle=OUTPUT.name,sha256=digest(OUTPUT.read_bytes()),
        counts=manifest['counts'],real_pairs_unchanged=True,validation_unchanged=True,test_data_absent=True,
        all_payload_hashes_verified=True,training_completed=False),indent=2)+'\n')
    print(json.dumps({'bundle':str(OUTPUT),'sha256':digest(OUTPUT.read_bytes()),'counts':manifest['counts']},indent=2))


if __name__ == '__main__':
    main()
