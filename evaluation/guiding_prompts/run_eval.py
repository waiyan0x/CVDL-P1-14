"""Guiding prompt evaluation: frame each sample's bus sign in every situation the prompts cover, send the frame
through the running app (POST /api/analysis, the call Live makes), and save the responses for score.mjs.

Usage (with the app running): .venv/bin/python evaluation/guiding_prompts/run_eval.py [--server URL]

Each sample's sign position comes from the detector on the original image (the largest model-detected display).
Frames are 1280x720, like a landscape camera frame. The sign is moved and scaled with one affine warp; space
outside the original photo is filled with flat grey.
"""
from __future__ import annotations

import argparse
import io
import json
import time
import urllib.request
import uuid
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
W, H = 1280, 720
GREY = (114, 114, 114)
CUTS = (0.0, 0.2, 0.4, 0.6)       # Fraction of the sign pushed past the frame edge (0 = just touching).


def post(server, image, backend):
    ok, jpeg = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in (('backend', backend), ('source', 'image')):
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="frame.jpg"\r\n'
               'Content-Type: image/jpeg\r\n\r\n'.encode() + jpeg.tobytes() + f'\r\n--{boundary}--\r\n'.encode())
    request = urllib.request.Request(f'{server}/api/analysis', data=body.getvalue(),
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    for attempt in range(60):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429:
                raise
            time.sleep(min(2 + attempt, 10))
    raise RuntimeError('server stayed busy')


def sign_box(data):
    """Largest display box the detector found, or None."""
    boxes = [r['screen']['box'] for r in data.get('results', [])
             if r.get('screen') and r['screen'].get('source') == 'model' and r['screen'].get('label') == 'eds']
    return max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), default=None)


def warp(image, box, sign_width, centre):
    """Scale the image so the sign is sign_width px wide and centred at `centre` in a WxH frame."""
    x1, y1, x2, y2 = box
    s = sign_width / (x2 - x1)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    matrix = np.float32([[s, 0, centre[0] - s * cx], [0, s, centre[1] - s * cy]])
    interpolation = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    frame = cv2.warpAffine(image, matrix, (W, H), flags=interpolation, borderMode=cv2.BORDER_CONSTANT, borderValue=GREY)
    inside = cv2.warpAffine(np.full(image.shape[:2], 255, np.uint8), matrix, (W, H), flags=cv2.INTER_NEAREST) > 0
    return np.where(inside[..., None], frame, backdrop(image))


def backdrop(image):
    """The photo scaled to cover the frame and blurred until no text survives: stands in for the scene
    beyond the photo's edges, without the hard grey border a flat fill leaves."""
    scale = max(W / image.shape[1], H / image.shape[0])
    cover = cv2.resize(image, (int(image.shape[1] * scale) + 1, int(image.shape[0] * scale) + 1))
    top, left = (cover.shape[0] - H) // 2, (cover.shape[1] - W) // 2
    return cv2.GaussianBlur(cover[top:top + H, left:left + W], (0, 0), 30)


def scenarios(image, box):
    """(scenario, expected prompt code, frame). Expected None means no prompt should be needed."""
    x1, y1, x2, y2 = box
    natural = (x2 - x1) / image.shape[1]
    sw = W * min(max(natural, .20), .45)   # Readable size: 20-45% of the frame width.
    sh = sw * (y2 - y1) / (x2 - x1)
    yield 'centred', None, warp(image, box, sw, (W / 2, H / 2))
    for cut in CUTS:
        tag = f'{round(cut * 100)}%'
        yield f'left {tag}', 'left', warp(image, box, sw, (sw / 2 - cut * sw, H / 2))
        yield f'right {tag}', 'right', warp(image, box, sw, (W - sw / 2 + cut * sw, H / 2))
        yield f'top {tag}', 'top', warp(image, box, sw, (W / 2, sh / 2 - cut * sh))
        yield f'bottom {tag}', 'bottom', warp(image, box, sw, (W / 2, H - sh / 2 + cut * sh))
    for over in (1.15, 1.4):
        yield f'fills {over:.2f}x', 'wide', warp(image, box, W * over, (W / 2, H / 2))
    for width in (.07, .05, .035):
        yield f'small {round(width * 100, 1)}%', 'small', warp(image, box, W * width, (W / 2, H / 2))
    # The sign painted out: the frame now has no front display (other displays in the photo may remain).
    masked = image.copy()
    pad = int(.1 * (x2 - x1))
    mask = np.zeros(image.shape[:2], np.uint8)
    mask[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad] = 255
    masked = cv2.inpaint(masked, mask, 5, cv2.INPAINT_TELEA)
    yield 'no sign', 'none', warp(masked, box, sw, (W / 2, H / 2))


def compact(data):
    return {'width': data['width'], 'height': data['height'], 'status': data.get('status'),
            'results': [{'screen': r.get('screen') and {k: r['screen'].get(k) for k in ('label', 'source', 'box', 'confidence')},
                         'fields': {name: {'box': f.get('box')} for name, f in (r.get('fields') or {}).items() if f},
                         'match': r.get('match')} for r in data.get('results', [])]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default='http://127.0.0.1:8000')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--resume', action='store_true', help='keep responses.jsonl and skip finished images')
    args = parser.parse_args()
    with urllib.request.urlopen(f'{args.server}/api/health') as response:
        backend = json.load(response)['default_backend']
    images = sorted(p for p in (ROOT / 'data/samples').rglob('*') if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
    if args.limit:
        images = images[:args.limit]
    frames_dir = OUT / 'frames'
    frames_dir.mkdir(exist_ok=True)
    started = time.time()
    log = OUT / 'responses.jsonl'
    done = set()
    if args.resume and log.exists():
        # An image is finished when its last scenario was written; drop any partly written image.
        records = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
        done = {r['image'] for r in records if r['scenario'] == 'no sign'}
        done |= {r['image'] for r in records if r['scenario'] == 'original' and not r.get('sign_box')}
        log.write_text(''.join(json.dumps(r) + '\n' for r in records if r['image'] in done), encoding='utf-8')
    with open(log, 'a' if args.resume else 'w', encoding='utf-8') as out:
        for index, path in enumerate(images, 1):
            if str(path.relative_to(ROOT / 'data/samples')) in done:
                continue
            image = cv2.imread(str(path))
            if image is None:
                continue
            name = str(path.relative_to(ROOT / 'data/samples'))
            original = post(args.server, image, backend)
            box = sign_box(original)
            record = {'image': name, 'backend': backend, 'scenario': 'original', 'expected': None,
                      'sign_box': box, 'response': compact(original)}
            out.write(json.dumps(record) + '\n')
            if not box:
                print(f'[{index}/{len(images)}] {name}: no display detected, skipped')
                continue
            for scenario, expected, frame in scenarios(image, box):
                if index <= 3:
                    cv2.imwrite(str(frames_dir / f"{path.stem}__{scenario.replace(' ', '_').replace('%', 'pc')}.jpg"), frame)
                response = post(args.server, frame, backend)
                out.write(json.dumps({'image': name, 'backend': backend, 'scenario': scenario, 'expected': expected,
                                      'response': compact(response)}) + '\n')
            out.flush()
            print(f'[{index}/{len(images)}] {name} done ({time.time() - started:.0f}s)', flush=True)


if __name__ == '__main__':
    main()
