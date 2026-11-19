#!/usr/bin/env python3
"""Focused display-ownership review page for selected crops of a matching handoff.

For each requested review_id it draws, on the source photo, the text crop (red),
every detected front_eds panel of the same photo and population (green, labelled
with its display ID) and the other text crops of that photo (blue). The reviewer
chooses the crop's display; nothing is pre-selected and no AI decision is stored.
The exported CSV uses the columns of review/display_ownership.csv plus a note.

Usage: .venv/bin/python scripts/prepare_display_review.py HANDOFF_DIR OUT_DIR P005 P035 ...
"""
import argparse
import base64
import csv
import html
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RED, GREEN, BLUE = (255, 40, 40), (0, 210, 80), (40, 120, 255)


def png64(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def jpg64(im, quality=85):
    buf = io.BytesIO()
    im.convert('RGB').save(buf, 'JPEG', quality=quality)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def draw(photo, target, panels, others, region=None):
    im = photo.copy()
    d = ImageDraw.Draw(im)
    width = max(2, round(max(im.size) / 500))
    font = ImageFont.load_default(size=max(14, round(max(im.size) / 70)))
    for p in panels:
        d.rectangle(p['box_xyxy'], outline=GREEN, width=width)
        d.text((p['box_xyxy'][0], p['box_xyxy'][3] + 2), p['display'], fill=GREEN, font=font)
    for o in others:
        d.rectangle(o['box_xyxy'], outline=BLUE, width=width)
        d.text((o['box_xyxy'][0], max(0, o['box_xyxy'][1] - font.size - 2)), o['review_id'], fill=BLUE, font=font)
    d.rectangle(target['box_xyxy'], outline=RED, width=width + 1)
    d.text((target['box_xyxy'][0], max(0, target['box_xyxy'][1] - font.size - 2)), target['review_id'], fill=RED, font=font)
    if region:
        im = im.crop(region)
    im.thumbnail((1400, 1400))
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('handoff', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('ids', nargs='+')
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f'{a.out} exists')
    h = a.handoff
    records = [json.loads(line) for line in (h / 'matching_inputs.jsonl').read_text().splitlines()]
    review = {r['review_id']: r for r in csv.DictReader(open(h / 'review/display_ownership.csv', encoding='utf-8'))}
    by_id = {r['review_id']: r for r in records}
    cards, source_rows = [], []
    for rid in a.ids:
        t, row = by_id[rid], review[rid]
        same = [r for r in records if r['split'] == t['split'] and r['input_set'] == t['input_set']
                and r['source_image_sha256'] == t['source_image_sha256'] and r['review_id'] != rid]
        panels = [dict(box_xyxy=r['box_xyxy'], display=r['candidate_display_id'].split(':')[-1],
                       display_id=r['candidate_display_id'], ocr=r['raw_ocr_text']) for r in same if r['field'] == 'front_eds']
        others = [r for r in same if r['field'] != 'front_eds']
        photo = Image.open(h / row['source_photo']).convert('RGB')
        boxes = [t['box_xyxy']] + [p['box_xyxy'] for p in panels] + [o['box_xyxy'] for o in others]
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        pad = max(80, round(0.25 * max(x1 - x0, y1 - y0)))
        region = (max(0, x0 - pad), max(0, y0 - pad), min(photo.width, x1 + pad), min(photo.height, y1 + pad))
        full = draw(photo, t, panels, others)
        zoom = draw(photo, t, panels, others, region)
        crop = Image.open(h / t['crop']).convert('RGB')
        crop = crop.resize((round(crop.width * 90 / crop.height), 90), Image.NEAREST)
        options = ''.join(
            f'<option value="{html.escape(p["display_id"], quote=True)}">Same display as panel {html.escape(p["display"])}'
            f' (panel OCR: {html.escape(p["ocr"].replace(chr(10), " | ") or "-")})</option>' for p in panels)
        others_txt = ''.join(
            f'<li><b>{html.escape(o["review_id"])}</b> {html.escape(o["field"])}: '
            f'"{html.escape(o["raw_ocr_text"].replace(chr(10), " | "))}" → display {html.escape(o["candidate_display_id"].split(":")[-1])}</li>'
            for o in others) or '<li>None</li>'
        situation = {'none': 'No detected panel covers this crop (coverage < 50%).',
                     'ambiguous': 'More than one detected panel covers this crop.'}.get(row['assignment'], row['assignment'])
        cards.append(f'''<section data-id="{html.escape(rid)}">
<h2>{html.escape(rid)} <small>{html.escape(t['field'])} · {html.escape(t['split'])}/{html.escape(t['input_set'])}</small></h2>
<p><b>Why it is flagged:</b> {situation} Current proposal: <code>{html.escape(row['candidate_display_id'].split(':')[-1])}</code>.</p>
<p><b>OCR of this crop:</b> "{html.escape(t['raw_ocr_text'].replace(chr(10), ' | ')) or '(empty)'}"</p>
<img class="crop" src="{png64(crop)}" alt="text crop">
<p class="legend"><span style="color:rgb{RED}">Red</span>: this crop ·
<span style="color:rgb{GREEN}">Green</span>: detected panels (display IDs) ·
<span style="color:rgb{BLUE}">Blue</span>: other text crops in the photo</p>
<img src="{jpg64(zoom)}" alt="zoomed photo">
<details><summary>Whole photo</summary><img src="{jpg64(full, 75)}" alt="whole photo"></details>
<p><b>Other text crops in this photo:</b></p><ul>{others_txt}</ul>
<fieldset><legend>Which display does {html.escape(rid)} belong to?</legend>
<select data-key="choice"><option value="">Choose…</option>{options}
<option value="__own__">Its own display (a bus/panel the detector missed)</option>
<option value="__other__">Same display as another crop (type its display ID)</option>
<option value="__unresolved__">Cannot tell / leave unresolved</option></select>
<label>Display ID (only for "another crop") <input data-key="other_id"></label>
<label>Note <input data-key="note" size="50"></label></fieldset></section>''')
        source_rows.append(dict(row, own_display_id=row['candidate_display_id'] if row['assignment'] == 'none'
                                else f"{t['split']}:{t['input_set']}:{Path(t['source_image']).stem}:solo-{rid}"))
    page = PAGE.replace('__CARDS__', '\n'.join(cards)).replace('__ROWS__', json.dumps(source_rows).replace('<', '\\u003c'))
    a.out.mkdir(parents=True)
    (a.out / 'display_ownership_review.html').write_text(page, encoding='utf-8')
    print(f"Wrote {a.out / 'display_ownership_review.html'} for {', '.join(a.ids)}")


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Display ownership review</title>
<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:0 16px;color:#111;background:#fff}
section{border-top:2px solid #ccc;padding:16px 0}img{max-width:100%;display:block;margin:8px 0}img.crop{image-rendering:pixelated;border:1px solid #999}
header{position:sticky;top:0;background:#fff;padding:10px 0;border-bottom:1px solid #ccc;z-index:2}fieldset{margin-top:10px}
label{display:block;margin-top:6px}code{background:#eee;padding:0 4px}small{color:#555;font-weight:normal}.legend{font-size:14px}</style>
<h1>Display ownership review: 4 flagged crops</h1>
<p>For each crop, decide which bus display it belongs to, so its number/destination can be paired with the right fields.
Judge from the photo only. Nothing is pre-selected and no automatic decision is recorded. Choose "Cannot tell" when unsure.
These are validation detector crops; this is not a text-label review.</p>
<header><label>Your name <input id="reviewer"></label><label>Date <input id="date" type="date"></label>
<button id="export">Download decisions (CSV)</button> <span id="status"></span>
<div><small>This page does not save. Download before closing.</small></div></header>
__CARDS__
<script>
const source=__ROWS__;
document.getElementById('export').onclick=()=>{
 const reviewer=document.getElementById('reviewer').value.trim(),date=document.getElementById('date').value;
 if(!reviewer||!date){alert('Enter your name and date');return;}
 const out=[];
 for(const [i,s] of [...document.querySelectorAll('section')].entries()){
  const v=k=>s.querySelector(`[data-key="${k}"]`).value.trim(),src=source[i];let decision,id;
  const c=v('choice');if(!c){alert('Choose an option for '+src.review_id);return;}
  if(c==='__unresolved__'){decision='unresolved';id='';}
  else if(c==='__own__'){id=src.own_display_id;decision=id===src.candidate_display_id?'confirm_candidate':'correct_display';}
  else if(c==='__other__'){id=v('other_id');if(!id){alert('Type the display ID for '+src.review_id);return;}decision='correct_display';}
  else{id=c;decision=id===src.candidate_display_id?'confirm_candidate':'correct_display';}
  const r={...src};delete r.own_display_id;r.human_decision=decision;r.human_display_id=id;r.reviewer=reviewer;r.reviewed_at=date;r.note=v('note');out.push(r);
 }
 const cols=Object.keys(out[0]),q=x=>'"'+String(x??'').replaceAll('"','""')+'"';
 const csv=[cols,...out.map(r=>cols.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\n')+'\n';
 const url=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));
 const link=document.createElement('a');link.href=url;link.download='display_ownership_flagged.'+reviewer.replace(/[^a-zA-Z0-9_-]/g,'_')+'.'+date+'.csv';link.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('status').textContent=out.length+' decisions downloaded';
};
</script></html>'''

if __name__ == '__main__':
    main()
