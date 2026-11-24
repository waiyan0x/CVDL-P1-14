"""Score Whisper transcripts of spoken announcements against their intended meaning.

Inputs (from build_tts_manifest.mjs, synthesize_tts_windows.ps1 and the Colab
notebook colab/tts_eval/tts_whisper_eval.ipynb):
  <run>/manifest.csv, <run>/synthesis_<voice>.csv, <run>/transcripts.csv

Each clip is scored on the whole utterance (WER), whether the bus service was
heard exactly, and the destination words alone. Raw and normalised wording of
the same route share one reference, so their difference is the effect of the
text clean-up. Speech recognition is a proxy for a listener, not a user study.

Usage: python scripts/score_tts_transcripts.py evaluation/tts/announcements-v2
"""
import argparse
import csv
from pathlib import Path
import re
import statistics

NUMBER_WORDS = {'zero': '0', 'oh': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'}
# Whisper writes US spelling; the reference names are Singapore (British) spelling.
SPELLING = {'center': 'centre'}


def normalise(text):
    """Lower-case words with spelled-out codes joined: "9 2 B", "92B" and "9-2B" all become "92b"."""
    # A hyphen next to a digit is code formatting ("TS-1", "8-4G"); elsewhere it joins words ("Ritz-Carlton").
    text = re.sub(r'(?<=[0-9])-|-(?=[0-9])', '', text.lower())
    words = re.sub(r"[^a-z0-9 ]+", ' ', text.replace('-', ' ')).split()
    words = [NUMBER_WORDS.get(word, SPELLING.get(word, word)) for word in words]
    joined, run = [], []
    for word in words + ['']:
        # Digits and single letters are the pieces of service, block and acronym codes.
        if word and (word.isdigit() or len(word) == 1):
            run.append(word)
            continue
        if run:
            joined.append(''.join(run))
            run = []
        if word:
            joined.append(word)
    return joined


def word_errors(reference, hypothesis):
    """Levenshtein distance over words."""
    previous = list(range(len(hypothesis) + 1))
    for i, ref_word in enumerate(reference, 1):
        current = [i]
        for j, hyp_word in enumerate(hypothesis, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ref_word != hyp_word)))
        previous = current
    return previous[-1]


def after(words, marker, fallback):
    """Words after the first `marker`; if it was not heard, after position `fallback`."""
    return words[words.index(marker) + 1:] if marker in words else words[fallback:]


def score(reference, transcript, service):
    """Announcements read "Bus <service> to <destination>." The service is the word after "bus";
    the destination is everything after "to" (or after the service, if "to" was lost, e.g. heard
    as part of the number: "Bus 1 7 4 to" -> "Bus 17442")."""
    ref, hyp = normalise(reference), normalise(transcript)
    ref_dest, hyp_dest = after(ref, 'to', 2), after(hyp, 'to', 2)
    code = ''.join(normalise(service))
    heard = after(hyp, 'bus', 1)[:1]
    return {
        'ref_words': len(ref), 'word_errors': word_errors(ref, hyp),
        'service_correct': int(heard == [code]),
        'dest_words': len(ref_dest), 'dest_errors': word_errors(ref_dest, hyp_dest),
        'dest_exact': int(ref_dest == hyp_dest),
    }


SERVICE_KINDS = ('digits (174)', 'digits + A (63A)', 'digits + other letter (92B, 10E)', 'letter prefix (CW1, TS8)')


def service_kind(service):
    if service.isdigit():
        return SERVICE_KINDS[0]
    if re.fullmatch(r'[0-9]+A', service):
        return SERVICE_KINDS[1]
    if re.fullmatch(r'[0-9]+[A-Z]+', service):
        return SERVICE_KINDS[2]
    return SERVICE_KINDS[3]


