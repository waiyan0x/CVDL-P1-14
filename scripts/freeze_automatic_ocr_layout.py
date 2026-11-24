"""Freeze pixel-only training line candidates once for all OCR engines."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.ocr_crop_baseline import load_crops, segment_lines, sha256, SEGMENTATION
from backend.app.evaluation.ocr_line_layout import AUTOMATIC_METHOD, line_quads, load_layout
from backend.app.evaluation.review_decisions import load_source


def freeze(review, crop_root, split, output):
    if output.exists():
        raise FileExistsError(output)
    input_hash = sha256(review)
    records = load_crops(crop_root, review_manifest=review, crop_root=crop_root, split=split)
    rows = {r['review_id']: r for r in load_source(review)[1]}
    stamp = datetime.now(timezone.utc).isoformat()
    entries = []
    for record in records:
        row = rows[record['review_id']]
        excluded = bool(row.get('exclusion_reason') or row.get('training_exclusion_reason')
                        or row.get('training_disposition') == 'quarantined_legacy_holdout_candidate')
        with Image.open(record['crop_path']) as im:
            rgb = np.asarray(im.convert('RGB'))
            if im.size != (record['input_width'], record['input_height']):
                raise ValueError('Crop dimensions changed')
        if excluded:
            regions, info = [], {'status': 'excluded_or_quarantined_no_inference'}
        else:
            _, regions, info = segment_lines(rgb)
        separators = [[box[3], box[3]] for box in regions[:-1]]
        entry = {k: record[k] for k in ('review_id', 'crop_id', 'crop_sha256', 'input_width', 'input_height')}
        entry.update(layout_method=AUTOMATIC_METHOD, reviewer='row_projection_v2', reviewer_type='algorithm',
                     reviewed_at=stamp, independent_human_review=False,
                     review_status='accepted' if regions else 'unresolved',
                     separators=separators if regions else [],
                     line_quads=line_quads(record['input_width'], record['input_height'], separators) if regions else [],
                     reason='Frozen automatic geometry; no visual review. ' + info['status'],
                     automatic_details=info, policy_excluded=excluded)
        entries.append(entry)
    if sha256(review) != input_hash:
        raise ValueError('Review source changed during preparation')
    summary = dict(total=len(entries), accepted=sum(e['review_status']=='accepted' for e in entries),
                   unresolved=sum(e['review_status']=='unresolved' for e in entries),
                   policy_excluded=sum(e['policy_excluded'] for e in entries),
                   multiline_crops=sum(len(e['line_quads'])>1 for e in entries),
                   line_regions=sum(len(e['line_quads']) for e in entries))
    manifest = dict(schema_version=1, method=AUTOMATIC_METHOD, version=output.name, frozen=True,
                    reviewer_type='algorithm', generated_at=stamp, split=split,
                    source_review_sha256=input_hash, segmentation=SEGMENTATION,
                    transformation='Frozen horizontal partitions; original grayscale pixels; exact slices',
                    unresolved_policy='Explicit errors, including policy quarantine; no OCR fallback',
                    summary=summary, entries=entries)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp)/'layout';stage.mkdir()
        path=stage/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
        (stage/'manifest.sha256').write_text(sha256(path)+'  manifest.json\n')
        load_layout(path, records)
        stage.rename(output)
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--crop-root',type=Path,required=True)
    parser.add_argument('--split',choices=('train','valid','test'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(freeze(args.review,args.crop_root,args.split,args.output),indent=2))
