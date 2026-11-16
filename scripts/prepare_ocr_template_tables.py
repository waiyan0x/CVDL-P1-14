"""Render the requested six-column layout using measured data or explicit statuses."""

import argparse
import csv
from html import escape
import json
from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.review_decisions import digest

FIELDS = ("front_eds", "front_eds_destination", "front_eds_route", "front_eds_num")


def table_rows(records):
    result = []
    for row in records:
        count = "Reserved" if row["crops"] is None else str(row["crops"])
        eligible = (f'<small>{row["eligible"]} eligible for scoring</small>'
                    if row["eligible"] is not None else '<small>not assessed / context</small>')
        if row.get("candidate_crops") is not None:
            count = str(row["candidate_crops"])
            eligible = f'<small>of {row["crops"]} available; AI-label subset</small>'
        values = [{"train": "Train", "valid": "Validation", "test": "Test"}[row["split"]],
                  row["crop_class"]]
        result.append('<tr>' + ''.join('<td>' + escape(v) + '</td>' for v in values)
                      + '<td>' + count + eligible + '</td>'
                      + ''.join('<td>' + (f'{100*row[k]:.2f}' if row[k] is not None
                                           else escape(row["status"])) + '</td>'
                                for k in ("cer", "wer", "exact_match")) + '</tr>')
    return ''.join(result)


