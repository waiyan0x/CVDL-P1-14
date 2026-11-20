"""Match OCR text from one bus display to the bus reference and print the result.

Type the text yourself:
    python scripts/match_reference.py --number 14E --destination "> TAMP1NES INT"
    python scripts/match_reference.py --panel "65 TAMPINES INT"

Or look up Cody's fine-tuned PaddleOCR reading for a dataset crop / photo:
    python scripts/match_reference.py --review-id A001
    python scripts/match_reference.py --image 14488614-bus_8_jpg.rf.f42edf43192002dc5ef10238a21c7e38.jpg

Settings default to the ones chosen on validation (results/selected_setting.json).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.reference_matching import SCORERS, DisplayMatcher, Reference, Settings  # noqa: E402

OUT = ROOT / "evaluation/reference_matching"


def default_settings():
    path = OUT / "results/selected_setting.json"
    if path.is_file():
        s = json.loads(path.read_text())
        return Settings(s["cutoff"], s["margin"], s["scorer"], s.get("conflict", "withhold_both"))
    return Settings()


def ocr(field):
    if field is None:
        return None
    return (field["raw"] or "") if field["ocr_status"] == "success" else ""


def show(result, labels=None, title=None):
    def cell(value):
        return "-" if value in (None, "") else str(value).replace("\n", " / ")
    raw = result["raw"]
    rows = [("Service number", raw["number"], result["service"], None, result["service_status"]),
            ("Destination", raw["destination"], result["destination"],
             f"{result['destination_score']:.1f}%" if result["destination_score"] is not None else None,
             result["destination_status"] + (" (from whole display)" if result["sources"].get("destination") == ["panel"] else "")),
            ("Route text", raw["route"], result["route_text"], None, "kept as read" if result["route_text"] else None),
            ("Whole display", raw["panel"], None, None, None)]
    head = ["Field", "Raw OCR", "Matched reference", "Similarity", "Decision"] + (["Human label"] if labels else [])
    table = [head] + [[name, cell(r), cell(m), cell(s), cell(d)] + ([cell(labels.get(name))] if labels else [])
                      for name, r, m, s, d in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(head))]
    if title:
        print(f"\n== {title}")
    for i, row in enumerate(table):
        print("  ".join(value.ljust(width) for value, width in zip(row, widths)))
        if i == 0:
            print("  ".join("-" * width for width in widths))
    print(f"Result: {result['status'].upper()} - {result['message']}")
    print(f"Why:    {result['reason']}")
    if result.get("candidate") and not result["destination"]:
        print(f"Best destination candidate (not accepted): {result['candidate']} ({result['destination_score']:.1f}%)")
    if result["runner_up"]:
        print(f"Next best destination: {result['runner_up']} ({result['runner_up_score']:.1f}%)")
    for line in result["log"]:
        print(f"Note:   {line}")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    text = parser.add_argument_group("type the OCR text")
    text.add_argument("--number"), text.add_argument("--destination"), text.add_argument("--route")
    text.add_argument("--panel", help="OCR text of the whole display crop")
    data = parser.add_argument_group("use dataset crops (Cody's fine-tuned PaddleOCR readings)")
    data.add_argument("--review-id", help="crop id such as A001, P034 or TEST_A0169")
    data.add_argument("--image", help="source photo file name: shows every display on it")
    tune = parser.add_argument_group("settings (default: chosen on validation)")
    tune.add_argument("--cutoff", type=float), tune.add_argument("--margin", type=float)
    tune.add_argument("--scorer", choices=list(SCORERS)), tune.add_argument("--conflict", choices=["withhold_both", "keep_number"])
    parser.add_argument("--reference", type=Path, default=ROOT / "data/reference/bus_information.cleaned.csv")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args(argv)

    settings = default_settings()
    for name in ("cutoff", "margin", "scorer", "conflict"):
        if getattr(args, name) is not None:
            setattr(settings, name, getattr(args, name))
    matcher = DisplayMatcher(Reference(args.reference), settings)
    print(f"Settings: scorer={settings.scorer} cutoff={settings.cutoff:g} margin={settings.margin:g} conflict={settings.conflict}")

    if args.review_id or args.image:
        path = OUT / "displays.jsonl"
        displays = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        wanted = [d for d in displays
                  if (args.image and d["image"] == args.image) or (args.review_id and (
                      args.review_id in {f["review_id"] for f in d["fields"].values()}
                      or (d["panel"] or {}).get("review_id") == args.review_id))]
        if not wanted:
            parser.error("no display found; run scripts/build_matching_displays.py and check the id / file name")
        for d in wanted:
            f = d["fields"]
            result = matcher.match(number=ocr(f.get("number")), destination=ocr(f.get("destination")),
                                   route=ocr(f.get("route")), panel=(d["panel"] or {}).get("raw"))
            labels = {"Service number": (f.get("number") or {}).get("label_text"),
                      "Destination": (f.get("destination") or {}).get("label_text"),
                      "Route text": (f.get("route") or {}).get("label_text")}
            print(json.dumps(result, indent=2, ensure_ascii=False)) if args.json else show(result, labels, d["display_key"])
        return
    if all(v is None for v in (args.number, args.destination, args.route, args.panel)):
        parser.error("give OCR text (--number/--destination/--route/--panel) or --review-id / --image")
    result = matcher.match(number=args.number, destination=args.destination, route=args.route, panel=args.panel)
    print(json.dumps(result, indent=2, ensure_ascii=False)) if args.json else show(result)


if __name__ == "__main__":
    main()
