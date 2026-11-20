"""Evaluate reference matching on Cody's fine-tuned PaddleOCR readings.

1. Every setting in the grid (scorer x cutoff x margin) is scored on VALIDATION.
2. One setting is chosen on validation by the rule in choose_setting().
3. TEST is run once with that frozen setting.

Gold service = human number label. Gold destination = answer key
(confirmed_endpoint, or the draft proposal until a person confirms it).

    python scripts/evaluate_reference_matching.py
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.reference_matching import (  # noqa: E402
    SCORERS, DisplayMatcher, Reference, Settings, normalise_place, normalise_service)

OUT = ROOT / "evaluation/reference_matching"
CUTOFFS = [25, 50, 60, 70, 75, 80, 90]
MARGINS = [0, 5, 10]
CONFLICT = ["withhold_both", "keep_number"]
ROUTE_FALLBACK = ["off", "check", "use"]


def read_displays(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_key(path, reference):
    """answer_key.csv (endpoint, confirmed_by) or the draft (confirmed_endpoint / proposed_endpoint)."""
    key, reviewers = {}, Counter()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if "endpoint" in row:
                endpoint, who = row["endpoint"].strip(), row.get("confirmed_by", "").strip() or "unrecorded"
            else:
                endpoint = row["confirmed_endpoint"].strip() or row["proposed_endpoint"].strip()
                who = "person" if row["confirmed_endpoint"].strip() else "draft only"
            reviewers[who] += 1
            key[(row["gold_number"], normalise_place(row["destination_label"], reference.abbreviations))] = endpoint
    return key, reviewers


def ocr_text(field):
    if field is None:
        return None
    return (field["raw"] or "") if field["ocr_status"] == "success" else ""


def gold(display, key, reference):
    number = display["fields"].get("number")
    g_number = normalise_service(number["label_text"]) if number and number["label_usable"] else None
    dest = display["fields"].get("destination")
    g_dest = None
    if dest and dest["label_usable"]:
        g_dest = key.get((g_number or "", normalise_place(dest["label_text"], reference.abbreviations)))
        if g_dest in ("NONE", ""):
            g_dest = None
    return g_number, g_dest


def same_place(a, b, reference):
    return a is not None and b is not None and \
        normalise_place(a, reference.abbreviations, display=False) == normalise_place(b, reference.abbreviations, display=False)


def evaluate(displays, matcher, key, reference):
    rows, m = [], Counter()
    for d in displays:
        f = d["fields"]
        result = matcher.match(number=ocr_text(f.get("number")), destination=ocr_text(f.get("destination")),
                               route=ocr_text(f.get("route")), panel=(d["panel"] or {}).get("raw"))
        g_number, g_dest = gold(d, key, reference)
        raw_number = normalise_service(ocr_text(f.get("number")) or "")
        out_number = result["service"]
        if g_number:
            m["svc_gold"] += 1
            in_ref = reference.has_service(g_number)
            m["svc_gold_not_in_reference"] += not in_ref
            raw_ok, out_ok = raw_number == g_number, out_number == g_number
            m["svc_raw_correct"] += raw_ok
            m["svc_shown"] += out_number is not None
            m["svc_correct"] += out_ok
            m["svc_wrong"] += out_number is not None and not out_ok
            m["svc_withheld"] += out_number is None
            m["svc_withheld_correctly"] += out_number is None and not in_ref
            m["svc_rescued"] += out_ok and not raw_ok
            m["svc_harmful"] += raw_ok and out_number is not None and not out_ok
            m["svc_valid_but_wrong_read"] += bool(raw_number) and raw_number != g_number and reference.has_service(raw_number)
        out_dest = result["destination"]
        dest_field = f.get("destination")
        if g_dest == "NOT_IN_SERVICE":
            m["dest_gold_not_in_service"] += 1
            m["dest_not_in_service_caught"] += result["status"] == "not_in_service"
        elif g_dest:
            m["dest_gold"] += 1
            raw_ok = dest_field is not None and normalise_place(ocr_text(dest_field), reference.abbreviations) == \
                normalise_place(dest_field["label_text"], reference.abbreviations)
            out_ok = same_place(out_dest, g_dest, reference)
            m["dest_raw_correct"] += raw_ok
            m["dest_shown"] += out_dest is not None
            m["dest_correct"] += out_ok
            m["dest_wrong"] += out_dest is not None and not out_ok
            m["dest_withheld"] += out_dest is None
            m["dest_rescued"] += out_ok and not raw_ok
            m["dest_harmful"] += raw_ok and out_dest is not None and not out_ok
        m[f"status_{result['status']}"] += 1
        m["displays"] += 1
        rows.append({"display_key": d["display_key"], "status": result["status"], "reason": result["reason"],
                     "gold_number": g_number, "raw_number": ocr_text(f.get("number")), "matched_number": out_number,
                     "service_status": result["service_status"], "gold_destination": g_dest,
                     "raw_destination": ocr_text(dest_field), "matched_destination": out_dest,
                     "destination_status": result["destination_status"], "similarity": result["destination_score"],
                     "runner_up": result["runner_up"], "runner_up_similarity": result["runner_up_score"],
                     "raw_route": ocr_text(f.get("route")), "raw_panel": (d["panel"] or {}).get("raw"),
                     "sources": json.dumps(result["sources"]), "log": " | ".join(result["log"])})
    return m, rows


def summary(m):
    shown = m["svc_shown"] + m["dest_shown"]
    wrong = m["svc_wrong"] + m["dest_wrong"]
    return {"net_correct": m["svc_correct"] + m["dest_correct"] - wrong,
            "shown_precision": round(100 * (shown - wrong) / shown, 1) if shown else None,
            "svc_correct": m["svc_correct"], "svc_wrong": m["svc_wrong"],
            "dest_correct": m["dest_correct"], "dest_wrong": m["dest_wrong"], "dest_withheld": m["dest_withheld"],
            "dest_gold": m["dest_gold"], "svc_gold": m["svc_gold"]}


# Project decision (20 Nov 2026): try the route crop as the destination when no destination crop exists.
# Validation cannot measure it (scored destinations always have a destination crop) and showed no harm.
ROUTE_ALLOWED = ("check", "use")


def choose_setting(grid):
    """Most correct outputs minus wrong outputs; then higher precision; then stricter cutoff/margin."""
    grid = [g for g in grid if g["route_as_destination"] in ROUTE_ALLOWED]
    return max(grid, key=lambda g: (g["net_correct"], g["shown_precision"] or 0, g["cutoff"], g["margin"],
                                    g["conflict"] == "withhold_both", g["route_as_destination"] == "check"))


def pct(a, b):
    return f"{100 * a / b:.1f}% ({a}/{b})" if b else "n/a"


def table(groups):
    lines = ["| Measure | " + " | ".join(groups) + " |", "| --- |" + " ---: |" * len(groups)]
    def row(name, fn):
        lines.append(f"| {name} | " + " | ".join(fn(m) for m in groups.values()) + " |")
    row("Displays", lambda m: str(m["displays"]))
    row("Service: displays with a readable label", lambda m: str(m["svc_gold"]))
    row("Service: raw OCR exact", lambda m: pct(m["svc_raw_correct"], m["svc_gold"]))
    row("Service: shown and correct", lambda m: pct(m["svc_correct"], m["svc_gold"]))
    row("Service: shown but wrong", lambda m: str(m["svc_wrong"]))
    row("Service: withheld", lambda m: str(m["svc_withheld"]))
    row("Service: label not in reference (withheld = correct)", lambda m: f"{m['svc_withheld_correctly']}/{m['svc_gold_not_in_reference']}")
    row("Service: misread as another real service", lambda m: str(m["svc_valid_but_wrong_read"]))
    row("Service: rescued / harmful", lambda m: f"{m['svc_rescued']} / {m['svc_harmful']}")
    row("Destination: displays with an answer-key entry", lambda m: str(m["dest_gold"]))
    row("Destination: raw OCR exact (vs sign text)", lambda m: pct(m["dest_raw_correct"], m["dest_gold"]))
    row("Destination: shown and correct", lambda m: pct(m["dest_correct"], m["dest_gold"]))
    row("Destination: shown but wrong", lambda m: str(m["dest_wrong"]))
    row("Destination: withheld", lambda m: str(m["dest_withheld"]))
    row("Destination: rescued / harmful", lambda m: f"{m['dest_rescued']} / {m['dest_harmful']}")
    row("Depot / not-in-service caught", lambda m: f"{m['dest_not_in_service_caught']}/{m['dest_gold_not_in_service']}")
    return "\n".join(lines)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--displays", type=Path, default=OUT / "displays.jsonl")
    parser.add_argument("--key", type=Path, default=OUT / "answer_key.csv" if (OUT / "answer_key.csv").is_file()
                        else OUT / "answer_key.draft.csv")
    parser.add_argument("--reference", type=Path, default=ROOT / "data/reference/bus_information.cleaned.csv")
    args = parser.parse_args(argv)
    reference = Reference(args.reference)
    key, reviewers = load_key(args.key, reference)
    displays = read_displays(args.displays)
    valid = [d for d in displays if d["split"] == "valid"]
    test = [d for d in displays if d["split"] == "test"]

    grid = []
    for scorer, cutoff, margin, conflict, route_fb in itertools.product(SCORERS, CUTOFFS, MARGINS, CONFLICT, ROUTE_FALLBACK):
        m, _ = evaluate(valid, DisplayMatcher(reference, Settings(cutoff, margin, scorer, conflict, route_fb)), key, reference)
        grid.append({"scorer": scorer, "cutoff": cutoff, "margin": margin, "conflict": conflict,
                     "route_as_destination": route_fb, **summary(m)})
    (OUT / "results").mkdir(exist_ok=True)
    write_csv(OUT / "results/validation_grid.csv", grid)
    best = choose_setting(grid)
    settings = Settings(best["cutoff"], best["margin"], best["scorer"], best["conflict"], best["route_as_destination"])
    matcher = DisplayMatcher(reference, settings)

    groups, all_rows = {}, {}
    for name, subset in [("valid/annotation", [d for d in valid if d["crop_set"] == "annotation"]),
                         ("valid/prediction", [d for d in valid if d["crop_set"] == "prediction"]),
                         ("test/annotation", test)]:
        groups[name], all_rows[name] = evaluate(subset, matcher, key, reference)
    write_csv(OUT / "results/per_display_validation.csv", all_rows["valid/annotation"] + all_rows["valid/prediction"])
    write_csv(OUT / "results/per_display_test.csv", all_rows["test/annotation"])

    focus = [g for g in grid if g["cutoff"] in (25, 50, 75) and g["margin"] == best["margin"]
             and g["scorer"] == best["scorer"] and g["conflict"] == best["conflict"]
             and g["route_as_destination"] == best["route_as_destination"]]
    route_cmp = [max((g for g in grid if g["route_as_destination"] == v), key=lambda g: (g["net_correct"], g["shown_precision"] or 0)) for v in ROUTE_FALLBACK]
    policy = [max((g for g in grid if g["conflict"] == c), key=lambda g: (g["net_correct"], g["shown_precision"] or 0)) for c in CONFLICT]
    by_scorer = [max((g for g in grid if g["scorer"] == s), key=lambda g: (g["net_correct"], g["shown_precision"] or 0)) for s in SCORERS]
    key_note = f"`{args.key.relative_to(ROOT)}`, {len(key)} entries; reviewed by: " + ", ".join(
        f"{who} ({n})" for who, n in reviewers.items())
    md = [
        "# Reference matching results",
        "",
        f"OCR input: Cody's fine-tuned PaddleOCR (`20261117-031848`) readings from the OCR branch "
        f"(validation layout v2). Reference: `{args.reference.relative_to(ROOT)}`. Destination gold: {key_note}.",
        "",
        "## Selected setting (chosen on validation only)",
        "",
        f"**Scorer `{best['scorer']}`, cutoff {best['cutoff']}, margin {best['margin']}, conflict policy `{best['conflict']}`, "
        f"route crop fallback `{best['route_as_destination']}`.** "
        "The route crop fallback is required by project decision (`check` or `use`, never `off`); `check` wins ties. "
        "Other settings: most correct outputs minus wrong outputs (services + destinations) on validation; "
        "ties go to higher precision, then the stricter cutoff and margin. Test was run once with this setting.",
        "",
        "## Results with the selected setting",
        "",
        "Raw OCR exact = OCR text equals the human label. Shown = the matcher outputs a value (the app would display it). "
        "Rescued = raw OCR wrong but matched output correct. Harmful = raw OCR right but matched output wrong.",
        "",
        table(groups),
        "",
        "## Your 25 / 50 / 75 cutoffs (validation, same scorer and margin)",
        "",
        "| Cutoff | Net correct | Shown precision | Service correct / wrong | Destination correct / wrong / withheld |",
        "| ---: | ---: | ---: | ---: | ---: |",
        *[f"| {g['cutoff']} | {g['net_correct']} | {g['shown_precision']}% | {g['svc_correct']} / {g['svc_wrong']} | "
          f"{g['dest_correct']} / {g['dest_wrong']} / {g['dest_withheld']} |" for g in focus],
        "",
        "## Best setting per similarity measure (validation)",
        "",
        "| Scorer | Cutoff | Margin | Net correct | Shown precision | Destination correct / wrong |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        *[f"| {g['scorer']} | {g['cutoff']} | {g['margin']} | {g['net_correct']} | {g['shown_precision']}% | "
          f"{g['dest_correct']} / {g['dest_wrong']} |" for g in by_scorer],
        "",
        "## Conflict policy (validation, best setting of each)",
        "",
        "When the destination fits a different service better than the number read: `withhold_both` hides "
        "service and destination; `keep_number` keeps the exact service and hides only the destination.",
        "",
        "| Policy | Scorer | Cutoff | Margin | Net correct | Shown precision | Service correct / wrong |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        *[f"| {g['conflict']} | {g['scorer']} | {g['cutoff']} | {g['margin']} | {g['net_correct']} | "
          f"{g['shown_precision']}% | {g['svc_correct']} / {g['svc_wrong']} |" for g in policy],
        "",
        "## Route crop as destination fallback (validation, best setting of each)",
        "",
        "When a display has no destination crop: `off` ignores the route crop; `check` uses it only to flag a service "
        "number it does not fit (never shown); `use` may also show it as the destination.",
        "",
        "| Fallback | Scorer | Cutoff | Margin | Net correct | Shown precision | Service correct / wrong | Destination correct / wrong |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[f"| {g['route_as_destination']} | {g['scorer']} | {g['cutoff']} | {g['margin']} | {g['net_correct']} | "
          f"{g['shown_precision']}% | {g['svc_correct']} / {g['svc_wrong']} | {g['dest_correct']} / {g['dest_wrong']} |" for g in route_cmp],
        "",
        "Full grid: `results/validation_grid.csv`. Per-display decisions with raw OCR, matched text, "
        "similarity and reasons: `results/per_display_validation.csv`, `results/per_display_test.csv`.",
        "",
        "## Limits",
        "",
        "- Displays are grouped by box containment (app association code), not Cody's `candidate_display_id`; "
        "swap in his `matching_inputs.jsonl` when it arrives.",
        "- Test has annotation-box crops only (no test detector crops).",
        "- Small samples: one display changes a percentage by several points.",
        "- Status counts (selected setting): " + "; ".join(
            f"{name}: " + ", ".join(f"{k[7:]} {v}" for k, v in sorted(m.items()) if k.startswith("status_"))
            for name, m in groups.items()),
    ]
    (OUT / "REFERENCE_MATCHING_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "results/selected_setting.json").write_text(json.dumps({**best, "answer_key": str(args.key.relative_to(ROOT)), "answer_key_reviewers": dict(reviewers),
                                                                   "answer_key_entries": len(key)}, indent=2) + "\n")
    print(json.dumps(best, indent=2))
    print(table(groups))


if __name__ == "__main__":
    main()
