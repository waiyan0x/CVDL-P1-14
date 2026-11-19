#!/usr/bin/env python3
"""Build frozen validation layout v4-lines-v3 from v4-lines-v2.

v3 changes only the four validation crops that v2 left unresolved
(A052, A094, P046, P087). Each becomes one full-height line, which is the
automatic proposal for all four and the same fix v2 applied to A095/P034.
Every other entry is copied unchanged. The decision was made from the crop
images alone; no OCR output, label or reference text was used.

Usage: scripts/make_layout_v4_lines_v3.py
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "evaluation/ocr_layouts/v4-lines-v2/manifest.json"
DST_DIR = ROOT / "evaluation/ocr_layouts/v4-lines-v3"
REVIEWED_AT = "2026-11-19"

REASONS = {
    "A052": "v3 fix: one glyph row (service number) with overlapping display-refresh "
            "states in the same row; overlap does not create a second text line.",
    "P046": "v3 fix: detector crop of the same display as A052; one glyph row with "
            "overlapping display-refresh states in the same row.",
    "A094": "v3 fix: one clear text row; the thin lower-edge fragment stays inside the "
            "single full-height line region instead of blocking recognition.",
    "P087": "v3 fix: one clear central text row; clipped upper/lower traces stay inside "
            "the single full-height line region instead of blocking recognition.",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    src = json.loads(SRC.read_text())
    out = copy.deepcopy(src)
    changed = []
    for entry in out["entries"]:
        rid = entry["review_id"]
        if rid not in REASONS:
            continue
        if entry["review_status"] != "unresolved" or entry.get("proposal_line_count") != 1:
            raise SystemExit(f"{rid}: expected an unresolved entry with a one-line proposal")
        w, h = entry["input_width"], entry["input_height"]
        entry.update(
            review_status="accepted",
            separators=[],
            line_quads=[[[0, 0], [w, 0], [w, h], [0, h]]],
            reason=REASONS[rid],
            reviewer="Claude",
            reviewer_type="AI",
            reviewed_at=REVIEWED_AT,
            independent_human_review=False,
            changed_from_proposal=False,
            line_count=1,
        )
        changed.append(rid)
    if sorted(changed) != sorted(REASONS):
        raise SystemExit(f"Changed {changed}, expected {sorted(REASONS)}")

    entries = out["entries"]
    out["version"] = "v4-lines-v3"
    out["summary"] = dict(
        out["summary"],
        accepted=sum(e["review_status"] == "accepted" for e in entries),
        unresolved=sum(e["review_status"] == "unresolved" for e in entries),
        line_regions=sum(len(e["line_quads"]) for e in entries),
        changed_from_proposal=sum(bool(e.get("changed_from_proposal")) for e in entries),
    )
    out["supersedes"] = {
        "version": "v4-lines-v2",
        "sha256": sha256(SRC),
        "changed_entries": sorted(changed),
        "reason": "Unresolved validation crops whose image shows one main text row "
                  "(A052/P046 refresh overlap, A094 edge fragment, P087 clipped "
                  "traces) set to one full-height line each, matching the automatic proposal "
                  "and the v2 fix for A095/P034; all other entries unchanged.",
        "previous": src.get("supersedes"),
    }

    DST_DIR.mkdir(parents=True, exist_ok=True)
    dst = DST_DIR / "manifest.json"
    dst.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    (DST_DIR / "manifest.sha256").write_text(f"{sha256(dst)}  manifest.json\n")
    print(f"Wrote {dst}: changed {sorted(changed)}; summary {out['summary']}")


if __name__ == "__main__":
    main()
