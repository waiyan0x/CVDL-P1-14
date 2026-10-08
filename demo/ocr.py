"""Local OCR backends; downloads are performed only by setup scripts."""
import csv
import io
import shutil
import subprocess

import cv2
import numpy as np


class OCR:
    def __init__(self, root):
        self.root = root
        self.reader = None
        self.trocr = None
        self.error = None
        try:
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=False,
                model_storage_directory=str(root / '.cache/easyocr'),
                download_enabled=False, verbose=False)
        except Exception as exc:
            self.error = str(exc)
        self.tesseract = shutil.which('tesseract')
        if not self.reader and not self.tesseract:
            raise RuntimeError('No OCR backend available. Run scripts/setup.sh first.')

    def backends(self):
        available = ['easyocr'] if self.reader else []
        if self.tesseract:
            available.append('tesseract')
        weights = self.root / '.cache/trocr/model.safetensors'
        if weights.exists() and weights.stat().st_size > 1_000_000:
            available.append('trocr')
        return available

    def read(self, crop, field, backend):
        height, width = crop.shape[:2]
        scale = min(4, max(1, 80 / height) if field == 'bus_number' else 1, 1000 / width)
        if scale != 1:
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        if backend == 'trocr':
            return self.read_trocr(crop)
        if backend == 'easyocr':
            allow = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' if field == 'bus_number' else None
            if field == 'bus_number':
                h, w = crop.shape[:2]
                lines = self.reader.recognize(crop, horizontal_list=[[0, w, 0, h]],
                    free_list=[], detail=1, allowlist=allow)
            else:
                lines = self.reader.readtext(crop, detail=1, paragraph=False,
                    min_size=3, text_threshold=.5, low_text=.3, canvas_size=1280)
            # Preserve top-to-bottom, left-to-right ordering of detected text lines.
            lines.sort(key=lambda line: (round(line[0][0][1] / 15), line[0][0][0]))
            raw = (' ' if field == 'bus_number' else '\n').join(line[1] for line in lines).strip()
            weight = sum(len(line[1]) for line in lines)
            confidence = sum(len(line[1]) * line[2] for line in lines) / weight if weight else 0
            return raw, float(confidence)
        ok, encoded = cv2.imencode('.png', crop)
        if not ok:
            return '', 0.0
        command = [self.tesseract, 'stdin', 'stdout', '-l', 'eng', '--psm', '7' if field == 'bus_number' else '6']
        if field == 'bus_number':
            command += ['-c', 'tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ']
        command.append('tsv')
        process = subprocess.run(command, input=encoded.tobytes(), capture_output=True, check=True, timeout=15)
        words = [r for r in csv.DictReader(io.StringIO(process.stdout.decode()), delimiter='\t')
                 if r.get('text', '').strip() and float(r['conf']) >= 0]
        raw = ' '.join(r['text'] for r in words)
        weight = sum(len(r['text']) for r in words)
        confidence = sum(len(r['text']) * float(r['conf']) / 100 for r in words) / weight if weight else 0
        return raw, confidence

    def read_trocr(self, crop):
        import torch
        from PIL import Image
        if self.trocr is None:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            directory = str(self.root / '.cache/trocr')
            processor = TrOCRProcessor.from_pretrained(directory, local_files_only=True)
            model = VisionEncoderDecoderModel.from_pretrained(directory, local_files_only=True).eval()
            device = 'mps' if torch.backends.mps.is_available() else 'cpu'
            model.to(device)
            self.trocr = processor, model, device
        processor, model, device = self.trocr
        image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        pixels = processor(images=image, return_tensors='pt').pixel_values.to(device)
        with torch.inference_mode():
            output = model.generate(pixels, max_new_tokens=48, return_dict_in_generate=True, output_scores=True)
            scores = model.compute_transition_scores(output.sequences, output.scores, normalize_logits=True)
        raw = processor.batch_decode(output.sequences, skip_special_tokens=True)[0].strip()
        # Token probability geometric mean, a heuristic rather than calibrated accuracy.
        confidence = float(scores.exp().prod().pow(1 / max(scores.numel(), 1)).cpu())
        return raw, confidence if raw else 0.0
