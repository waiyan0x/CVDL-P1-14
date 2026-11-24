"""Portable crop-only human review form with local draft recovery."""
import csv
import hashlib
import html
import json
import os
from pathlib import Path


def human_page(root, folder, title, rows, note):
    root = Path(root)
    # No source proposals or engine outputs enter this page or its form.
    folder = root / folder
    folder.mkdir(parents=True, exist_ok=True)
    form = []
    for row in rows:
        path = root / row['crop']
        if not path.is_file():
            raise FileNotFoundError(path)
        if row.get('crop_sha256') and hashlib.sha256(path.read_bytes()).hexdigest() != row['crop_sha256']:
            raise ValueError('Wrong crop: ' + row['review_id'])
        form.append(dict(review_id=row['review_id'], crop=row['crop'], field=row['field'],
                         input_set=row.get('input_set', 'annotation'), text='', legibility='',
                         field_status='', reviewer='', reviewed_at=''))
    with (folder / 'checks.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(form[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(form)
    cards = []
    for i, row in enumerate(rows):
        href = Path(os.path.relpath(root / row['crop'], folder)).as_posix()
        cards.append(f'<article data-index="{i}"><h2>{html.escape(row["review_id"])} '
                     f'— {html.escape(row["field"])}</h2><a href="{html.escape(href, quote=True)}">'
                     f'<img loading="lazy" src="{html.escape(href, quote=True)}" alt="{html.escape(row["review_id"])}"></a>'
                     '<p>Visible text<br><textarea data-key="text" rows="2"></textarea></p>'
                     '<label>Legibility <select data-key="legibility"><option value="">Choose…</option>'
                     '<option>full</option><option>partial</option><option>illegible</option>'
                     '<option>not_applicable</option></select></label> '
                     '<label>Field <select data-key="field_status"><option value="">Choose…</option>'
                     '<option>present</option><option>blank</option><option>absent</option>'
                     '<option>wrong_field</option><option>uncertain</option></select></label></article>')
    initial = json.dumps(form, ensure_ascii=False).replace('<', '\\u003c')
    set_name = folder.name
    binding = hashlib.sha256(json.dumps([(r['review_id'], r['crop'], r.get('crop_sha256')) for r in rows]).encode()).hexdigest()
    page = '''<!doctype html><meta charset="utf-8"><title>Human OCR review</title>
<style>body{font:17px system-ui;max-width:1000px;margin:30px auto;padding:0 15px}header{position:sticky;top:0;background:#fff;padding:12px;border-bottom:2px solid #aaa}article{padding:20px 0;border-bottom:1px solid #aaa}img{max-width:100%;max-height:260px;image-rendering:pixelated;min-width:160px}textarea{width:95%;font:18px monospace}button,input,select{font:inherit}small{display:block}</style>
'''
    page += '<h1>' + html.escape(title) + '</h1><p>' + html.escape(note) + '</p>'
    page += '''<p>Read pixels only; preserve case, punctuation, leading zeros and real line breaks.
Use [UNK] for an unreadable span. Partial text includes [UNK]; illegible text is [UNK].
Leave text empty for blank/absent fields. Uncertain field identity stays unresolved.</p>
<header><label>Your name <input id="reviewer"></label> <label>Actual review date <input id="date" type="date"></label>
<button id="export">Download inspected rows</button><small id="progress">No rows inspected.</small>
<small>No review is marked complete in advance. Only your own saved entries can be restored. Your draft saves in this browser when storage is available. Export CSV to submit your work.</small></header>'''
    page += ''.join(cards) + '<script>const setName=' + json.dumps(set_name) + ';const draftKey=' + json.dumps('ocr-human-review-v2:' + set_name + ':' + binding) + ';const records=' + initial + ''';
const cards=[...document.querySelectorAll('article')];
function values(){return cards.map((c,i)=>{const r={...records[i]};c.querySelectorAll('[data-key]').forEach(x=>r[x.dataset.key]=x.value);return r;});}
function checked(r){return r.legibility!==''&&r.field_status!=='';}
let draftSaved=false,dirty=false;
function touched(r){return r.text!==''||r.legibility!==''||r.field_status!=='';}
function update(){dirty=true;let msg='';try{localStorage.setItem(draftKey,JSON.stringify({records:values(),reviewer:document.getElementById('reviewer').value,date:document.getElementById('date').value}));draftSaved=true;msg='Draft saved in this browser.';}catch(e){draftSaved=false;msg='AUTOSAVE UNAVAILABLE: export before closing.';}
 document.getElementById('progress').textContent=values().filter(checked).length+' / '+records.length+' rows with human entries. '+msg;
}
try{const d=JSON.parse(localStorage.getItem(draftKey)||'null');if(d&&d.records.length===records.length&&d.records.every((r,i)=>r.review_id===records[i].review_id)){cards.forEach((c,i)=>c.querySelectorAll('[data-key]').forEach(x=>x.value=d.records[i][x.dataset.key]||''));document.getElementById('reviewer').value=d.reviewer||'';document.getElementById('date').value=d.date||'';update();}}catch(e){document.getElementById('progress').textContent='Autosave storage unavailable; export before closing.';}
window.addEventListener('beforeunload',e=>{if(dirty&&!draftSaved){e.preventDefault();e.returnValue='';}});
document.addEventListener('input',update);document.addEventListener('change',update);
document.getElementById('export').onclick=()=>{
 const name=document.getElementById('reviewer').value.trim(),date=document.getElementById('date').value;
 if(!name||!date){alert('Enter your name and actual review date.');return;}
 const all=values(),incomplete=all.filter(r=>touched(r)&&!checked(r));
 if(incomplete.length){alert('Export blocked: finish both dropdowns for '+incomplete.map(r=>r.review_id).join(', ')+'. Your entries remain in the form.');return;}
 const rows=all.filter(checked);
 if(!rows.length){alert('Inspect a crop and enter its text/state first.');return;}
 for(const r of rows){
  if(['blank','absent'].includes(r.field_status)&&(r.text!==''||r.legibility!=='not_applicable')){alert(r.review_id+': blank/absent requires empty text and not_applicable.');return;}
  if(r.field_status==='present'&&((r.legibility==='full'&&(!r.text.trim()||r.text.includes('[UNK]')))||(r.legibility==='partial'&&!r.text.includes('[UNK]'))||(r.legibility==='illegible'&&r.text!=='[UNK]'))){alert(r.review_id+': check text/legibility and [UNK].');return;}
  r.reviewer=name;r.reviewed_at=date;
 }
 const cols=Object.keys(records[0]);const quote=v=>'"'+String(v).replaceAll('"','""')+'"';
 const csv=[cols,...rows.map(r=>cols.map(k=>r[k]))].map(r=>r.map(quote).join(',')).join('\\n')+'\\n';
 const url=URL.createObjectURL(new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download=setName+'.checks.'+(name.replace(/[^a-zA-Z0-9_-]/g,'_')||'reviewer')+'.'+date+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};</script>'''
    (folder / 'review.html').write_text(page, encoding='utf-8')
    return len(form)

