import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.ocr_human_review_page import human_page


class HumanReviewPageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for form behaviour checks')
    def test_draft_recovery_incomplete_export_and_distinct_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'crop.png').write_bytes(b'synthetic-image-placeholder')
            human_page(root, 'validation', 'Synthetic test',
                       [dict(review_id='A001', crop='crop.png', field='bus_number')], 'Synthetic only')
            page = (root/'validation/review.html').read_text()
            js = re.search(r'<script>(.*)</script>', page, re.S).group(1)
            harness = r'''
const vm=require('vm'),assert=require('assert');
const source=SOURCE,storage=new Map();
function open(){
 const fields=['text','legibility','field_status'].map(k=>({dataset:{key:k},value:''}));
 const elements={reviewer:{value:''},date:{value:''},progress:{textContent:''},export:{}};
 const alerts=[],downloads=[],events={};
 const document={querySelectorAll:()=>[{querySelectorAll:()=>fields}],getElementById:k=>elements[k],
 addEventListener:(k,f)=>events[k]=f,createElement:()=>({click(){downloads.push(this.download)}})};
 const context={document,window:{addEventListener(){}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
 alert:x=>alerts.push(x),Blob:class{},URL:{createObjectURL:()=>'',revokeObjectURL(){}},setTimeout:f=>f()};
 vm.runInNewContext(source,context);
 return {fields,elements,alerts,downloads,events};
}
let a=open();assert(a.fields.every(f=>f.value===''));
a.elements.reviewer.value='Synthetic reviewer';a.elements.date.value='2026-11-16';
a.fields[0].value='097E';a.events.input();a.elements.export.onclick();
assert(a.alerts.some(s=>s.includes('A001')));assert.equal(a.downloads.length,0);
let b=open();assert.equal(b.fields[0].value,'097E');assert.equal(b.elements.reviewer.value,'Synthetic reviewer');
b.fields[1].value='full';b.fields[2].value='present';b.events.change();b.elements.export.onclick();
assert.deepEqual(b.downloads,['validation.checks.Synthetic_reviewer.2026-11-16.csv']);
assert(b.elements.progress.textContent.includes('Draft saved'));
'''.replace('SOURCE', json.dumps(js))
            result = subprocess.run(['node', '-e', harness], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