def render_tables(records, models):
    records = [dict(r, score_basis=r.get("score_basis", "verified")) for r in records]
    diagnostic = any(r["score_basis"] == "provisional_ai" for r in records)
    default_basis = "provisional_ai" if diagnostic else "verified"
    has_train_metrics = any(r['split']=='train' and r['cer'] is not None for r in records)
    date = datetime.now(ZoneInfo("Asia/Singapore")).strftime("%d %B %Y")
    totals = {}
    for pop in ("annotation", "prediction"):
        per_model = [sum(r["eligible"] or 0 for r in records
                         if r["model"] == model["id"] and r["scoring_mode"] == "normalised"
                         and r["score_basis"] == "verified"
                         and r["input_set"] == pop and r["split"] == "valid") for model in models]
        if len(set(per_model)) != 1:
            raise ValueError("Models must use the same eligible validation counts")
        totals[pop] = per_model[0]
    parts = ['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>Three OCR baseline tables</title>',
             '<style>body{background:#080e09;color:#b7edc9;font:15px ui-monospace,monospace;margin:24px}'
             'section{background:#132018;border:1px solid #344739;border-radius:24px;padding:24px;margin:24px 0}'
             'table{border-collapse:collapse;width:100%;min-width:850px}th,td{padding:16px 10px;border-bottom:1px solid #28392c;text-align:right}'
             'th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}small{display:block;font-size:11px;margin-top:6px}'
             'p{line-height:1.6;max-width:1100px}.scroll{overflow-x:auto}select{font:inherit;padding:8px;margin:8px;color:#b7edc9;background:#132018}</style>',
             '<h1>Three pretrained OCR baseline tables</h1>', '<p>Prepared ' + date + '</p>',
             '<p><strong>Pipeline stage: OCR scoring before reference matching.</strong> '
             'Raw and Step 4-normalised values both come from recogniser outputs; no reference lookup or inferred match is used.</p>',
             ('<p style="background:#493722;padding:18px">Default view: <strong>provisional agreement with AI-assisted labels</strong>. '
              'Numerical cells use a selected readable subset, not verified accuracy. Human field, grouping and correspondence checks remain pending. '
              'Choose the verified benchmark view to see review-gated results.</p>' if diagnostic else ''),
             '<p>One table per model. Select Step 4-normalised or primary raw scoring and the crop population below. '
             'Models share the same examples and scoring rules. In the AI-label view, Crops (n) is the actual compared subset, '
             'with available inventory beneath it. The verified view shows inventory and its eligible scoring denominator.</p>',
             f'<p>Eligible validation crops: annotation {totals["annotation"]}; detector-predicted {totals["prediction"]}. '
             'These are the human-verified eligible counts. Review pending does not mean zero accuracy. '
             'No values from the example screenshot are used.</p>',
             '<p>front_eds is panel context with N/A text metrics. '
             + ('Train contains training-split diagnostics with frozen automatic line geometry; validation uses earlier AI-reviewed geometry. '
                'Weights were not fine-tuned; do not interpret split differences as a controlled preprocessing comparison. ' if has_train_metrics else 'Train is not run. ')
             + 'Test is reserved. '
             'Route/road text is separate from destination. Reference matching is outside these OCR tables.</p>',
             ('<label>Evidence <select id="basis"><option value="provisional_ai">Provisional AI-label agreement</option>'
              '<option value="verified">Human-verified benchmark</option></select></label>' if diagnostic else
              '<input type="hidden" id="basis" value="verified">'),
             '<label>Scoring <select id="mode"><option value="normalised">Step 4-normalised</option><option value="raw">Primary raw</option></select></label>',
             '<label>Crops <select id="population"><option value="annotation">Annotation-box crops</option><option value="prediction">Detector-predicted crops</option></select></label>']
    for model in models:
        visible = [r for r in records if r["model"] == model["id"]
                   and r["score_basis"] == default_basis
                   and r["scoring_mode"] == "normalised" and r["input_set"] == "annotation"]
        parts.append('<section data-model="' + escape(model["id"], quote=True) + '"><h2>'
                     + escape(model["name"]) + '</h2><div class="scroll"><table><thead><tr>'
                     + ''.join('<th>' + title + '</th>' for title in
                               ('Split', 'Crop class', 'Crops (n)', 'CER (%) ↓', 'WER (%) ↓', 'Exact match (%) ↑'))
                     + '</tr></thead><tbody>' + table_rows(visible) + '</tbody></table></div></section>')
    parts.extend(['<p>Raw scoring uses NFC and per-line word spacing while preserving case/punctuation. '
                  'Step 4-normalised scoring adds Unicode casefold and collapsed whitespace; it preserves suffixes, zeros and abbreviations. '
                  'Both modes transform predictions and references identically.</p>',
                  '<script type="application/json" id="records">' + json.dumps(records).replace('<', '\\u003c') + '</script>',
                  '''<script>
const records=JSON.parse(document.getElementById('records').textContent);
const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function update(){
 const mode=document.getElementById('mode').value,pop=document.getElementById('population').value,basis=document.getElementById('basis').value;
 document.querySelectorAll('section[data-model]').forEach(section=>{
  section.querySelector('tbody').innerHTML=records.filter(r=>r.model===section.dataset.model&&r.scoring_mode===mode&&r.input_set===pop&&r.score_basis===basis).map(r=>{
   const metrics=['cer','wer','exact_match'].map(k=>r[k]===null?escapeHTML(r.status):(100*r[k]).toFixed(2));
   const hasSubset=r.candidate_crops!==null&&r.candidate_crops!==undefined;
   const count=hasSubset?r.candidate_crops:r.crops===null?'Reserved':r.crops;
   const eligible=hasSubset?'of '+r.crops+' available; AI-label subset':r.eligible===null?'not assessed / context':r.eligible+' eligible for scoring';
   return '<tr><td>'+({train:'Train',valid:'Validation',test:'Test'}[r.split])+'</td><td>'+escapeHTML(r.crop_class)+'</td><td>'+count+'<small>'+eligible+'</small></td>'+metrics.map(v=>'<td>'+v+'</td>').join('')+'</tr>';
  }).join('');
 });
}
document.getElementById('mode').onchange=update;
document.getElementById('population').onchange=update;
document.getElementById('basis').onchange=update;
</script>'''])
    return '\n'.join(parts)