def read(path):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('run', type=Path)
    args = parser.parse_args()

    manifest = read(args.run / 'manifest.csv')
    synthesis = {(row['voice'], row['clip_id']): row
                 for table in sorted(args.run.glob('synthesis_*.csv')) for row in read(table)}
    transcripts = {(row['voice'], row['clip_id']): row for row in read(args.run / 'transcripts.csv')}
    voices = sorted({voice for voice, _ in transcripts})

    rows = []
    for voice in voices:
        for item in manifest:
            heard = transcripts.get((voice, item['clip_id']))
            if heard is None:
                raise SystemExit(f'Missing transcript for {voice} / {item["clip_id"]}')
            timing = synthesis.get((voice, item['clip_id']), {})
            rows.append({**item, 'voice': voice, 'transcript': heard['transcript'],
                         'audio_ms': timing.get('audio_ms', ''), 'synthesis_ms': timing.get('synthesis_ms', ''),
                         **score(item['reference'], heard['transcript'], item['service'])})
    fields = list(rows[0])
    with open(args.run / 'scores.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)

    model = sorted({row.get('model', '') for row in transcripts.values()})
    groups = list(dict.fromkeys(item['group'] for item in manifest))
    conditions = list(dict.fromkeys(item['condition'] for item in manifest))
    if conditions == ['raw', 'normalised']:
        wordings = ('Each route is announced with the matcher message as written (raw) and as the app '
                    'speaks it (normalised); both are scored against the same normalised meaning.')
    else:
        wordings = (f'Each route is announced in {len(conditions)} wordings ({", ".join(conditions)}); '
                    'all are scored against the same meaning.')
    lines = [f'# Spoken announcement intelligibility: {args.run.name}', '',
             f'Speech recognition: {", ".join(model)}. Voices: {", ".join(voices)}. {wordings} '
             'WER and destination WER: lower is better. Service heard and destination exact: higher is '
             'better. All in %.', '',
             '| Voice | Group | Wording | n | WER | Service heard | Destination WER | Destination exact |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for voice in voices + ['all voices']:
        for group in groups:
            for condition in conditions:
                subset = [r for r in rows if r['group'] == group and r['condition'] == condition
                          and voice in (r['voice'], 'all voices')]
                if not subset:
                    continue
                rate = lambda e, n: 100 * sum(r[e] for r in subset) / max(1, sum(r[n] for r in subset))
                mean = lambda key: 100 * statistics.mean(r[key] for r in subset)
                lines.append(f'| {voice} | {group} | {condition} | {len(subset)} | {rate("word_errors", "ref_words"):.1f} '
                             f'| {mean("service_correct"):.1f} | {rate("dest_errors", "dest_words"):.1f} '
                             f'| {mean("dest_exact"):.1f} |')

    # The service wording differs by code shape: "1 7 4", "6 3 A", "C W 1".
    lines += ['', 'Service heard by code shape, all routes and voices (%):', '',
              f'| Service code | n | {" | ".join(conditions)} |', '| --- | ---: |' + ' ---: |' * len(conditions)]
    for kind in SERVICE_KINDS:
        subsets = [[r for r in rows if r['condition'] == condition and service_kind(r['service']) == kind]
                   for condition in conditions]
        if subsets[0]:
            cells = ' | '.join(f'{100 * statistics.mean(r["service_correct"] for r in subset):.1f}' for subset in subsets)
            lines.append(f'| {kind} | {len(subsets[0])} | {cells} |')

    # Paired by route and voice: the same route and voice, only the wording differs.
    paired = {}
    for row in rows:
        paired.setdefault((row['voice'], row['item_id']), {})[row['condition']] = row
    lines.append('')
    if conditions == ['raw', 'normalised']:
        changed = [p for p in paired.values() if p['raw']['group'] == 'changed']
        better = sum(p['normalised']['dest_exact'] > p['raw']['dest_exact'] for p in changed)
        worse = sum(p['normalised']['dest_exact'] < p['raw']['dest_exact'] for p in changed)
        lines.append(f'Changed routes, paired by voice: destination exact improved in {better} and '
                     f'worsened in {worse} of {len(changed)} pairs.')
    else:
        base = conditions[0]
        for condition in conditions[1:]:
            pairs = [p for p in paired.values() if base in p and condition in p]
            better = sum(p[condition]['service_correct'] > p[base]['service_correct'] for p in pairs)
            worse = sum(p[condition]['service_correct'] < p[base]['service_correct'] for p in pairs)
            lines.append(f'- {condition} vs {base}, paired by route and voice: service heard improved in '
                         f'{better} and worsened in {worse} of {len(pairs)} pairs.')
    lines += ['', '| Wording | Announcement length median / p95 (s) | Synthesis time median / p95 (ms) |',
              '| --- | ---: | ---: |']
    for condition in conditions:
        subset = [r for r in rows if r['condition'] == condition and r['audio_ms']]
        if subset:
            audio = [float(r['audio_ms']) / 1000 for r in subset]
            synth = [float(r['synthesis_ms']) for r in subset]
            lines.append(f'| {condition} | {statistics.median(audio):.1f} / {percentile(audio, .95):.1f} '
                         f'| {statistics.median(synth):.0f} / {percentile(synth, .95):.0f} |')
    lines += ['', 'Synthesis time is Windows OneCore offline synthesis to a file, not browser '
              'start-of-speech latency. Speech recognition stands in for a listener; it is not '
              'evidence of accessibility for visually impaired commuters.']
    (args.run / 'TTS_RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
