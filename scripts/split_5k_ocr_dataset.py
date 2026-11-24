"""Freeze a text/source-group-disjoint 4,000/500/500 split of the 5k pairs."""
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import unicodedata
import zipfile
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'.runtime/ocr_finetune_bundle-20261120-5k.zip'
TRAIN = ROOT/'.runtime/ocr_dataset-20261120-5k-train-valid.zip'
TEST = ROOT/'.runtime/ocr_dataset-20261120-5k-test.zip'
OUT = ROOT/'evaluation/ocr_dataset/5k-split-20261120'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_key(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def subset(groups, available, target, rng):
    order = sorted(available)
    rng.shuffle(order)
    dp = [None]*(target+1)
    dp[0] = 0
    for i in order:
        weight = len(groups[i])
        for size in range(target, weight-1, -1):
            if dp[size] is None and dp[size-weight] is not None:
                dp[size] = dp[size-weight] | (1 << i)
    if dp[target] is None:
        return None
    return {i for i in order if dp[target] & (1 << i)}


def csv_bytes(rows, columns):
    buf = io.StringIO()
    w = csv.DictWriter(buf, columns, lineterminator='\n')
    w.writeheader();w.writerows(rows)
    return buf.getvalue().encode()


def main():
    if OUT.exists() or TRAIN.exists() or TEST.exists():
        raise SystemExit('Refusing to overwrite a frozen split')
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        files = {n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    old = json.loads(files['bundle_manifest.json'])
    assert all(sha(files[n]) == h for n,h in old['payload_sha256'].items())
    pairs = [s.split('\t',1) for s in files['train.tsv'].decode().splitlines()]
    assert len(pairs) == 5000
    real = {r['review_id']:r for r in old['source_crops'] if r['split']=='train'}
    synthetic = {r['review_id']:r for r in old['synthetic']['crops']}
    original_labels = {r['review_id']:r for r in csv.DictReader((ROOT/'evaluation/ocr_dataset/labels.csv').open())}
    rows = []
    for path,text in pairs:
        rid = Path(path).stem.rsplit('_',1)[0]
        origin = 'rendered' if rid in synthetic else 'original_real'
        rows.append(dict(example_id=Path(path).stem,source_crop_id=rid,source_path=path,
                         field=synthetic[rid]['field'] if rid in synthetic else original_labels[rid]['field'],
                         origin=origin,text=text,image_sha256=sha(files[path]),
                         source_photo=real[rid]['group'][0] if rid in real else ''))
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]];i = parent[i]
        return i
    def union(i,j):
        parent[find(j)] = find(i)
    seen = {}
    for i,r in enumerate(rows):
        keys = [('text',text_key(r['text'])),('crop',r['source_crop_id']),('pixels',r['image_sha256'])]
        if r['source_photo']:
            keys.append(('photo',r['source_photo']))
        for key in keys:
            if key in seen:union(i,seen[key])
            else:seen[key] = i
    grouped = defaultdict(list)
    for i in range(len(rows)):grouped[find(i)].append(i)
    groups = sorted(grouped.values(),key=lambda g:min(rows[i]['example_id'] for i in g))
    all_groups = set(range(len(groups)))
    targets = Counter(r['field'] for r in rows)
    best = None
    rng = random.Random(0)
    for attempt in range(100):
        valid = subset(groups,all_groups,500,rng)
        if valid is None:continue
        test = subset(groups,all_groups-valid,500,rng)
        if test is None:continue
        score = 0
        for chosen in [valid,test]:
            counts = Counter(rows[i]['field'] for g in chosen for i in groups[g])
            if any(counts[f] == 0 for f in targets):score += 1000000
            score += sum((counts[f]-targets[f]*.1)**2 for f in targets)
        candidate = (score,attempt,valid,test)
        if best is None or candidate[0] < best[0]:best = candidate
    if best is None or best[0] >= 1000000:
        raise ValueError('Cannot make exact held-out splits with every field represented')
    _,attempt,valid,test = best
    for gid,group in enumerate(groups):
        split = 'valid' if gid in valid else 'test' if gid in test else 'train'
        for i in group:
            rows[i].update(split=split,group_id=f'G{gid:04d}',image=f'lines/{split}/{rows[i]["example_id"]}.png')
    assert Counter(r['split'] for r in rows) == {'train':4000,'valid':500,'test':500}
    for column in ['source_crop_id','image_sha256','source_photo','group_id']:
        mapping = defaultdict(set)
        for r in rows:
            if r[column]:mapping[r[column]].add(r['split'])
        assert all(len(v)==1 for v in mapping.values()),column
    text_splits = defaultdict(set)
    for r in rows:text_splits[text_key(r['text'])].add(r['split'])
    assert all(len(v)==1 for v in text_splits.values())
    stats = {s:{'pairs':sum(r['split']==s for r in rows),
                'fields':dict(Counter(r['field'] for r in rows if r['split']==s)),
                'origins':dict(Counter(r['origin'] for r in rows if r['split']==s))} for s in ['train','valid','test']}
    OUT.mkdir(parents=True)
    columns = list(rows[0])
    (OUT/'labels.csv').write_bytes(csv_bytes(rows,columns))
    for s in ['train','valid','test']:(OUT/f'{s}_labels.csv').write_bytes(csv_bytes([r for r in rows if r['split']==s],columns))
    policy = dict(seed=0,search_attempt_selected=attempt,unit='exported line-image/text pairs',
                  ratios={'train':.8,'valid':.1,'test':.1},counts=stats,connected_groups=len(groups),
                  grouping=['normalised exact line text','original source crop','original real source photo','identical PNG SHA-256'],
                  pairwise_group_and_text_overlap=0,parent_bundle=SOURCE.name,parent_sha256=sha(SOURCE.read_bytes()),
                  old_real_validation_replaced=True,old_validation_images_in_new_training_bundle=False,
                  earlier_finetuned_models_not_independent_on_new_test=True,
                  source_glyph_family_and_template_independence_not_established=True)
    (OUT/'split_manifest.json').write_text(json.dumps(policy,indent=2)+'\n')
    for archive,splits in [(TRAIN,{'train','valid'}),(TEST,{'test'})]:
        payload = {r['image']:files[r['source_path']] for r in rows if r['split'] in splits}
        for split in sorted(splits):
            subset_rows = [r for r in rows if r['split']==split]
            payload[split+'.tsv'] = ''.join(r['image']+'\t'+r['text']+'\n' for r in subset_rows).encode()
            payload[split+'_crops.jsonl'] = ''.join(json.dumps(dict(review_id=r['example_id'],
                input_set=r['origin'],field=r['field'],reference=r['text'],lines=[r['image']],
                source_crop_id=r['source_crop_id'],group_id=r['group_id']))+'\n' for r in subset_rows).encode()
        if archive == TRAIN:
            payload['weights.lock.json'] = files['weights.lock.json']
            payload['charset.txt'] = ''.join(sorted(set(''.join(r['text'] for r in rows if r['split']=='train')))).encode()
        m = dict(schema_version=1,counts=dict(train_pairs=4000 if archive==TRAIN else 0,
                 valid_crops=500 if archive==TRAIN else 0,valid_pairs=500 if archive==TRAIN else 0,
                 valid_images=500 if archive==TRAIN else 0,test_files=0 if archive==TRAIN else 500),
                 test_used=archive==TEST,purpose='training_validation_only' if archive==TRAIN else 'held_out_evaluation_only',
                 split_manifest_sha256=sha((OUT/'split_manifest.json').read_bytes()),
                 parent_sha256=policy['parent_sha256'],payload_sha256={n:sha(b) for n,b in payload.items()})
        payload['bundle_manifest.json'] = (json.dumps(m,indent=2)+'\n').encode()
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in sorted(payload.items()):z.writestr(n,b)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(sha(z.read(n))==h for n,h in m['payload_sha256'].items())
    policy['archives'] = {p.name:sha(p.read_bytes()) for p in [TRAIN,TEST]}
    (OUT/'archives.lock.json').write_text(json.dumps(policy['archives'],indent=2)+'\n')
    print(json.dumps(policy,indent=2))


if __name__ == '__main__':
    main()
