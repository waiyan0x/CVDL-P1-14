"""System Tesseract adapter with bounded subprocess execution."""
import csv
import io
import shutil
import subprocess

import cv2


class TesseractAdapter:
    confidence_method = 'character_weighted_tesseract_score'

    def __init__(self, settings):
        self.executable = shutil.which('tesseract')
        if not self.executable:
            raise RuntimeError('Install the system Tesseract executable to use this engine.')

    def read(self, crop, field):
        ok, encoded = cv2.imencode('.png', crop)
        if not ok:
            return '', 0.0
        command = [self.executable, 'stdin', 'stdout', '-l', 'eng', '--psm', '7' if field == 'bus_number' else '6']
        if field == 'bus_number':
            command += ['-c', 'tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ']
        command.append('tsv')
        process = subprocess.run(command, input=encoded.tobytes(), capture_output=True, check=True, timeout=15)
        words = [row for row in csv.DictReader(io.StringIO(process.stdout.decode()), delimiter='\t')
                 if row.get('text', '').strip() and float(row['conf']) >= 0]
        raw = ' '.join(row['text'] for row in words)
        weight = sum(len(row['text']) for row in words)
        confidence = sum(len(row['text']) * float(row['conf']) / 100 for row in words) / weight if weight else 0
        return raw, confidence
