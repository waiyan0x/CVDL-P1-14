"""Draft the destination answer key: human destination label -> correct reference endpoint.

The matcher outputs reference names ("Toa Payoh Bus Interchange") while labels
are sign text ("TOA PAYOH INT"), so scoring needs this key. The draft is built
from the HUMAN labels (never from OCR output) and must be checked by a person:
fill confirmed_endpoint (copy the proposal if it is right, type the correct
reference name if not, or NOT_IN_SERVICE / NONE).

    python scripts/draft_destination_answer_key.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.reference_matching import (  # noqa: E402
    NOT_IN_SERVICE, Reference, normalise_place, normalise_service, score_candidates, strip_display_clutter)

FIELDS = ["key_id", "gold_number", "destination_label", "splits", "displays", "proposed_endpoint",
          "proposed_score", "alt_1", "alt_1_score", "alt_2", "alt_2_score", "check", "confirmed_endpoint", "note"]


def gold_number(display, reference):
    field = display["fields"].get("number")
    if not field or not field["label_usable"]:
        return ""
    return normalise_service(field["label_text"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--displays", type=Path, default=ROOT / "evaluation/reference_matching/displays.jsonl")
    parser.add_argument("--reference", type=Path, default=ROOT / "data/reference/bus_information.cleaned.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/reference_matching/answer_key.draft.csv")
    args = parser.parse_args(argv)
    reference = Reference(args.reference)
    displays = [json.loads(line) for line in args.displays.read_text(encoding="utf-8").splitlines() if line.strip()]

    groups = defaultdict(list)
    for display in displays:
        field = display["fields"].get("destination")
        if not field or not field["label_usable"]:
            continue
        label = " ".join(field["label_text"].split())
        groups[(gold_number(display, reference), normalise_place(label, reference.abbreviations))].append((display, label))

    rows = []
    for index, ((number, norm), items) in enumerate(sorted(groups.items()), 1):
        label = items[0][1]
        row = {"key_id": f"K{index:03d}", "gold_number": number, "destination_label": label,
               "splits": ";".join(sorted({d["split"] + "/" + d["crop_set"] for d, _ in items})),
               "displays": len(items), "confirmed_endpoint": "", "note": ""}
        if NOT_IN_SERVICE.search(strip_display_clutter(label)):
            row.update(proposed_endpoint="NOT_IN_SERVICE", proposed_score="", check="ok")
        elif not norm:
            row.update(proposed_endpoint="NONE", proposed_score="", check="check", note="label has no place name")
        else:
            in_reference = number and reference.has_service(number)
            keys = reference.service_endpoints[number] if in_reference else list(reference.endpoints)
            scored = score_candidates(label, keys, reference, "token_sort_ratio")
            names = [(reference.endpoints[k].name, round(s, 1)) for s, k in scored[:3]]
            names += [("", "")] * (3 - len(names))
            margin = (scored[0][0] - scored[1][0]) if len(scored) > 1 else 100
            confident = in_reference and scored[0][0] >= 85 and margin >= 10
            row.update(proposed_endpoint=names[0][0], proposed_score=names[0][1], alt_1=names[1][0],
                       alt_1_score=names[1][1], alt_2=names[2][0], alt_2_score=names[2][1],
                       check="ok" if confident else "check",
                       note="" if in_reference else ("service not in reference; searched all endpoints" if number
                                                     else "no readable number on this display; searched all endpoints"))
        rows.append(row)

    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} label keys from {sum(r['displays'] for r in rows)} displays; "
          f"{sum(r['check'] == 'check' for r in rows)} flagged for a closer look -> {args.output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
