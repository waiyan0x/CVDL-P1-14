"""Held-out text keys shared by the synthetic text pool and batch intake scripts.

A synthetic training line must never match evaluation text. Keys are stricter
than the round 2 generator's check (NFC + casefold + whitespace): NFKC, casefold
and only letters/digits kept, so "> TOA PAYOH INT" and "Toa Payoh Int" collide.
Matching is per line as well as per whole label, because training uses line
images. [UNK] spans in partial labels are removed and the readable remainder is
held when it has at least MIN_PARTIAL_KEY characters.

Sources (final human-confirmed text, plus the earlier dataset labels):
  validation  human-verification-20261116/validation.source.corrected-P065.csv
  test        test-confirmation-20261117/test.source.confirmed.csv
  route hold-out (full and partial) route-holdout-20261117/*.csv
  evaluation/ocr_dataset/labels.csv rows with split valid/test
"""
import csv
import hashlib
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'evaluation/ocr_review'
SOURCES = [
    (REVIEW / 'human-verification-20261116/validation.source.corrected-P065.csv', 'transcription', None),
    (REVIEW / 'test-confirmation-20261117/test.source.confirmed.csv', 'transcription', None),
    (REVIEW / 'route-holdout-20261117/route_holdout.source.csv', 'transcription', None),
    (REVIEW / 'route-holdout-20261117/route_holdout_partial.inventory.csv', 'transcription', None),
    (ROOT / 'evaluation/ocr_dataset/labels.csv', 'text', {'valid', 'test'}),
]
MIN_PARTIAL_KEY = 4
PADDLE_CTC_STEPS = 40  # must match ctc_steps in colab/ocr_finetune/train_paddle.py
FIELDS = ('bus_number', 'destination', 'route_text')


def key(text):
    """Comparison key: NFKC, casefold, letters and digits only."""
    return ''.join(ch for ch in unicodedata.normalize('NFKC', text).casefold() if ch.isalnum())


def ctc_need(text):
    """Same rule as add_synthetic_to_bundle.py: repeated characters need a blank step."""
    return len(text) + sum(x == y for x, y in zip(text, text[1:]))


def _keys_for(text):
    out = set()
    if '[UNK]' in text:
        for part in re.split(r'\[UNK\]', text):
            for line in part.split('\n'):
                k = key(line)
                if len(k) >= MIN_PARTIAL_KEY:
                    out.add(k)
        return out
    whole = key(text)
    if whole:
        out.add(whole)
    out |= {key(line) for line in text.split('\n') if key(line)}
    return out


def held_keys():
    """Return (keys, provenance) for every evaluation string."""
    keys, provenance = set(), []
    for path, column, splits in SOURCES:
        rows = list(csv.DictReader(open(path, encoding='utf-8')))
        used = 0
        for r in rows:
            if splits and r.get('split') not in splits:
                continue
            text = (r.get(column) or '').strip()
            if text:
                keys |= _keys_for(text)
                used += 1
        provenance.append(dict(path=str(path.relative_to(ROOT)), column=column, rows_used=used,
                               sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return keys, provenance


def leaks(text, keys):
    """Return the label keys (whole or per line) that collide with held-out text."""
    cand = {key(text)} | {key(line) for line in text.split('\n')}
    return sorted(k for k in cand if k and k in keys)
