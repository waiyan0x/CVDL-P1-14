"""Export train/valid frozen-line inputs only; never discover or open TEST data."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import inspect
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
from PIL import Image
from backend.app.evaluation.ocr_line_layout import extract_region


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def pairing(text, count):
    """Return line labels, or an explicit reason; preserve literal text otherwise."""
    labels = text.split('\n')
    if count == 0:
        return None, 'no_frozen_regions'
    if count == len(labels):
        return labels, None
    if count == 1 and len(labels) == 2:
        return [' '.join(labels)], 'two_text_lines_joined_for_one_region'
    return None, 'region_text_count_mismatch'


def build(output, root=ROOT, training=None, valid_manifest=None):
    root = Path(root).resolve()
    output = Path(output)
    if output.exists():
        raise FileExistsError('Refusing existing output: ' + str(output))
    packet = root/'.runtime/ocr-task-files-20261116'
    training = training or root/'evaluation/ocr_training/train_labels_final.csv'
    valid_manifest = valid_manifest or root/'evaluation/ocr_scoring/normalised-v4-valid-human-corrected/manifest.json'
    inputs = [Path(training), Path(valid_manifest), packet/'labels/training.source.csv',
              packet/'labels/validation_labels.proposals.csv',
              packet/'layouts/training_existing/manifest.json',
              root/'evaluation/ocr_layouts/v4-lines-v1/manifest.json',
              packet/'weights/models.lock.json']
    before = {str(p.relative_to(root)):sha(p) for p in inputs}
    train = csv_rows(training)
    if len(train) != 387:
        raise ValueError(f'Expected 387 training labels, got {len(train)}; review changed inputs')
    original = csv_rows(inputs[2])
    if any(r['split'] != 'train' for r in original):
        raise ValueError('Training metadata contains another split')
    names = [Path(r['crop']).name for r in original]
    if len(names) != len(set(names)):
        raise ValueError('Ambiguous training crop basename')
    index = dict(zip(names, original))
    groups = defaultdict(list)
    for row in train:
        source = index[Path(row['crop']).name]
        groups[row['source_name'], source['label']].append(row)
    if len(groups) != 129 or any(len(g) != 3 or len({r['text'] for r in g}) != 1 for g in groups.values()):
        raise ValueError('Training triplet identity/consensus changed')
    manifest = json.loads(Path(valid_manifest).read_text())
    if any(r['split'] != 'valid' for r in manifest['rows']):
        raise ValueError('Validation manifest contains another split')
    valid = [r for r in manifest['rows'] if r['scoring_eligible'] is True]
    mapping = {r['review_id']:r for r in csv_rows(inputs[3])}
    layouts = {}
    for split, path in [('train',inputs[4]), ('valid',inputs[5])]:
        hash_file = path.with_suffix('.sha256')
        if sha(path) != hash_file.read_text().split()[0]:
            raise ValueError('Layout hash mismatch: ' + str(path))
        before[str(hash_file.relative_to(root))] = sha(hash_file)
        content = json.loads(path.read_text())
        if not content.get('frozen'):
            raise ValueError('Layout is not frozen')
        layouts[split] = {r['review_id']:r for r in content['entries']}
        if len(layouts[split]) != len(content['entries']):
            raise ValueError('Duplicate layout IDs')
    prepared = []
    for row in train:
        source = index[Path(row['crop']).name]
        path = (root/row['crop']).resolve()
        permitted = (root/'.cache/ocr_training/v4-reviewed-01-ai-01/source').resolve()
        if not path.is_relative_to(permitted):
            raise ValueError('Training path outside the explicit training source')
        prepared.append(dict(review_id=source['review_id'], split='train', input_set='annotation',
                             field=row['field'], reference=row['text'], crop_path=path,
                             crop_sha256=source['crop_sha256'], group=[row['source_name'],source['label']]))
    for row in valid:
        path = (packet/mapping[row['review_id']]['crop']).resolve()
        if not path.is_relative_to((packet/'crops/valid').resolve()):
            raise ValueError('Validation path outside the explicit valid root')
        prepared.append(dict(review_id=row['review_id'], split='valid', input_set=row['crop_source'],
                             field=row['label'], reference=row['transcription'], crop_path=path,
                             crop_sha256=row['crop_sha256']))
    if len({r['review_id'] for r in prepared}) != len(prepared):
        raise ValueError('Duplicate crop IDs')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Open exclusively and clean only this newly created file on failure.
    counts = Counter(); skipped = []; joins = []; valid_crops = []; train_pairs = []; valid_pairs = []
    val_pixels = {}; payload = {}; crop_evidence = []
    stream=output.open('xb')
    try:
        with stream, zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            def put(name, data):
                if isinstance(data,str):data=data.encode('utf-8')
                z.writestr(name,data);payload[name]=hashlib.sha256(data).hexdigest()
            for row in prepared:
                split,rid,text = row['split'],row['review_id'],row['reference']
                if '\r' in text or '\t' in text:
                    raise ValueError('TSV-unsafe raw label character: '+rid)
                entry = layouts[split][rid]
                if sha(row['crop_path']) != row['crop_sha256'] or entry['crop_sha256'] != row['crop_sha256']:
                    raise ValueError('Crop hash mismatch: '+rid)
                with Image.open(row['crop_path']) as im:
                    rgb = np.asarray(im.convert('RGB'))
                if (rgb.shape[1],rgb.shape[0]) != (entry['input_width'],entry['input_height']):
                    raise ValueError('Crop geometry mismatch: '+rid)
                gray = cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
                quads = entry['line_quads']
                if entry['review_status'] != 'accepted' and quads:
                    raise ValueError('Unresolved layout has regions: '+rid)
                labels,reason = pairing(text,len(quads))
                if labels is None:
                    skipped.append(dict(review_id=rid,split=split,reason=reason))
                elif reason:
                    joins.append(dict(review_id=rid,split=split,reason=reason))
                # Skip train pairs exactly as requested. Retain validation
                # regions without line labels for full crop-level inference.
                paths = []
                if labels is not None or split == 'valid':
                    for i,quad in enumerate(quads):
                        line = extract_region(gray,quad)
                        name = f'lines/{split}/{rid}_{i:02d}.png'
                        buf = io.BytesIO();Image.fromarray(line).save(buf,format='PNG');put(name,buf.getvalue())
                        paths.append(name);counts[split+'_images']+=1
                        if labels is not None:
                            (train_pairs if split=='train' else valid_pairs).append((name,labels[i]))
                        if split == 'valid':val_pixels[name]=(line.shape,hashlib.sha256(line.tobytes()).hexdigest())
                if split == 'valid':
                    valid_crops.append(dict(review_id=rid,input_set=row['input_set'],field=row['field'],
                                            reference=text,lines=paths,line_pair_status=reason or 'aligned'))
                crop_evidence.append(dict(review_id=rid,split=split,sha256=row['crop_sha256'],
                                          group=row.get('group')))
            charset = ''.join(sorted(set(''.join(t for _,t in train_pairs))))
            put('charset.txt',charset)  # Literal characters; no extra trailing newline.
            put('weights.lock.json', inputs[6].read_bytes())
            for split,pairs in [('train',train_pairs),('valid',valid_pairs)]:
                put(split+'.tsv',''.join(p+'\t'+t+'\n' for p,t in pairs))
            put('valid_crops.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in valid_crops))
            for name,rows in [('skipped.csv',skipped),('joined.csv',joins)]:
                buf=io.StringIO();w=csv.DictWriter(buf,['review_id','split','reason'],lineterminator='\n')
                w.writeheader();w.writerows(rows);put(name,buf.getvalue())
            # Pixel-array equality, as the runner feeds arrays rather than PNG streams.
            selected=random.Random(0).sample([r for r in valid_crops if r['lines']],5)
            equivalence=[]
            for crop in selected:
                raw=next(r for r in prepared if r['review_id']==crop['review_id'])
                with Image.open(raw['crop_path']) as im:gray=cv2.cvtColor(np.asarray(im.convert('RGB')),cv2.COLOR_RGB2GRAY)
                for i,name in enumerate(crop['lines']):
                    expected=extract_region(gray,layouts['valid'][crop['review_id']]['line_quads'][i])
                    # Decode saved PNG from the exact encoded payload recorded above.
                    # PIL's encoding is lossless; explicit readback runs after ZIP close.
                    equivalence.append(dict(review_id=crop['review_id'],line=name,shape=list(expected.shape),
                                            pixel_sha256=hashlib.sha256(expected.tobytes()).hexdigest()))
            after={name:sha(root/name) for name in before}
            if before != after:raise ValueError('An input changed during export')
            result=dict(schema_version=1,git_commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
                        input_sha256=before,source_crops=crop_evidence,counts=dict(train_crops=len(train),train_groups=len(groups),
                        train_pairs=len(train_pairs),valid_crops=len(valid_crops),valid_pairs=len(valid_pairs),
                        valid_images=counts['valid_images'],test_files=0),
                        skipped=skipped,joined=joins,payload_sha256=payload,
                        extraction_method='PIL RGB -> cv2 RGB2GRAY -> imported extract_region -> grayscale PNG',
                        extract_region_source_sha256=hashlib.sha256(inspect.getsource(extract_region).encode()).hexdigest(),
                        equivalence_seed=0,equivalence_checks=equivalence,
                        assumptions=['All eligible validation crops retained; missing regions predict empty strings.',
                                     'Validation mismatched line labels skip line pairs only; native regions retained for crop inference.',
                                     'No train/valid resplit; augmented copies remain in their original train group.',
                                     'Pixel-array bytes are compared, not compressed PNG bytes.'],test_used=False)
            put('bundle_manifest.json',json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        with zipfile.ZipFile(output) as z:
            if z.testzip():raise ValueError('ZIP CRC failed')
            for check in result['equivalence_checks']:
                with Image.open(io.BytesIO(z.read(check['line']))) as im:a=np.asarray(im)
                if list(a.shape)!=check['shape'] or hashlib.sha256(a.tobytes()).hexdigest()!=check['pixel_sha256']:
                    raise ValueError('Pixel equivalence check failed')
        return result
    except BaseException:
        output.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'.runtime/ocr_finetune_bundle.zip')
    a=p.parse_args();r=build(a.output);print(json.dumps(dict(output=str(a.output),counts=r['counts'],
                                         skipped=len(r['skipped']),joined=len(r['joined'])),indent=2))
