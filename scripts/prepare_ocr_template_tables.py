"""Render the requested six-column layout using measured data or explicit statuses."""

import argparse
import csv
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.review_decisions import digest

FIELDS = ("front_eds", "front_eds_destination", "front_eds_route", "front_eds_num")


def prepare(training_manifest, validation_manifest, report_path, output):
    if output.exists():
        raise FileExistsError(output)
    train = json.loads(training_manifest.read_text())
    valid = json.loads(validation_manifest.read_text())
    report = json.loads(report_path.read_text())
    if train["split"] != "train" or valid["split"] != "valid":
        raise ValueError("Unexpected manifest splits")
    parts = ['<!doctype html><meta charset="utf-8"><title>OCR results tables</title>',
             '<style>body{background:#080e09;color:#b7edc9;font:15px ui-monospace,monospace;margin:30px}'
             'section{background:#132018;border:1px solid #344739;border-radius:24px;padding:26px;margin:24px 0}'
             'table{border-collapse:collapse;width:100%;margin-bottom:24px}th,td{padding:16px 10px;border-bottom:1px solid #28392c;text-align:right}'
             'th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}'
             'p{line-height:1.6}h3{margin-top:30px}.scroll{overflow-x:auto}</style>',
             '<h1>OCR results — 13 November 2026</h1>'
             '<p>Pretrained baselines. Crops (n) means available crop inventory, not the scoring denominator. '
             'Current validation eligible count: 0. Raw and normalised scores are shown separately. '
             'Pending accuracy is not zero accuracy. No screenshot example values were used.</p>'
             '<p>Not run = no saved run for that population. Review pending = saved predictions exist but no eligible truth. '
             'Reserved = test not evaluated and crop count not asserted. N/A = panel context has no whole-panel transcription/scoring protocol. '
             'Class names follow source manifests; front_eds_num is service number, front_eds_route is separate route/road text.</p>']
    records = []
    for model in report["models"]:
        parts.append('<section><h2>'+escape(model["name"])+'</h2>')
        for mode, key in (("raw", "cells"), ("normalised", "normalised_cells")):
            cells = model["variants"]["baseline"][key]
            for population, title in (("annotation", "Annotation-box crops"), ("prediction", "Detector-predicted validation crops")):
                parts.append('<h3>'+escape(mode.title()+' — '+title)+'</h3><div class="scroll"><table><tr>'+
                             ''.join('<th>'+s+'</th>' for s in ['Split', 'Crop class', 'Crops (n)', 'CER (%) ↓', 'WER (%) ↓', 'Exact match (%) ↑'])+'</tr>')
                for split in (("train", "valid", "test") if population == "annotation" else ("valid",)):
                    for field in FIELDS:
                        cell = next(c for c in cells if (c["split"], c["input_set"], c["field"]) == (split, population, field))
                        count = (train["counts"]["gt_"+field] if split == "train" else
                                 valid["counts"][("gt_" if population == "annotation" else "pred_")+field] if split == "valid" else None)
                        status = "Reserved" if split == "test" else "N/A" if field == "front_eds" else cell["status"]
                        if split == "valid" and field != "front_eds" and cell["inventory"] != count:
                            raise ValueError("Saved scoring inventory differs from source counts")
                        record = dict(model=model["id"], scoring_mode=mode, input_set=population,
                                      split=split, crop_class=field, crops=count, status=status,
                                      eligible=cell["eligible"] if split == "valid" and field != "front_eds" else None,
                                      **{k: cell[k] if status == "Scored" else None for k in ("cer", "wer", "exact_match")})
                        records.append(record)
                        metrics = [f'{100*record[k]:.2f}' if record[k] is not None else status
                                   for k in ("cer", "wer", "exact_match")]
                        values = [{"train":"Train", "valid":"Validation", "test":"Test"}[split], field,
                                  count if count is not None else "Reserved", *metrics]
                        parts.append('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in values)+'</tr>')
                parts.append('</table></div>')
        parts.append('</section>')
    output.mkdir(parents=True)
    (output / "tables.html").write_text('\n'.join(parts), encoding="utf-8")
    with (output / "tables.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (output / "provenance.json").write_text(json.dumps(dict(
        inputs={str(p):digest(p) for p in (training_manifest, validation_manifest, report_path)},
        rows=len(records), csv_metric_units="fractions; HTML displays percentages",
        reserved_test_accessed=False, panel_metrics="not applicable", screenshot_values_used=False), indent=2)+'\n')
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--validation-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print("Table rows:",len(prepare(args.training_manifest, args.validation_manifest, args.report, args.output)))
