"""Preprocessing sweep on the scored validation crops. Usage: prep_exp.py ENGINE PKG RECORDS OUT.csv"""
import csv, sys, os, re, time
import cv2, numpy as np

engine, pkg, records_csv, out = sys.argv[1:5]
weights = os.path.join(pkg, 'weights')

def lev(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        c = [i]
        for j, y in enumerate(b, 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (x != y)))
        p = c
    return p[-1]

def norm(s):
    return ' '.join(s.split()).casefold()

# ---------- variants (input/output: RGB uint8) ----------
def up(img, f=2):
    return cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)

def to3(g):
    return cv2.cvtColor(g, cv2.COLOR_GRAY2RGB)

def gray(img):
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

def v_raw(img): return img
def v_up2(img): return up(img, 2)
def v_up2_sharp(img):
    u = up(img, 2); b = cv2.GaussianBlur(u, (0, 0), 2)
    return cv2.addWeighted(u, 1.6, b, -0.6, 0)
def v_clahe(img):
    g = gray(up(img, 2)); return to3(cv2.createCLAHE(2.0, (8, 8)).apply(g))
def v_otsu_inv(img):  # bright LED text -> black text on white (screenshot "colour threshold")
    g = cv2.GaussianBlur(gray(up(img, 2)), (3, 3), 0)
    _, t = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return to3(255 - t)
def v_close(img):  # bridge LED dots into solid strokes
    g = gray(up(img, 2)); k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return to3(cv2.morphologyEx(g, cv2.MORPH_CLOSE, k))
def v_blur_bridge(img):  # soften dot matrix
    return cv2.GaussianBlur(up(img, 2), (0, 0), 2.0)
def v_erode(img):  # screenshot "thin thick strokes"
    g = gray(up(img, 2)); return to3(cv2.erode(g, np.ones((3, 3), np.uint8)))
def v_pad(img):
    h = img.shape[0]; p = max(4, h // 4)
    return cv2.copyMakeBorder(img, p, p, p, p, cv2.BORDER_REPLICATE)

VARIANTS = dict(raw=v_raw, up2=v_up2, up2_sharp=v_up2_sharp, clahe=v_clahe, otsu_inv=v_otsu_inv,
                close=v_close, blur_bridge=v_blur_bridge, erode=v_erode, pad=v_pad)

# ---------- engines ----------
if engine == 'trocr':
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from PIL import Image
    proc = TrOCRProcessor.from_pretrained(os.path.join(weights, 'trocr'))
    model = VisionEncoderDecoderModel.from_pretrained(os.path.join(weights, 'trocr')).eval()
    def run(img):
        with torch.no_grad():
            px = proc(images=Image.fromarray(img), return_tensors='pt').pixel_values
            ids = model.generate(px, max_new_tokens=48, num_beams=1)
        return proc.batch_decode(ids, skip_special_tokens=True)[0]
elif engine == 'easyocr':
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False, model_storage_directory=os.path.join(weights, 'easyocr'),
                            download_enabled=False, verbose=False)
    def run(img):
        h, w = img.shape[:2]
        res = reader.recognize(gray(img), horizontal_list=[[0, w, 0, h]], free_list=[], detail=0,
                               decoder='greedy', contrast_ths=0.0)
        return ' '.join(res)
elif engine == 'paddleocr':
    from paddleocr import TextRecognition
    rec = TextRecognition(model_name='en_PP-OCRv5_mobile_rec', model_dir=os.path.join(weights, 'paddleocr'))
    def run(img):
        r = rec.predict(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), batch_size=1)
        return r[0]['rec_text'] if r else ''
else:
    raise SystemExit('unknown engine')

# ---------- data: eligible crops with their reference ----------
rows = {}
for r in csv.DictReader(open(records_csv)):
    if r['scoring_eligible'] == 'True':
        rows[r['review_id']] = r
crop_path = {r['review_id']: r['crop'] for r in csv.DictReader(open(os.path.join(pkg, 'labels/validation_labels.proposals.csv')))}

with open(out, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['engine', 'variant', 'review_id', 'input_set', 'field', 'ref', 'hyp'])
    for rid, r in sorted(rows.items()):
        img = cv2.cvtColor(cv2.imread(os.path.join(pkg, crop_path[rid])), cv2.COLOR_BGR2RGB)
        for vn, vf in VARIANTS.items():
            try:
                hyp = run(vf(img))
            except Exception as e:
                hyp = ''
            w.writerow([engine, vn, rid, r['input_set'], r['field'], r['normalised_reference_text'], norm(hyp)])
print('done', engine, len(rows))