def prepare(training_manifest, validation_manifest, report_path, output, diagnostic_summary=None):
    if output.exists():
        raise FileExistsError(output)
    train = json.loads(training_manifest.read_text())
    valid = json.loads(validation_manifest.read_text())
    report = json.loads(report_path.read_text())
    if train["split"] != "train" or valid["split"] != "valid":
        raise ValueError("Unexpected manifest splits")
    records = []
    for model in report["models"]:
        for mode, key in (("raw", "cells"), ("normalised", "normalised_cells")):
            cells = model["variants"]["baseline"][key]
            for population, title in (("annotation", "Annotation-box crops"), ("prediction", "Detector-predicted validation crops")):
                for split in (("train", "valid", "test") if population == "annotation" else ("valid",)):
                    for field in FIELDS:
                        cell = next(c for c in cells if (c["split"], c["input_set"], c["field"]) == (split, population, field))
                        count = (train["counts"]["gt_"+field] if split == "train" else
                                 valid["counts"][("gt_" if population == "annotation" else "pred_")+field] if split == "valid" else None)
                        status = "Reserved" if split == "test" else "N/A" if field == "front_eds" else cell["status"]
                        if split == "valid" and field != "front_eds" and cell["inventory"] != count:
                            raise ValueError("Saved scoring inventory differs from source counts")
                        record = dict(model=model["id"], scoring_mode=mode, input_set=population,
                                      score_basis="verified", candidate_crops=None,
                                      split=split, crop_class=field, crops=count, status=status,
                                      eligible=cell["eligible"] if split in {"train","valid"} and field != "front_eds" and cell["inventory"] else None,
                                      **{k: cell[k] if status == "Scored" else None for k in ("cer", "wer", "exact_match")})
                        records.append(record)
    if diagnostic_summary is not None:
        with diagnostic_summary.open(newline="") as handle:
            diagnostic_rows = list(csv.DictReader(handle))
        diagnostics = {}
        for row in diagnostic_rows:
            key = (row["model"], row.get("split") or "valid", row["scoring_mode"], row["input_set"], row["field"])
            if key in diagnostics:
                raise ValueError("Duplicate diagnostic cell")
            diagnostics[key] = row
        provisional = []
        subset_counts = {}
        for record in records:
            row = dict(record, score_basis="provisional_ai", eligible=None)
            key = (row["model"],row["split"],row["scoring_mode"],row["input_set"],row["crop_class"])
            if row["split"] in {"train","valid"} and row["crop_class"] != "front_eds" and key in diagnostics:
                source = diagnostics[key]
                count = int(source["candidate_crops"])
                if not 0 < count <= row["crops"] or source["verified_benchmark"].lower() != "false":
                    raise ValueError("Invalid provisional diagnostic count/basis")
                shared_key = (row["split"], row["input_set"], row["crop_class"])
                if subset_counts.setdefault(shared_key, count) != count:
                    raise ValueError("Diagnostic subset counts differ across models/modes")
                row.update(candidate_crops=count, status="Provisional AI-label agreement",
                           cer=float(source["cer_pct"])/100, wer=float(source["wer_pct"])/100,
                           exact_match=float(source["exact_match_pct"])/100)
            provisional.append(row)
        records.extend(provisional)
    output.mkdir(parents=True)
    (output / "tables.html").write_text(render_tables(records, report["models"]), encoding="utf-8")
    with (output / "tables.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    for model in report["models"]:
        with (output / (model["id"] + ".csv")).open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(r for r in records if r["model"] == model["id"])
    (output / "provenance.json").write_text(json.dumps(dict(
        inputs={str(p):digest(p) for p in (training_manifest, validation_manifest, report_path,
                                          *([diagnostic_summary] if diagnostic_summary else []))},
        rows=len(records), visible_model_tables=len(report["models"]), csv_metric_units="fractions; HTML displays percentages",
        reserved_test_accessed=False, panel_metrics="not applicable", screenshot_values_used=False), indent=2)+'\n')
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--validation-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-summary", type=Path,
                        help="Optional separate provisional AI-label metrics; never replaces verified cells")
    args = parser.parse_args()
    print("Table rows:",len(prepare(args.training_manifest, args.validation_manifest, args.report, args.output,
                                   args.diagnostic_summary)))
