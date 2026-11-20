"""Write a cleaned copy of data/bus_information.csv and a report of what changed.

The original file is never modified. Cleaning only fixes formatting and obvious
errors; it adds no services and keeps both directions of every route.

    python scripts/clean_bus_reference.py
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.reference_matching import load_abbreviations, normalise_place  # noqa: E402

# Spelling errors confirmed by reading the file; add new ones here, never edit the original CSV.
CORRECTIONS = {"Kent Ridge MRT dtation": "Kent Ridge MRT station"}
STANDARD_SERVICE = re.compile(r"^[0-9]{1,3}[A-Z]{0,2}$")


def clean_name(text: str) -> tuple[str, list[str]]:
    notes, name = [], " ".join((text or "").split())
    if name != (text or ""):
        notes.append("whitespace trimmed")
    if "’" in name:
        name = name.replace("’", "'")
        notes.append("curly apostrophe made straight")
    if name in CORRECTIONS:
        notes.append(f"spelling corrected from '{name}'")
        name = CORRECTIONS[name]
    return name, notes


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=ROOT / "data/bus_information.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/bus_information.cleaned.csv")
    parser.add_argument("--report", type=Path, default=ROOT / "data/reference/cleaning_report.json")
    args = parser.parse_args(argv)

    with args.source.open(newline="", encoding="utf-8-sig") as stream:
        source = list(csv.DictReader(stream))
    cleaned, changes, dropped, flags, seen = [], [], [], [], {}
    for line, row in enumerate(source, 2):
        service = " ".join(row["Route number"].split())
        if STANDARD_SERVICE.match(service.upper()):
            service = service.upper()          # 851e -> 851E; named shuttles keep their spelling
        notes = [] if service == row["Route number"] else ["service id trimmed / upper-cased"]
        origin, n1 = clean_name(row["Origin"])
        destination, n2 = clean_name(row["Destination"])
        notes += [f"origin: {n}" for n in n1] + [f"destination: {n}" for n in n2]
        key = (service, origin, destination)
        if key in seen:
            dropped.append({"line": line, "duplicate_of_line": seen[key], "row": list(key)})
            continue
        seen[key] = line
        if notes:
            changes.append({"line": line, "service": service, "changes": notes})
        if not origin or not destination:
            flags.append({"line": line, "service": service, "flag": "blank endpoint; only the filled endpoint can be matched"})
        if not STANDARD_SERVICE.match(service.upper()):
            flags.append({"line": line, "service": service, "flag": "non-standard service id (shuttle/named service); kept"})
        cleaned.append({"Route number": service, "Origin": origin, "Destination": destination, "source_line": line})

    abbreviations = load_abbreviations()
    names = sorted({r[k] for r in cleaned for k in ("Origin", "Destination") if r[k]})
    keys = {name: normalise_place(name, abbreviations, display=False) for name in names}
    merged = {}
    for name, key in keys.items():
        merged.setdefault(key, []).append(name)
    same_after_normalising = {k: v for k, v in merged.items() if len(v) > 1}
    close_pairs = sorted(((a, b, round(fuzz.ratio(keys[a], keys[b]), 1))
                          for a, b in itertools.combinations(names, 2)
                          if keys[a] != keys[b] and fuzz.ratio(keys[a], keys[b]) >= 90),
                         key=lambda item: -item[2])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["Route number", "Origin", "Destination", "source_line"])
        writer.writeheader()
        writer.writerows(cleaned)
    report = {
        "source": str(args.source.relative_to(ROOT)), "output": str(args.output.relative_to(ROOT)),
        "rows_in": len(source), "rows_out": len(cleaned), "services": len({r["Route number"] for r in cleaned}),
        "distinct_endpoint_names": len(names), "distinct_endpoints_after_normalising": len(merged),
        "exact_duplicates_dropped": dropped, "rows_changed": changes, "flags": flags,
        "names_identical_after_normalising": same_after_normalising,
        "similar_names_kept_distinct": [{"a": a, "b": b, "ratio": r} for a, b, r in close_pairs],
    }
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(source)} rows -> {len(cleaned)} rows; {len(dropped)} duplicates dropped, "
          f"{len(changes)} rows changed, {len(flags)} flags; {len(names)} names -> {len(merged)} after normalising")


if __name__ == "__main__":
    main()
