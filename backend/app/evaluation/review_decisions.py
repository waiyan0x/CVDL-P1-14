"""Import explicit human crop-review decisions without promoting training data."""

from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
import unicodedata


DECISION_COLUMNS = (
    "review_id", "crop_sha256", "source_review_sha256", "human_decision",
    "final_transcription", "final_legibility", "final_field_status",
    "human_field_confirmation", "human_crop_treatment", "human_reviewer",
    "human_reviewer_type", "human_reviewed_at", "human_notes",
)
IMMUTABLE = ("crop", "image", "label", "class_id", "annotation_id",
             "source_image_sha256", "box_xyxy", "split", "crop_sha256")
CLASSES = {"front_eds", "front_eds_num", "front_eds_destination", "front_eds_route"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns, rows = reader.fieldnames, list(reader)
    if not columns or len(columns) != len(set(columns)):
        raise ValueError("Missing or duplicate CSV columns")
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed CSV: missing or extra cells")
    ids = [r.get("review_id", "") for r in rows]
    if any(not rid or rid != rid.strip() for rid in ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate review IDs")
    return columns, rows


def load_source(path):
    columns, rows = read_rows(path)
    required = {"review_id", "transcription", "legibility", "field_status", *IMMUTABLE}
    if not required.issubset(columns) or not rows:
        raise ValueError("Source requires full crop-review metadata and at least one row")
    for row in rows:
        if row["label"] not in CLASSES or row["split"] not in {"train", "valid", "val", "test"}:
            raise ValueError(f"Invalid class/split: {row['review_id']}")
        for key in ("crop_sha256", "source_image_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise ValueError(f"Invalid {key}: {row['review_id']}")
        try:
            box = json.loads(row["box_xyxy"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid geometry: {row['review_id']}") from exc
        if (not isinstance(box, list) or len(box) != 4
                or any(type(n) not in {int, float} or not math.isfinite(n) or n < 0 for n in box)
                or box[2] <= box[0] or box[3] <= box[1]):
            raise ValueError(f"Invalid geometry: {row['review_id']}")
    return columns, rows


def write_rows(path, columns, rows):
    with Path(path).open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_template(source, output):
    _, rows = load_source(source)
    source_hash = digest(source)
    decisions = [dict.fromkeys(DECISION_COLUMNS, "") for _ in rows]
    for row, decision in zip(rows, decisions):
        decision.update(review_id=row["review_id"], crop_sha256=row["crop_sha256"],
                        source_review_sha256=source_hash)
    write_rows(output, DECISION_COLUMNS, decisions)
    return len(decisions)


def validate_text(text, legibility, field):
    if field not in {"present", "blank", "absent", "wrong_field"}:
        raise ValueError("Final field status must be present, blank, absent or wrong_field")
    if field in {"blank", "absent"}:
        if text or legibility != "not_applicable":
            raise ValueError("Blank/absent fields require empty text and not_applicable legibility")
        return
    if text != unicodedata.normalize("NFC", text) or "\\n" in text:
        raise ValueError("Use NFC text and actual newlines")
    if (any(not line or line != line.strip() or "  " in line for line in text.split("\n"))
            or any(c.isspace() and c not in {" ", "\n"} for c in text)):
        raise ValueError("Use nonempty lines, one word space and no line padding")
    valid = ((legibility == "full" and text and "[UNK]" not in text)
             or (legibility == "partial" and "[UNK]" in text
                 and text.replace("[UNK]", "").strip())
             or (legibility == "illegible" and text == "[UNK]"))
    if not valid:
        raise ValueError("Text contradicts full/partial/illegible conventions")


def blockers(row):
    reasons = []
    try:
        datetime.fromisoformat(row.get("reviewed_at", "").replace("Z", "+00:00"))
        valid_date = True
    except ValueError:
        valid_date = False
    if (row.get("human_verification_status") != "verified"
            or row.get("reviewer_type") != "human" or row.get("review_status") != "reviewed"
            or not row.get("reviewer", "").strip() or not valid_date):
        reasons.append("human_review_incomplete")
    try:
        validate_text(row.get("transcription", ""), row.get("legibility", ""), row.get("field_status", ""))
    except ValueError:
        reasons.append("text_or_field_conventions_unresolved")
    if row.get("exclusion_reason"):
        reasons.append("explicit_exclusion")
    if row.get("field_status") != "present":
        reasons.append("field_not_confirmed_present")
    if row.get("legibility") != "full" or not row.get("transcription") or "[UNK]" in row.get("transcription", ""):
        reasons.append("text_not_full")
    if row.get("human_field_confirmation") != "confirmed":
        reasons.append("field_confirmation_pending")
    if row.get("human_crop_treatment") != "single_field":
        reasons.append("crop_target_unresolved_or_challenge")
    if not row.get("group_id") or row.get("group_review_status") != "reviewed":
        reasons.append("group_review_pending")
    predicted = row.get("crop_source") in {"prediction", "predicted"} or row["review_id"].startswith("P")
    if predicted and row.get("correspondence_status") not in {
            "same_visible_text", "different_visible_text", "no_match"}:
        reasons.append("correspondence_pending")
    if row["label"] == "front_eds":
        reasons.append("panel_text_protocol_undefined")
    return reasons


def apply_decision(row, decision):
    action = decision["human_decision"]
    if action not in {"accept", "correct", "needs_resolution", "exclude"}:
        raise ValueError("Decision must be accept, correct, needs_resolution or exclude")
    if decision["human_reviewer_type"] != "human" or not decision["human_reviewer"].strip():
        raise ValueError("Explicit human reviewer identity and reviewer_type=human required")
    try:
        datetime.fromisoformat(decision["human_reviewed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Actual ISO review date/time required") from exc
    if not decision["human_notes"].strip():
        raise ValueError("A human decision reason is required")
    confirmation, treatment = (decision[k] for k in ("human_field_confirmation", "human_crop_treatment"))
    if confirmation not in {"confirmed", "needs_resolution"} or treatment not in {
            "single_field", "challenge", "needs_resolution"}:
        raise ValueError("Explicit field confirmation and crop treatment required")
    if action in {"accept", "correct"}:
        for key in ("transcription", "legibility", "field_status"):
            final = decision[f"final_{key}"]
            if action == "accept" and final and final != row[key]:
                raise ValueError("Accept cannot silently discard a conflicting final value; use correct")
            if action == "correct":
                row[key] = final
        validate_text(row["transcription"], row["legibility"], row["field_status"])
        row["review_status"] = "reviewed" if confirmation == "confirmed" else "needs_resolution"
    else:
        if any(decision[f"final_{key}"] for key in ("transcription", "legibility", "field_status")):
            raise ValueError("Unresolved/excluded decisions must not supply unused final labels")
        row["review_status"] = "excluded" if action == "exclude" else "needs_resolution"
    row.update(reviewer=decision["human_reviewer"], reviewer_type="human",
               reviewed_at=decision["human_reviewed_at"], human_notes=decision["human_notes"],
               human_field_confirmation=confirmation, human_crop_treatment=treatment,
               human_verification_status="verified" if action in {"accept", "correct", "exclude"} else "pending")
    row["field_review_status"] = "reviewed" if confirmation == "confirmed" else "needs_resolution"
    if action == "exclude":
        row["exclusion_reason"] = decision["human_notes"]


def import_decisions(source, decisions, output=None, dry_run=False):
    if not dry_run and output is None:
        raise ValueError("Output directory required unless dry-run")
    if output is not None and Path(output).exists():
        raise FileExistsError(f"Refusing existing output: {output}")
    _, originals = load_source(source)
    columns, decisions_rows = read_rows(decisions)
    if not set(DECISION_COLUMNS).issubset(columns):
        raise ValueError("Use a decision template generated by this command")
    source_hash, decisions_hash = digest(source), digest(decisions)
    by_id = {row["review_id"]: row for row in originals}
    updated, changes = {rid: row.copy() for rid, row in by_id.items()}, []
    for decision in decisions_rows:
        rid = decision["review_id"]
        if rid not in by_id:
            raise ValueError(f"Unknown review ID: {rid}")
        if (decision["source_review_sha256"] != source_hash
                or decision["crop_sha256"] != by_id[rid]["crop_sha256"]):
            raise ValueError(f"Source/crop hash mismatch: {rid}")
        if not decision["human_decision"]:
            if any(decision[k] for k in DECISION_COLUMNS[4:]):
                raise ValueError(f"Review values supplied without a decision: {rid}")
            continue
        try:
            apply_decision(updated[rid], decision)
        except ValueError as exc:
            raise ValueError(f"{rid}: {exc}") from exc
        changes.append({"review_id": rid, "decision": decision, "before": by_id[rid], "after": updated[rid].copy()})
    pending, counts = [], Counter()
    for rid, row in updated.items():
        for key in IMMUTABLE:
            if row[key] != by_id[rid][key]:
                raise ValueError(f"Immutable identity changed: {rid}/{key}")
        reasons = blockers(row)
        row.update(scoring_ready=str(not reasons).lower(), training_ready="false",
                   review_blocking_reasons=";".join(reasons))
        if reasons:
            pending.append({"review_id": rid, "blocking_reasons": ";".join(reasons)})
        counts.update(reasons)
    for change in changes:
        change["after"] = updated[change["review_id"]].copy()
    audit = {"schema_version": 1, "source_sha256": source_hash, "decisions_sha256": decisions_hash,
             "rows": len(updated), "decisions_applied": len(changes), "scoring_ready_rows": len(updated)-len(pending),
             "training_ready_rows": 0, "blocker_counts": dict(counts),
             "human_attestation": "Recorded from input; identity and independent inspection not independently verified",
             "dry_run": dry_run, "crop_pixels_accessed": False}
    if not dry_run:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".review-import-", dir=output.parent) as temp:
            staging = Path(temp) / "export"
            staging.mkdir()
            result = list(updated.values())
            keys = list(dict.fromkeys(key for row in result for key in row))
            write_rows(staging / "review.csv", keys, result)
            write_rows(staging / "unresolved.csv", ["review_id", "blocking_reasons"], pending)
            (staging / "audit.json").write_text(json.dumps(audit, indent=2)+"\n")
            (staging / "change_log.json").write_text(json.dumps(changes, indent=2)+"\n")
            if digest(source) != source_hash or digest(decisions) != decisions_hash:
                raise ValueError("Input changed during import")
            if output.exists():
                raise FileExistsError(f"Refusing existing output: {output}")
            staging.rename(output)
    return audit
