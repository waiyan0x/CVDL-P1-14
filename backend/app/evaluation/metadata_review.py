"""Hash-bound metadata adjudication, preserving text provenance and exclusions."""

from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile

from .crop_scoring import canonical_text, set_eligibility
from .review_decisions import (
    DECISION_COLUMNS, IMMUTABLE, apply_decision, create_template, digest,
    import_decisions, load_source, read_rows, write_rows,
)


HUMAN = ("human_reviewer", "human_reviewer_type", "human_reviewed_at", "human_notes")
PAIR_IDENTITY = ("prediction_id", "prediction_class", "prediction_crop",
                 "source_image", "crop_sha256", "source_review_sha256")
GROUP_IDENTITY = ("split", "image", "source_name", "source_image_sha256", "family_id")


def table(path, keys):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns, rows = reader.fieldnames, list(reader)
    if (not columns or len(columns) != len(set(columns)) or not set(keys) <= set(columns)
            or any(None in r or any(v is None for v in r.values()) for r in rows)):
        raise ValueError(f"Malformed metadata CSV: {path}")
    ids = [tuple(r[k] for k in keys) for r in rows]
    if any(any(not k or k != k.strip() for k in rid) for rid in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Missing or duplicate identity: {path}")
    return rows


def note_exclusion(row, reason):
    row["exclusion_reason"] = "; ".join(dict.fromkeys(filter(None, [row.get("exclusion_reason"), reason])))


def attest(row, binding):
    if row.get("source_bundle_sha256") != binding:
        raise ValueError("Source bundle hash mismatch; review a fresh metadata template")
    if row.get("human_reviewer_type") != "human" or not row.get("human_reviewer", "").strip():
        raise ValueError("Explicit human metadata reviewer identity/type required")
    if not row.get("human_notes", "").strip():
        raise ValueError("Metadata decision reason required")
    try:
        datetime.fromisoformat(row.get("human_reviewed_at", "").replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Actual metadata review date required") from exc


def blank_action(row, action_fields, value_fields=()):
    actions = {row.get(k, "") for k in action_fields} - {""}
    if len(actions) > 1:
        raise ValueError("Conflicting human/final metadata decisions")
    action = next(iter(actions), "")
    if not action and any(row.get(k, "") for k in (*HUMAN, *value_fields)):
        raise ValueError("Human metadata supplied without a decision")
    return action


class ReviewBundle:
    def __init__(self, reviews, policies, group_source, pair_source, registry, source_policy=None):
        self.reviews = [Path(p) for p in reviews]
        self.inputs = list(dict.fromkeys([*self.reviews, *map(Path, policies),
                                         Path(group_source), Path(pair_source), Path(registry),
                                         *([Path(source_policy)] if source_policy else [])]))
        self.hashes = {str(p): digest(p) for p in self.inputs}
        self.binding = hashlib.sha256(json.dumps(self.hashes, sort_keys=True).encode()).hexdigest()
        self.originals, self.rows = {}, {}
        for path in self.reviews:
            _, rows = load_source(path)
            for row in rows:
                if row["split"] not in {"train", "valid"} or row["review_id"] in self.rows:
                    raise ValueError("Only unique train/valid review identities are permitted")
                self.originals[row["review_id"]] = dict(row)
                self.rows[row["review_id"]] = dict(row)
        for path in policies:
            for policy in load_source(path)[1]:
                row = self.rows.get(policy["review_id"])
                if row is None or any(row[k] != policy[k] for k in IMMUTABLE):
                    raise ValueError("Policy snapshot identity mismatch")
                # Only exclusions are overlaid: policy snapshots cannot attest human review.
                if policy.get("exclusion_reason"):
                    note_exclusion(row, policy["exclusion_reason"])
        self.groups = table(group_source, ("split", "image"))
        self.pairs = table(pair_source, ("prediction_id",))
        self.registry = table(registry, ("split", "image"))
        self.sources = {(r["split"], r["image"]): r for r in self.groups}
        self.source_policy = {}
        if source_policy:
            for policy in table(source_policy, ("split", "image")):
                key = (policy["split"], policy["image"])
                source = self.sources.get(key)
                if source is None or any(policy.get(k) != source.get(k) for k in GROUP_IDENTITY):
                    raise ValueError("Source policy identity mismatch")
                treatment = policy.get("benchmark_split_treatment", "")
                if treatment not in {"exclude_unverified_cross_split_scene", "unchanged_pending_review"}:
                    raise ValueError("Unknown source policy disposition")
                if treatment == "exclude_unverified_cross_split_scene":
                    if not policy.get("benchmark_split_treatment_basis", "").strip():
                        raise ValueError("Source policy exclusion requires a reason")
                    self.source_policy[key] = policy["benchmark_split_treatment_basis"]
        registry_by_id = {(r["split"], r["image"]): r for r in self.registry}
        for key, source in self.sources.items():
            reg = registry_by_id.get(key)
            if (reg is None or source["source_image_sha256"] != reg["declared_sha256"]
                    or source["source_name"] != reg["source_name"]):
                raise ValueError("Source inventory differs from split registry")
        for row in self.rows.values():
            source = self.sources.get((row["split"], row["image"]))
            if source is None or row["source_image_sha256"] != source["source_image_sha256"]:
                raise ValueError("Crop source absent from metadata inventory")
            policy = self.source_policy.get((row["split"], row["image"]))
            if policy and policy not in row.get("exclusion_reason", ""):
                note_exclusion(row, policy)
        self.seed_rows = {rid: dict(row) for rid, row in self.rows.items()}

    def unchanged(self):
        if any(digest(p) != h for p, h in self.hashes.items()):
            raise ValueError("Input changed during metadata operation")

    def prepare(self, output):
        output = Path(output)
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent) as temp:
            stage = Path(temp) / "templates"
            stage.mkdir()
            for path in self.reviews:
                split = load_source(path)[1][0]["split"]
                create_template(path, stage / f"{split}.text.decisions.csv")
            for name, original in (("photo_group_decisions.csv", self.groups),
                                    ("crop_pairing_decisions.csv", self.pairs)):
                rows = []
                for source in original:
                    row = dict(source)
                    row.update(source_bundle_sha256=self.binding, **dict.fromkeys(HUMAN, ""))
                    if name.startswith("photo"):
                        row.update(human_group_id="", human_group_decision="",
                                   final_photo_group="", final_group_decision="")
                    else:
                        row.update(human_correspondence="", final_pairing_decision="")
                        if float(row["iou"]) == 0:
                            row.update(annotation_id="", annotation_crop="", annotation_crop_sha256="")
                    rows.append(row)
                write_rows(stage / name, list(rows[0]), rows)
            (stage / "bindings.json").write_text(json.dumps(self.hashes, indent=2) + "\n")
            self.unchanged()
            stage.rename(output)

    def apply(self, group_decisions, pair_decisions, output, text_decisions=(), dry_run=False):
        self.rows = {rid: dict(row) for rid, row in self.seed_rows.items()}
        output = Path(output)
        if output.exists():
            raise FileExistsError(output)
        decision_paths = [Path(group_decisions), Path(pair_decisions), *map(Path, text_decisions)]
        decision_hashes = {str(p): digest(p) for p in decision_paths}
        changes = []
        # Text decisions remain bound to their original review, never the policy overlay.
        seen = set()
        for path in text_decisions:
            _, decisions = read_rows(path)
            bindings = {r.get("source_review_sha256") for r in decisions}
            candidates = [p for p in self.reviews if digest(p) in bindings]
            if len(candidates) != 1 or bindings != {digest(candidates[0])}:
                raise ValueError("Text decisions do not bind exactly one original source")
            import_decisions(candidates[0], path, dry_run=True)
            for decision in decisions:
                rid = decision["review_id"]
                if rid in seen:
                    raise ValueError("Duplicate text decision across submissions")
                seen.add(rid)
                if decision["human_decision"]:
                    row = self.rows[rid]
                    previous = row.get("exclusion_reason", "")
                    apply_decision(row, decision)
                    if previous:
                        note_exclusion(row, previous)
                    changes.append({"kind": "text", "id": rid, "decision": decision})
        # Canonical source groups, including sources without text crops.
        assignments = {k: dict(v, accepted_group="", decision="") for k, v in self.sources.items()}
        for decision in table(group_decisions, ("split", "image")):
            key = (decision["split"], decision["image"])
            source = self.sources.get(key)
            if source is None or any(decision.get(k) != source.get(k) for k in GROUP_IDENTITY):
                raise ValueError("Group source identity/hash mismatch")
            action = blank_action(decision, ("human_group_decision", "final_group_decision"),
                                  ("human_group_id", "final_photo_group"))
            if not action:
                continue
            attest(decision, self.binding)
            if action not in {"confirm", "exclude", "needs_resolution"}:
                raise ValueError("Group decision must be confirm, exclude or needs_resolution")
            ids = {decision.get(k, "") for k in ("human_group_id", "final_photo_group")} - {""}
            if len(ids) > 1 or (action == "confirm" and not ids):
                raise ValueError("Confirmed group needs one consistent final group ID")
            gid = next(iter(ids), "")
            if gid != gid.strip():
                raise ValueError("Group ID has padding")
            assignments[key].update(accepted_group=gid, decision=action,
                                    group_review_status="reviewed" if action == "confirm" else "needs_resolution",
                                    **{k: decision[k] for k in HUMAN})
            for row in self.rows.values():
                if (row["split"], row["image"]) == key:
                    row.update(group_review_status="reviewed" if action == "confirm" else "needs_resolution",
                               **{f"group_{k}": decision[k] for k in HUMAN})
                    if action == "confirm":
                        row["group_id"] = gid
                    if action == "exclude":
                        note_exclusion(row, "Human source exclusion: " + decision["human_notes"])
            changes.append({"kind": "group", "id": key, "decision": decision})
        # Known source families and exact duplicates cannot be split into conflicting groups.
        identifiers = defaultdict(set)
        memberships = defaultdict(set)
        for source in assignments.values():
            if source["decision"] != "confirm":
                continue
            gid = source["accepted_group"]
            for key in ("source_name", "source_image_sha256"):
                identifiers[(key, source[key])].add(gid)
            memberships[gid].add(source["split"])
            for reg in self.registry:
                if (reg["source_name"] == source["source_name"]
                        or reg["declared_sha256"] == source["source_image_sha256"]):
                    memberships[gid].add(reg["split"])
        if any(len(ids) > 1 for ids in identifiers.values()):
            raise ValueError("Conflicting groups for the same source family/hash")
        cross = {gid for gid, splits in memberships.items() if len(splits) > 1}
        for row in self.rows.values():
            if row.get("group_id") in cross:
                note_exclusion(row, "Cross-split source group: " + row["group_id"])
        for source in assignments.values():
            policy = self.source_policy.get((source["split"], source["image"]))
            source["policy_exclusion_reason"] = policy or ""
            source["split_treatment"] = (
                "excluded_by_existing_policy" if policy else
                "excluded_cross_split_group" if source["accepted_group"] in cross else
                "excluded_by_reviewer" if source["decision"] == "exclude" else
                "reviewed_within_supplied_registry" if source["decision"] == "confirm" else "pending")
        pair_by_id = {r["prediction_id"]: r for r in self.pairs}
        for decision in table(pair_decisions, ("prediction_id",)):
            rid = decision["prediction_id"]
            reference = pair_by_id.get(rid)
            row = self.rows.get(rid)
            if (reference is None or row is None
                    or any(decision.get(k) != reference.get(k) for k in PAIR_IDENTITY)
                    or row["crop_sha256"] != decision["crop_sha256"]
                    or row["image"] != decision["source_image"]):
                raise ValueError("Pair source identity/hash mismatch")
            action = blank_action(decision, ("human_correspondence", "final_pairing_decision"))
            if not action:
                continue
            attest(decision, self.binding)
            if action not in {"same_visible_text", "different_visible_text", "no_match", "needs_resolution", "exclude"}:
                raise ValueError("Unknown correspondence decision")
            target = decision.get("annotation_id", "")
            if action == "no_match":
                if any(decision.get(k) for k in ("annotation_id", "annotation_crop", "annotation_crop_sha256")):
                    raise ValueError("no_match must have no accepted annotation target")
            elif action in {"same_visible_text", "different_visible_text"}:
                annotation = self.rows.get(target)
                if (annotation is None or annotation.get("crop_source") not in {"annotation", ""}
                        or not target.startswith("A") or annotation["image"] != row["image"]
                        or annotation["split"] != row["split"]
                        or annotation["source_image_sha256"] != row["source_image_sha256"]
                        or annotation["crop_sha256"] != decision.get("annotation_crop_sha256")
                        or annotation["crop"] != decision.get("annotation_crop")):
                    raise ValueError("Pair annotation identity/hash/image mismatch")
                a, b = json.loads(row["box_xyxy"]), json.loads(annotation["box_xyxy"])
                if min(a[2], b[2]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(a[1], b[1]):
                    raise ValueError("Accepted pair must overlap geometrically")
                if (action == "same_visible_text" and all(
                        r.get("human_verification_status") == "verified" and r.get("legibility") == "full"
                        for r in (row, annotation))
                        and canonical_text(row["transcription"]) != canonical_text(annotation["transcription"])):
                    raise ValueError("same_visible_text conflicts with verified transcriptions")
            row.update(correspondence_status=action if action not in {"exclude", "needs_resolution"} else "pending",
                       reviewed_annotation_id=target if action in {"same_visible_text", "different_visible_text"} else "",
                       **{f"correspondence_{k}": decision[k] for k in HUMAN})
            if action == "exclude":
                note_exclusion(row, "Human correspondence exclusion: " + decision["human_notes"])
            changes.append({"kind": "pairing", "id": rid, "decision": decision})
        rows = list(self.rows.values())
        set_eligibility(rows)
        for row in rows:
            original = self.originals[row["review_id"]]
            if any(row[k] != original[k] for k in IMMUTABLE):
                raise ValueError("Immutable crop metadata changed")
            row.update(scoring_ready=str(row["scoring_eligible"]).lower(), training_ready="false",
                       review_blocking_reasons=";".join(row["scoring_blockers"]))
        audit = {"input_sha256": self.hashes, "decision_sha256": decision_hashes,
                 "source_bundle_sha256": self.binding, "rows": len(rows),
                 "decisions_applied": dict(Counter(c["kind"] for c in changes)),
                 "validation_eligible": sum(r["scoring_eligible"] for r in rows if r["split"] == "valid"),
                 "validation_excluded": sum(bool(r.get("exclusion_reason")) for r in rows if r["split"] == "valid"),
                 "cross_split_groups": sorted(cross), "training_ready_rows": 0,
                 "source_photos_excluded_by_policy": len(self.source_policy),
                 "validation_blockers": dict(Counter(b for r in rows if r["split"] == "valid" for b in r["scoring_blockers"])),
                 "dry_run": dry_run, "image_pixels_accessed": False,
                 "limits": ["Human attestations recorded as supplied, not independently authenticated.",
                            "Split checks cover supplied groups and registry exact-name/hash links; unknown related scenes and historical model lineage remain outside this check."]}
        self.unchanged()
        if any(digest(p) != h for p, h in decision_hashes.items()):
            raise ValueError("Decision file changed during import")
        if not dry_run:
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output.parent) as temp:
                stage = Path(temp) / "export"
                stage.mkdir()
                for split in ("train", "valid"):
                    subset = [r for r in rows if r["split"] == split]
                    if subset:
                        columns = list(dict.fromkeys(k for r in subset for k in r))
                        write_rows(stage / f"{split}.review.csv", columns, subset)
                pending = [{"review_id": r["review_id"], "split": r["split"], "blocking_reasons": r["review_blocking_reasons"]}
                           for r in rows if not r["scoring_eligible"]]
                write_rows(stage / "unresolved.csv", ["review_id", "split", "blocking_reasons"], pending)
                group_rows = list(assignments.values())
                write_rows(stage / "source_groups.csv", list(dict.fromkeys(k for r in group_rows for k in r)), group_rows)
                (stage / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
                (stage / "change_log.json").write_text(json.dumps(changes, indent=2) + "\n")
                self.unchanged()
                if any(digest(p) != h for p, h in decision_hashes.items()):
                    raise ValueError("Decision file changed during publication")
                if output.exists():
                    raise FileExistsError(output)
                stage.rename(output)
        return audit
