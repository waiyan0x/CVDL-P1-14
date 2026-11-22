"""Pack a spoken-announcement evaluation set for the Colab Whisper notebook.

Converts each synthesised WAV to lossless FLAC (same samples, about half the
size) and zips it with the manifest and synthesis logs.

Usage: python scripts/package_tts_eval.py evaluation/tts/announcements-v2 \
           .runtime/tts-eval/announcements-v2 .runtime/tts-eval/announcements-v2.zip
"""
import argparse
import hashlib
import io
from pathlib import Path
import zipfile

import soundfile


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('manifest_dir', type=Path)
    parser.add_argument('audio_dir', type=Path)
    parser.add_argument('zip_path', type=Path)
    parser.add_argument('--part-mb', type=int, default=10)
    args = parser.parse_args()

    clips = 0
    args.zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip_path, 'w', zipfile.ZIP_STORED) as bundle:
        for table in sorted(args.manifest_dir.glob('*.csv')):
            bundle.write(table, table.name)
        for wav in sorted(args.audio_dir.glob('*/*.wav')):
            samples, rate = soundfile.read(wav, dtype='int16')
            flac = io.BytesIO()
            soundfile.write(flac, samples, rate, format='FLAC')
            bundle.writestr(f'audio/{wav.parent.name}/{wav.stem}.flac', flac.getvalue())
            clips += 1
    size = args.zip_path.stat().st_size / 2**20
    print(f'{clips} clips -> {args.zip_path} ({size:.1f} MB)')

    data = args.zip_path.read_bytes()
    parts_dir = args.zip_path.with_name(args.zip_path.stem + '-parts')
    parts_dir.mkdir(exist_ok=True)
    for old in parts_dir.glob(args.zip_path.name + '.*'):
        old.unlink()
    step = args.part_mb * 2**20
    for index, start in enumerate(range(0, len(data), step), 1):
        (parts_dir / f'{args.zip_path.name}.part{index:02d}').write_bytes(data[start:start + step])
    (parts_dir / f'{args.zip_path.name}.sha256').write_text(hashlib.sha256(data).hexdigest() + '\n')
    print(f'{index} parts of up to {args.part_mb} MB -> {parts_dir}')


if __name__ == '__main__':
    main()
