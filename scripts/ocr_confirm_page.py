"""Confirm-or-correct page for AI-proposed OCR labels (faster than blind typing).

Rows are pre-filled with the AI proposal, but a row is exported only after the
reviewer ticks "Confirmed". Export keeps the AI proposal beside the human answer
so provenance and the correction rate stay measurable.

Usage: python3 scripts/ocr_confirm_page.py DATASET_DIR SPLIT OUT_FOLDER_NAME
"""
import csv
import hashlib
import html
import json
import os
import sys
from pathlib import Path


def build(root, split, folder_name):
    root = Path(root)
    rows = [r for r in csv.DictReader(open(root / 'labels.csv', encoding='utf-8')) if r['split'] == split]
    folder = root / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    records, cards = [], []
    for i, r in enumerate(rows):
        path = root / r['crop']
        if hashlib.sha256(path.read_bytes()).hexdigest() != r['crop_sha256']:
            raise ValueError('Wrong crop: ' + r['review_id'])
        records.append(dict(review_id=r['review_id'], crop=r['crop'], field=r['field'], input_set=r['input_set'],
                            ai_text=r['text'], ai_legibility=r['legibility'], text=r['text'],
                            legibility=r['legibility'], field_status=r['field_status'] or 'present',
                            changed='', reviewer='', reviewed_at=''))
        href = html.escape(Path(os.path.relpath(path, folder)).as_posix(), quote=True)
        opts = lambda key, values: ''.join(
            f'<option{" selected" if records[-1][key] == v else ""}>{v}</option>' for v in values)
        note = f'<small>AI note: {html.escape(r["note"])}</small>' if r.get('note') else ''
        cards.append(
            f'<article data-index="{i}"><h2>{html.escape(r["review_id"])} — {html.escape(r["field"])}</h2>'
            f'<a href="{href}"><img loading="lazy" src="{href}" alt="{html.escape(r["review_id"])}"></a>{note}'
            f'<p>Visible text<br><textarea data-key="text" rows="2">{html.escape(r["text"])}</textarea></p>'
            f'<label>Legibility <select data-key="legibility">{opts("legibility", ["full", "partial", "illegible", "not_applicable"])}</select></label> '
            f'<label>Field <select data-key="field_status">{opts("field_status", ["present", "blank", "absent", "wrong_field", "uncertain"])}</select></label> '
            f'<label class="ok"><input type="checkbox" data-key="confirmed"> Confirmed by eye</label></article>')
    binding = hashlib.sha256(json.dumps([(r['review_id'], r['crop_sha256']) for r in rows]).encode()).hexdigest()
    key = f'ocr-confirm-v1:{split}:{binding}'
    page = f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OCR label confirmation</title>
<style>body{{font:17px system-ui;max-width:1000px;margin:30px auto;padding:0 15px;background:#fff;color:#111}}header{{position:sticky;top:0;background:#fff;padding:12px;border-bottom:2px solid #aaa;z-index:1}}
article{{padding:20px 0;border-bottom:1px solid #aaa}}article.done{{background:#eef8ee}}img{{max-width:100%;max-height:260px;image-rendering:pixelated;min-width:160px}}
textarea{{width:95%;font:18px monospace}}button,input,select{{font:inherit}}small{{display:block;color:#555}}.ok{{font-weight:600;margin-left:8px}}</style>
<h1>{html.escape(split.title())}: confirm or correct {len(rows)} AI-proposed labels</h1>
<p>Each box is pre-filled with an AI reading of the crop pixels (no OCR engine output). Look at the crop, fix the text or legibility if needed, then tick <b>Confirmed by eye</b>. Only confirmed rows are exported.
Rules: keep case, punctuation and real line breaks; [UNK] marks an unreadable span; partial text contains [UNK]; illegible text is exactly [UNK].</p>
<header><label>Your name <input id="reviewer"></label> <label>Review date <input id="date" type="date"></label>
<button id="export">Download confirmed rows</button><small id="progress"></small></header>
{"".join(cards)}
<script>const draftKey={json.dumps(key)};const setName={json.dumps(split + "_confirm")};const records={json.dumps(records, ensure_ascii=False).replace("<", "\\u003c")};
const cards=[...document.querySelectorAll('article')];
function val(x){{return x.type==='checkbox'?(x.checked?'yes':''):x.value;}}
function values(){{return cards.map((c,i)=>{{const r={{...records[i]}};c.querySelectorAll('[data-key]').forEach(x=>r[x.dataset.key]=val(x));r.changed=(r.text!==r.ai_text||r.legibility!==r.ai_legibility)?'yes':'no';return r;}});}}
let saved=true;
function update(){{const v=values();cards.forEach((c,i)=>c.classList.toggle('done',v[i].confirmed==='yes'));let m;
 try{{localStorage.setItem(draftKey,JSON.stringify({{rows:v,reviewer:reviewer.value,date:date.value}}));saved=true;m='Draft saved in this browser.';}}catch(e){{saved=false;m='AUTOSAVE UNAVAILABLE: export before closing.';}}
 const n=v.filter(r=>r.confirmed==='yes');progress.textContent=n.length+' / '+records.length+' confirmed, '+n.filter(r=>r.changed==='yes').length+' corrected. '+m;}}
try{{const d=JSON.parse(localStorage.getItem(draftKey)||'null');if(d&&d.rows.length===records.length){{cards.forEach((c,i)=>c.querySelectorAll('[data-key]').forEach(x=>{{const s=d.rows[i][x.dataset.key];if(x.type==='checkbox')x.checked=s==='yes';else x.value=s??x.value;}}));reviewer.value=d.reviewer||'';date.value=d.date||'';}}}}catch(e){{}}
update();document.addEventListener('input',update);document.addEventListener('change',update);
window.addEventListener('beforeunload',e=>{{if(!saved){{e.preventDefault();e.returnValue='';}}}});
document.getElementById('export').onclick=()=>{{const name=reviewer.value.trim(),d=date.value;if(!name||!d){{alert('Enter your name and review date.');return;}}
 const rows=values().filter(r=>r.confirmed==='yes');if(!rows.length){{alert('Tick Confirmed on at least one row.');return;}}
 for(const r of rows){{if(r.field_status==='present'&&((r.legibility==='full'&&(!r.text.trim()||r.text.includes('[UNK]')))||(r.legibility==='partial'&&!r.text.includes('[UNK]'))||(r.legibility==='illegible'&&r.text!=='[UNK]'))){{alert(r.review_id+': check text/legibility and [UNK].');return;}}
  if(['blank','absent'].includes(r.field_status)&&(r.text!==''||r.legibility!=='not_applicable')){{alert(r.review_id+': blank/absent needs empty text and not_applicable.');return;}}r.reviewer=name;r.reviewed_at=d;}}
 const cols=['review_id','crop','field','input_set','text','legibility','field_status','ai_text','ai_legibility','changed','reviewer','reviewed_at'];
 const q=v=>'"'+String(v).replaceAll('"','""')+'"';const csv=[cols,...rows.map(r=>cols.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\\n')+'\\n';
 const url=URL.createObjectURL(new Blob(['\\uFEFF'+csv],{{type:'text/csv;charset=utf-8'}}));const a=document.createElement('a');a.href=url;a.download=setName+'.'+name.replace(/[^a-zA-Z0-9_-]/g,'_')+'.'+d+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}};
</script>'''
    (folder / 'review.html').write_text(page, encoding='utf-8')
    return len(rows)


if __name__ == '__main__':
    print(build(*sys.argv[1:4]), 'rows')
