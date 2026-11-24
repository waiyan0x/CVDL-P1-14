"""Import submitted A/P labels without altering source crops or guessing text.

Preserves raw CSVs, joins by review ID and audits annotation conventions.
Only extra cells in the final note column are mechanically rejoined.
"""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unicodedata


FIELD_NAMES = {"front_eds_num": "service number", "front_eds_route": "route text",
               "front_eds_destination": "destination"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_csv(path, columns, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def import_labels(workspace, annotations, predictions, output, reviewer, reviewed_at):
    date.fromisoformat(reviewed_at)
    if not reviewer.strip():
        raise ValueError("Reviewer name is required")
    if output.exists():
        raise FileExistsError(f"Choose a new import directory: {output}")
    records, repairs, sources, columns_by_kind = [], [], {}, {}
    for kind, path, expected_count in (("annotation", annotations, 157), ("prediction", predictions, 114)):
        columns, templates = read_csv(workspace / "human_review" / f"{kind}_submission.template.csv")
        columns_by_kind[kind] = columns
        template_by_id = {r["review_id"]: r for r in templates}
        headers, submitted = read_csv(path)
        if not {"id", "field", "text", "quality", "note"}.issubset(headers) or headers[-1] != "note":
            raise ValueError(f"Unexpected submission schema: {path}")
        ids = [r["id"] for r in submitted]
        if len(ids) != expected_count or len(set(ids)) != len(ids) or set(ids) != set(template_by_id):
            raise ValueError(f"Missing, duplicate or unexpected review IDs in {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sources[kind] = {"filename": path.name, "sha256": digest, "rows": len(submitted)}
        for logical_row, raw in enumerate(submitted, 1):
            if any(value is None for key, value in raw.items() if key is not None):
                raise ValueError(f"Missing CSV cells: {path}:{raw['id']}")
            extra = raw.pop(None, [])
            if extra:
                raw["note"] = ",".join([raw["note"]] + extra)
                repairs.append({"review_id": raw["id"], "source_file": path.name,
                                "repair": "Rejoined overflow CSV cells into the final note column; text unchanged"})
            original = template_by_id[raw["id"]]
            row = original.copy()
            row.update(transcription=raw["text"], legibility=raw["quality"], reviewer=reviewer,
                       reviewed_at=reviewed_at, submitted_field=raw["field"],
                       submission_flag=raw.get("flag", ""), source_submission=path.name,
                       source_submission_sha256=digest, source_record_number=logical_row,
                       notes=raw["note"])
            issues = []
            def flag(code, action, severity="resolve"):
                issues.append({"code": code, "severity": severity, "action": action})
            text, legibility = row["transcription"], row["legibility"]
            if raw["field"] != FIELD_NAMES[row["label"]]:
                flag("submitted_field_mismatch", "Verify the field against the crop and supplied class; do not silently relabel")
            if legibility not in {"full", "partial", "illegible"}:
                flag("invalid_legibility", "Use full, partial or illegible; handle blank/absent separately")
            if legibility == "full" and not text.strip():
                flag("full_empty_text", "Provide visible text or correct the state after inspecting the crop")
            if legibility == "full" and "[UNK]" in text:
                flag("full_contains_unknown", "Resolve the unknown span or confirm partial legibility")
            if legibility == "partial" and "[UNK]" not in text:
                flag("partial_missing_unknown", "Mark the actual unresolved/clipped span with [UNK], or confirm that the complete field is full")
            if legibility == "partial" and not text.replace("[UNK]", "").strip():
                flag("partial_no_readable_text", "Confirm whether any glyph is readable; otherwise use illegible")
            if legibility == "illegible" and text != "[UNK]":
                flag("illegible_has_readable_text", "If the visible arrow/text is reliably readable, confirm partial and retain the unknown span; otherwise use exactly [UNK]")
            if any(line != line.strip() or "  " in line or not line or "\t" in line
                   for line in text.split("\n")):
                flag("spacing", "Check word spaces and per-line padding against the transcription conventions")
            if unicodedata.normalize("NFC", text) != text:
                flag("non_nfc", "Normalize storage to Unicode NFC without changing the visible text")
            if "\\n" in text:
                flag("literal_newline_escape", "Use actual newlines in quoted CSV cells")
            if row["label"] == "front_eds_num" and any(c.isspace() for c in text):
                flag("service_identifier_whitespace", "Verify whether spacing or extra lines belong to another field")
            submitted_flag = raw.get("flag", "")
            if submitted_flag == "field_mismatch":
                flag("field_mismatch", "Review the predicted crop's field identity; keep original class and detector error evidence")
            elif submitted_flag == "field_bleed":
                flag("field_bleed", "Decide the intended field and treatment of adjacent text before field-specific scoring; do not silently drop visible text")
            elif submitted_flag == "no_text":
                flag("no_text_state", "Distinguish blank/absent field from visible but unreadable text; the note currently describes unreadability")
            elif submitted_flag not in {"", "ok"}:
                flag("unknown_submission_flag", "Define and review this submission flag")
            row["field_status"] = "" if submitted_flag in {"field_mismatch", "no_text"} else "present"
            row["review_status"] = "needs_resolution" if issues else "reviewed"
            records.append({"kind": kind, "row": row, "issues": issues})

    # Case variants across crops are review candidates, never automatic corrections.
    variants = defaultdict(list)
    for record in records:
        row = record["row"]
        if row["transcription"] and "[UNK]" not in row["transcription"]:
            key = (row["label"], " ".join(row["transcription"].casefold().split()))
            variants[key].append(record)
    for group in variants.values():
        if len({r["row"]["transcription"] for r in group}) > 1:
            ids = ", ".join(r["row"]["review_id"] for r in group)
            for record in group:
                record["issues"].append({"code": "case_variant", "severity": "inspect",
                    "action": f"Compare visible case for {ids}; mixed case may be correct. Do not auto-uppercase"})
                record["row"]["review_status"] = "needs_resolution"

    issues = []
    summary = {}
    for kind in ("annotation", "prediction"):
        selected = [r for r in records if r["kind"] == kind]
        summary[kind] = {
            "rows": len(selected),
            "quality_counts": dict(Counter(r["row"]["legibility"] for r in selected)),
            "field_counts": {label: dict(Counter(r["row"]["legibility"] for r in selected if r["row"]["label"] == label)) for label in FIELD_NAMES},
            "review_status_counts": dict(Counter(r["row"]["review_status"] for r in selected)),
        }
        for record in selected:
            record["row"]["issue_codes"] = ";".join(i["code"] for i in record["issues"])
            for issue in record["issues"]:
                issues.append({"review_id": record["row"]["review_id"], "crop_set": kind,
                               "field": record["row"]["label"], "text": record["row"]["transcription"],
                               "legibility": record["row"]["legibility"], **issue})
    audit = {
        "status": "imported_with_resolution_items", "reviewer": reviewer, "reviewed_at": reviewed_at,
        "review_attestation": "Reviewer/date supplied by user; no independent second review attested",
        "sources": sources, "summary": summary, "mechanical_note_repairs": repairs,
        "issue_counts": dict(Counter(i["code"] for i in issues)),
        "rows_needing_resolution": len({i["review_id"] for i in issues}),
        "missing_group_ids": sum(not r["row"]["group_id"] for r in records),
        "split_counts": dict(Counter(r["row"]["split"] for r in records)),
        "group_leakage_check": "Not assessable: group IDs are unassigned. All imported rows are validation only",
        "scoring_ready_rows": 0,
        "field_patterns": "No closed field regex established; only declared whitespace and legibility syntax checked",
        "text_changes": "None; transcription and supplied quality preserved, including actual newlines",
    }
    report = [
        "# Codi OCR label import", "", f"Reviewer supplied by user: **{reviewer}**. Actual review date: **{reviewed_at}**.",
        "Independent second review has not been attested. This import checks structure and conventions, not visual transcription correctness.", "",
        "| Crop set | Field | Full | Partial | Illegible |", "| --- | --- | ---: | ---: | ---: |",
    ]
    for kind, data in summary.items():
        for label, counts in data["field_counts"].items():
            report.append(f"| {kind} | {FIELD_NAMES[label]} | {counts.get('full', 0)} | {counts.get('partial', 0)} | {counts.get('illegible', 0)} |")
    report += ["", "All 271 expected IDs are present without duplicates. Original text, quality, field labels and crop provenance are retained.",
               "Source CSVs are preserved byte-for-byte in `raw/`. Five overflow note cells are rejoined and quoted in the imported files; no transcription is changed.", "",
               "## Items to resolve", "", f"**{audit['rows_needing_resolution']} distinct rows** need resolution or visual inspection. See `rows_to_resolve.csv` for text, issue and requested action. A row can have multiple issues.", ""]
    for code, count in audit["issue_counts"].items():
        ids = [i["review_id"] for i in issues if i["code"] == code]
        report.append(f"- **{code} ({count}):** {', '.join(ids)}")
    report += ["", "Case variants are candidates for inspection, not proof of incorrect case. Do not auto-uppercase.",
               "A partial label needs the actual unresolved span marked; do not guess its location or reclassify solely because the crop is blurred.",
               "Keep field-bleed and field-mismatch observations separate from character recognition errors. Confirm the intended target before scoring; source classes must not be silently changed.", "",
               "## Remaining scoring prerequisites", "",
               "All 271 group IDs remain unassigned and group review is pending. The imports retain the original `valid` split, so there is no recorded train/test split conflict, but burst/scene leakage cannot be assessed or ruled out.",
               "Predicted-crop correspondence review is also pending. No row is declared scoring-ready and no OCR accuracy has been measured.",
               "No complete field-specific regex or closed alphabet has been established. Checks cover the declared legibility/whitespace conventions, not an invented service/destination grammar.",
               "The earlier `human_review/annotation_jun_yong.draft.csv` is a historical partial submission and is not merged into this new Codi submission. The source templates and preparation audit are unchanged.", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ocr-import-", dir=output.parent) as temporary:
        staging = Path(temporary) / "import"
        staging.mkdir()
        (staging / "raw").mkdir()
        for kind, path in (("annotation", annotations), ("prediction", predictions)):
            (staging / "raw" / path.name).write_bytes(path.read_bytes())
            extra_columns = ["submitted_field", "submission_flag", "source_submission", "source_submission_sha256", "source_record_number", "issue_codes"]
            write_csv(staging / f"{kind}_codi.csv", columns_by_kind[kind] + extra_columns,
                      [r["row"] for r in records if r["kind"] == kind])
        write_csv(staging / "rows_to_resolve.csv",
                  ["review_id", "crop_set", "field", "text", "legibility", "code", "severity", "action"], issues)
        (staging / "import_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        (staging / "README.md").write_text("\n".join(report), encoding="utf-8")
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewed-at", required=True, help="Actual review date YYYY-MM-DD")
    parser.add_argument("--workspace", type=Path, default=Path("evaluation/ocr_annotations/v4-reviewed-01"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = import_labels(args.workspace, args.annotations, args.predictions, args.output, args.reviewer, args.reviewed_at)
    print(json.dumps({k: v for k, v in audit.items() if k in {"summary", "issue_counts", "rows_needing_resolution", "scoring_ready_rows"}}, indent=2))


if __name__ == "__main__":
    main()
