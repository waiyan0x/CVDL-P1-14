"""Add synthetic EDS crops to an existing fine-tuning bundle (train split only).

Each synthetic crop is cut into lines with the same frozen automatic method the
test runs use (segment_lines -> line_quads -> extract_region, grayscale), then
paired with its ground-truth text from the synthetic labels.csv using the
bundle's own pairing rule. Crops whose region count does not match the text's
line count are skipped and logged in skipped.csv; nothing is guessed.

The source bundle is verified against its own payload hashes and copied
unchanged except train.tsv, charset.txt, skipped.csv, joined.csv and
bundle_manifest.json. Validation members are untouched; no test data is read.

Usage: python3 scripts/add_synthetic_to_bundle.py [--bundle ZIP] [--synthetic DIR] [--output ZIP] [--limit N]
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from backend.app.evaluation.ocr_crop_baseline import segment_lines  # noqa: E402
from backend.app.evaluation.ocr_line_layout import AUTOMATIC_METHOD, extract_region, line_quads  # noqa: E402
from export_ocr_finetune_bundle import pairing  # noqa: E402

CHANGED = ('train.tsv', 'charset.txt', 'skipped.csv', 'joined.csv', 'bundle_manifest.json')


PADDLE_CTC_STEPS = 40  # must match ctc_steps in colab/ocr_finetune/train_paddle.py


def ctc_need(text):
    return len(text) + sum(x == y for x, y in zip(text, text[1:]))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--bundle', type=Path, default=ROOT / '.runtime/ocr_finetune_bundle-20261117.zip')
    ap.add_argument('--synthetic', type=Path, default=ROOT / '.runtime/synthetic-eds-20261117')
    ap.add_argument('--output', type=Path, default=ROOT / '.runtime/ocr_finetune_bundle-20261118-syn.zip')
    ap.add_argument('--limit', type=int, help='Use at most N synthetic crops (seeded sample); default all')
    a = ap.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)

    with zipfile.ZipFile(a.bundle) as z:
        members = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(members['bundle_manifest.json'])
    for name, h in manifest['payload_sha256'].items():
        if digest(members[name]) != h:
            raise ValueError('Source bundle hash mismatch: ' + name)
    if manifest['test_used'] is not False or any(n.startswith('lines/test/') for n in members):
        raise ValueError('Source bundle must not contain test data')

    labels_path = a.synthetic / 'labels.csv'
    rows = list(csv.DictReader(open(labels_path, encoding='utf-8')))
    if any(r['split'] != 'train' or r['input_set'] != 'synthetic' or r['scoring_eligible'] != 'False' for r in rows):
        raise ValueError('Synthetic labels must be train/synthetic/not scoring-eligible')
    if a.limit:
        rows = sorted(random.Random(0).sample(rows, min(a.limit, len(rows))), key=lambda r: r['review_id'])

    new, pairs, skipped, joined, evidence = {}, [], [], [], []
    for r in rows:
        rid, text = r['review_id'], r['text']
        path = a.synthetic / r['crop']
        raw = path.read_bytes()
        if digest(raw) != r['crop_sha256']:
            raise ValueError('Synthetic crop hash mismatch: ' + rid)
        if '\t' in text or '\r' in text:
            raise ValueError('TSV-unsafe label: ' + rid)
        with Image.open(io.BytesIO(raw)) as im:
            rgb = np.asarray(im.convert('RGB'))
        _, regions, info = segment_lines(rgb)
        h, w = rgb.shape[:2]
        separators = [[box[3], box[3]] for box in regions[:-1]]
        quads = line_quads(w, h, separators) if regions else []
        labels, reason = pairing(text, len(quads))
        if labels is None:
            skipped.append(dict(review_id=rid, split='train', reason=reason))
            continue
        too_long = [t for t in labels if ctc_need(t) > PADDLE_CTC_STEPS]
        if too_long:  # train_paddle.py refuses labels the 48x320 CTC head cannot emit
            skipped.append(dict(review_id=rid, split='train',
                                reason=f'label needs {max(map(ctc_need, too_long))} CTC steps > {PADDLE_CTC_STEPS}'))
            continue
        if reason:
            joined.append(dict(review_id=rid, split='train', reason=reason))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        for i, quad in enumerate(quads):
            buf = io.BytesIO()
            Image.fromarray(extract_region(gray, quad)).save(buf, format='PNG')
            name = f'lines/train/{rid}_{i:02d}.png'
            new[name] = buf.getvalue()
            pairs.append((name, labels[i]))
        evidence.append(dict(review_id=rid, split='train', sha256=r['crop_sha256'], field=r['field'],
                             origin=r['source_name'], lines=len(quads), segmentation=info.get('status')))

    for name in new:
        if name in members:
            raise ValueError('Name collision with existing bundle member: ' + name)
    train_tsv = members['train.tsv'].decode('utf-8') + ''.join(f'{p}\t{t}\n' for p, t in pairs)
    all_text = ''.join(line.partition('\t')[2] for line in train_tsv.splitlines())
    charset = ''.join(sorted(set(all_text)))
    old_charset = members['charset.txt'].decode('utf-8')

    def merged_csv(name, extra):
        old = list(csv.DictReader(io.StringIO(members[name].decode('utf-8'))))
        buf = io.StringIO()
        w = csv.DictWriter(buf, ['review_id', 'split', 'reason'], lineterminator='\n')
        w.writeheader()
        w.writerows(old + extra)
        return buf.getvalue().encode('utf-8')

    out = dict(members)
    out.update(new)
    out['train.tsv'] = train_tsv.encode('utf-8')
    out['charset.txt'] = charset.encode('utf-8')
    out['skipped.csv'] = merged_csv('skipped.csv', skipped)
    out['joined.csv'] = merged_csv('joined.csv', joined)

    m = dict(manifest)
    m['counts'] = dict(manifest['counts'], synthetic_crops=len(rows), synthetic_crops_used=len(evidence),
                       synthetic_pairs=len(pairs), train_pairs=manifest['counts']['train_pairs'] + len(pairs),
                       real_train_pairs=manifest['counts']['train_pairs'])
    m['skipped'] = manifest['skipped'] + skipped
    m['joined'] = manifest['joined'] + joined
    m['synthetic'] = dict(source_bundle=a.bundle.name, source_bundle_sha256=digest(a.bundle.read_bytes()),
                          labels_csv_sha256=digest(labels_path.read_bytes()),
                          manifest_sha256=digest((a.synthetic / 'manifest.json').read_bytes()),
                          limit=a.limit, segmentation=AUTOMATIC_METHOD,
                          extraction='PIL RGB -> cv2 RGB2GRAY -> imported extract_region -> grayscale PNG',
                          charset_added=sorted(set(charset) - set(old_charset)), crops=evidence)
    m['assumptions'] = manifest['assumptions'] + [
        'Synthetic crops (lines/train/SYN*) are training-only; valid/test are unchanged real crops.',
        'Synthetic line pairs use automatic segmentation; region/text count mismatches are skipped.']
    m['payload_sha256'] = {n: digest(d) for n, d in out.items() if n != 'bundle_manifest.json'}
    out['bundle_manifest.json'] = (json.dumps(m, indent=2, ensure_ascii=False) + '\n').encode('utf-8')

    a.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with a.output.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for name in sorted(out):
                z.writestr(name, out[name])
        with zipfile.ZipFile(a.output) as z:
            if z.testzip():
                raise ValueError('ZIP CRC failed')
    except BaseException:
        a.output.unlink(missing_ok=True)
        raise
    print(json.dumps(dict(output=str(a.output), sha256=digest(a.output.read_bytes()), counts=m['counts'],
                          skipped=len(skipped), joined=len(joined),
                          charset_added=m['synthetic']['charset_added']), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
