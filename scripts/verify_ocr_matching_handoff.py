"""Verify a delivered OCR handoff without loading models or requiring ML packages."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path, nargs='?', default=Path(__file__).resolve().parent)
    root = p.parse_args().folder.resolve()
    manifest = json.loads((root / 'handoff_manifest.json').read_text())
    for name, expected in manifest['files_sha256'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Path escapes package')
        with path.open('rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != expected:
                raise ValueError('Hash mismatch: ' + name)
    records = [json.loads(line) for line in (root / 'matching_inputs.jsonl').read_text().splitlines()]
    if len(records) != manifest['records'] or len({r['record_id'] for r in records}) != len(records):
        raise ValueError('Missing or duplicate records')
    panels = {r['candidate_display_id']: r for r in records if r['field'] == 'front_eds'}
    for r in records:
        if set(r) & {'text', 'transcription', 'target', 'legibility', 'scoring_eligible'}:
            raise ValueError('Ground truth found in matching inputs')
        if r['display_assignment'] in ('panel', 'ambiguous'):
            panel = panels[r['candidate_display_id']]
            if any(r[k] != panel[k] for k in ('split', 'input_set', 'source_image_sha256')):
                raise ValueError('Display join crosses source/population')
    labels = []
    for name in ('validation_labels.csv', 'test_labels.csv'):
        with (root / name).open(newline='') as f:
            labels.extend(csv.DictReader(f))
    if {r['review_id'] for r in labels} != {r['review_id'] for r in records if r['field'] != 'front_eds'}:
        raise ValueError('Label join mismatch')
    print(f"Verified {len(manifest['files_sha256'])} files, {len(records)} OCR records and {len(labels)} separate label rows")


if __name__ == '__main__':
    main()
