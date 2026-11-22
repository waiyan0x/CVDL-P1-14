"""Match OCR text from one bus display to the bus reference and print the result.

Type the text yourself:
    python scripts/match_reference.py --number 14E --destination "> TAMP1NES INT"
    python scripts/match_reference.py --panel "65 TAMPINES INT"

Or look up Cody's fine-tuned PaddleOCR reading for a dataset crop / photo:
    python scripts/match_reference.py --review-id A001
    python scripts/match_reference.py --image 14488614-bus_8_jpg.rf.f42edf43192002dc5ef10238a21c7e38.jpg

Or run the full chain on a photo: YOLO11s finds the display boxes, PaddleOCR reads each crop,
then every display is matched (needs: pip install ultralytics paddlepaddle paddleocr):
    python scripts/match_reference.py --photo models/local/photos/bus_374.png --save-dir runs/matching

Or read every crop saved by --photo --save-dir (display-N_<field>.png), grouped by display:
    python scripts/match_reference.py --crop-dir runs/matching/bus_374

Or read crop images with PaddleOCR first (needs: pip install paddlepaddle paddleocr):
    python scripts/match_reference.py --number-crop num.png --destination-crop dest.png
    python scripts/match_reference.py --destination-crop dest.png --ocr-model-dir path/to/paddleocr/best
OCR weights: two models. Number, destination and route crops use --ocr-model-dir, else
models/local/paddleocr (fine-tuned), else models/local/paddleocr-pretrained, else the public
en_PP-OCRv5_mobile_rec (downloaded on first use). Whole-display (panel) crops use --panel-ocr-model-dir,
else models/local/paddleocr-pretrained, else the public model: the fine-tuned model was trained on
single-field crops only and misreads whole displays. --panel-ocr-model-dir same = one model for all crops.
Detector weights: --detector, default models/local/yolo/best.pt (Brendan's fine-tuned YOLO11s).

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
        return Settings(s["cutoff"], s["margin"], s["scorer"], s.get("conflict", "withhold_both"),
                        s.get("route_as_destination", "off"))
    return Settings()


PUBLIC_MODEL = "en_PP-OCRv5_mobile_rec"
LOCAL_OCR_DIRS = [ROOT / "models/local/paddleocr", ROOT / "models/local/paddleocr-pretrained"]
DEFAULT_DETECTOR = ROOT / "models/local/yolo/best.pt"
DETECTOR_LABELS = {"front_eds": "eds", "front_eds_num": "bus_number",
                   "front_eds_destination": "destination", "front_eds_route": "route"}


def resolve_ocr_dir(model_dir):
    if model_dir:
        return Path(model_dir)
    return next((d for d in LOCAL_OCR_DIRS if (d / "inference.pdiparams").is_file()), None)


def resolve_panel_ocr_dir(panel_dir, field_dir):
    """Whole-display crops: pretrained model by default (None = public model)."""
    if panel_dir == "same":
        return field_dir
    if panel_dir:
        return Path(panel_dir)
    pretrained = ROOT / "models/local/paddleocr-pretrained"
    return pretrained if (pretrained / "inference.pdiparams").is_file() else None


def make_readers(args):
    """Return read(path, field) -> (text, confidence): panel crops use the panel model, others the field model."""
    field_dir = resolve_ocr_dir(args.ocr_model_dir)
    panel_dir = resolve_panel_ocr_dir(args.panel_ocr_model_dir, field_dir)
    name = lambda d: str(d) if d else PUBLIC_MODEL + " (public pretrained, downloaded)"
    print(f"OCR model (number/destination/route crops): {name(field_dir)}")
    print(f"OCR model (whole-display crops):            {name(panel_dir)}")
    field_reader = make_reader(field_dir)
    panel_reader = field_reader if panel_dir == field_dir else make_reader(panel_dir)
    return lambda path, field: (panel_reader if field == "panel" else field_reader)(path)


def iou(a, b):
    w = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w * h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def drop_duplicate_panels(boxes, threshold=0.5):
    """Keep the more confident of two display (eds) boxes that overlap by IoU >= threshold."""
    kept = []
    for box in sorted(boxes, key=lambda b: -b["confidence"]):
        if box["label"] == "eds" and any(k["label"] == "eds" and iou(k["box"], box["box"]) >= threshold for k in kept):
            continue
        kept.append(box)
    return kept


def merge_orphan_lines(groups):
    """Attach a display that has no display box and no number (e.g. a lone route line) to the display it
    sits directly above or below: horizontal overlap and a vertical gap under one line height."""
    def box_of(group):
        if group["screen"]:
            return group["screen"]["box"]
        fb = [f["box"] for f in group["fields"].values()]
        return [min(b[0] for b in fb), min(b[1] for b in fb), max(b[2] for b in fb), max(b[3] for b in fb)]
    kept = [g for g in groups if g["screen"] or "bus_number" in g["fields"]]
    for orphan in [g for g in groups if g not in kept]:
        ob = box_of(orphan)
        line = ob[3] - ob[1]
        candidates = []
        for g in kept:
            gb = box_of(g)
            overlap = min(ob[2], gb[2]) - max(ob[0], gb[0])
            gap = max(gb[1] - ob[3], ob[1] - gb[3], 0)
            if overlap > 0 and gap <= line and not (set(orphan["fields"]) & set(g["fields"])):
                candidates.append((gap, id(g), g))
        best = min(candidates, key=lambda c: c[:2]) if candidates else None
        if best:
            best[2]["fields"].update(orphan["fields"])
        else:
            kept.append(orphan)
    return kept


def run_photo(photo, detector_path, reader, save_dir=None, conf=0.5, iou=0.7, imgsz=640):
    """YOLO11s boxes -> displays (app association) -> PaddleOCR per crop. Returns (displays, image size)."""
    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("Photo mode needs Ultralytics: pip install ultralytics")
    from PIL import Image, ImageDraw
    from backend.app.services.association import associate_displays
    if not Path(detector_path).is_file():
        sys.exit(f"Detector weights not found: {detector_path}")
    import time
    timing = {}
    image = Image.open(photo).convert("RGB")
    model = YOLO(str(detector_path))
    model.predict(image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)            # warm-up, not timed
    start = time.perf_counter()
    result = model.predict(image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)[0]
    timing["detection_ms"] = (time.perf_counter() - start) * 1000
    boxes = [{"label": DETECTOR_LABELS[model.names[int(b.cls)]], "confidence": round(float(b.conf), 3),
              "box": [round(v) for v in b.xyxy[0].tolist()]} for b in result.boxes]
    boxes = drop_duplicate_panels(boxes)
    start = time.perf_counter()
    groups, _ = associate_displays(boxes, *image.size)
    groups = merge_orphan_lines(groups)
    timing["association_ms"] = (time.perf_counter() - start) * 1000
    timing["ocr_ms"], timing["ocr_crops"] = 0.0, 0
    save = Path(save_dir) / Path(photo).stem if save_dir else None
    if save:
        save.mkdir(parents=True, exist_ok=True)
    displays = []
    for group in groups:
        texts, crops = {}, {}
        items = [("panel", group["screen"])] if group["screen"] and group["screen"].get("source") != "field_union" else []
        items += [({"bus_number": "number"}.get(k, k), v) for k, v in group["fields"].items()]
        for field, item in items:
            x1, y1, x2, y2 = item["box"]
            crop = image.crop((max(0, x1), max(0, y1), min(image.size[0], x2), min(image.size[1], y2)))
            path = (save / f"{group['display_id']}_{field}.png") if save else Path(f"/tmp/_crop_{group['display_id']}_{field}.png")
            crop.save(path)
            start = time.perf_counter()
            text, confidence = reader(path, field)
            timing["ocr_ms"] += (time.perf_counter() - start) * 1000
            timing["ocr_crops"] += 1
            texts[field] = text
            crops[field] = {"box": item["box"], "detector_confidence": item.get("confidence"),
                            "ocr_confidence": confidence, "crop": str(path)}
        if group["screen"]:
            box = group["screen"]["box"]
        else:
            fb = [f["box"] for f in group["fields"].values()]
            box = [min(b[0] for b in fb), min(b[1] for b in fb), max(b[2] for b in fb), max(b[3] for b in fb)]
        displays.append({"display_id": group["display_id"], "texts": texts, "crops": crops, "box": box,
                         "area": (box[2] - box[0]) * (box[3] - box[1])})
    # Nearest bus first: its display appears largest in the photo.
    displays.sort(key=lambda d: -d["area"])
    if save:
        draw = ImageDraw.Draw(image)
        colours = {"eds": "yellow", "bus_number": "red", "destination": "lime", "route": "cyan"}
        for b in boxes:
            draw.rectangle(b["box"], outline=colours[b["label"]], width=3)
            draw.text((b["box"][0], max(0, b["box"][1] - 12)), f"{b['label']} {b['confidence']:.2f}", fill=colours[b["label"]])
        image.save(save / "detections.png")
    return displays, boxes, timing


def make_reader(model_dir=None):
    """Return read(path) -> (text, confidence) using PaddleOCR text recognition."""
    try:
        from paddleocr import TextRecognition
    except ImportError:
        sys.exit("Reading crop images needs PaddleOCR: pip install paddlepaddle paddleocr")
    model = (TextRecognition(model_name=PUBLIC_MODEL, model_dir=str(model_dir)) if model_dir
             else TextRecognition(model_name=PUBLIC_MODEL))

    warmed = []

    def read(path):
        if not warmed:                       # first call loads the model; keep it out of the timings
            warmed.append(True)
            list(model.predict(str(path)))
        if not Path(path).is_file():
            sys.exit(f"Crop image not found: {path}")
        results = list(model.predict(str(path)))
        if not results:
            return "", None
        return results[0]["rec_text"], float(results[0]["rec_score"])
    return read


def read_crops(args, reader):
    """OCR every crop given on the command line; typed text is used for fields without a crop."""
    texts, notes = {}, []
    for field in ("number", "destination", "route", "panel"):
        path = getattr(args, f"{field}_crop")
        if path:
            text, confidence = reader(path, field)
            texts[field] = text
            notes.append(f"{field}: {path} -> {text!r}" + (f" (OCR confidence {confidence:.2f})" if confidence is not None else ""))
        else:
            texts[field] = getattr(args, field)
    return texts, notes


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
             result["destination_status"] + {("panel",): " (from whole display)", ("route",): " (from route crop)",
                                                ("route_swapped",): " (from route crop: lines swapped)",
                                                ("route_swapped", "panel"): " (route crop + whole display)",
                                                ("panel", "route_swapped"): " (whole display + route crop)"}.get(
                 tuple(result["sources"].get("destination", [])), "")),
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
    if result.get("announcement"):
        print(f"Message: {result['announcement']}")
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
    crops = parser.add_argument_group("read crop images with PaddleOCR first")
    for field in ("number", "destination", "route", "panel"):
        crops.add_argument(f"--{field}-crop", type=Path, help=f"image of the {field} crop")
    crops.add_argument("--crop-dir", type=Path,
                       help="folder of display-N_<number|destination|route|panel>.png crops; reads all of them")
    crops.add_argument("--ocr-model-dir", type=Path,
                       help="model for number/destination/route crops: folder with inference.pdiparams/.json/.yml")
    crops.add_argument("--panel-ocr-model-dir",
                       help="model for whole-display crops (default models/local/paddleocr-pretrained); "
                            "'same' = use --ocr-model-dir for every crop")
    photo = parser.add_argument_group("run the full chain on a photo (YOLO11s -> PaddleOCR -> matching)")
    photo.add_argument("--photo", type=Path, help="bus photo")
    photo.add_argument("--detector", type=Path, default=DEFAULT_DETECTOR, help="YOLO11s weights (.pt)")
    photo.add_argument("--save-dir", type=Path, help="write crops and an annotated detections.png here")
    photo.add_argument("--closest-only", action="store_true",
                       help="report only the largest display (the nearest bus); others are listed by size")
    data = parser.add_argument_group("use dataset crops (Cody's fine-tuned PaddleOCR readings)")
    data.add_argument("--review-id", help="crop id such as A001, P034 or TEST_A0169")
    data.add_argument("--image", help="source photo file name: shows every display on it")
    tune = parser.add_argument_group("settings (default: chosen on validation)")
    tune.add_argument("--cutoff", type=float), tune.add_argument("--margin", type=float)
    tune.add_argument("--scorer", choices=list(SCORERS)), tune.add_argument("--conflict", choices=["withhold_both", "keep_number"])
    tune.add_argument("--route-as-destination", choices=["off", "check", "use"],
                      help="no destination crop: off = ignore route crop; check = only flag a number it does not fit; "
                           "use = may show it as the destination")
    parser.add_argument("--reference", type=Path, default=ROOT / "data/reference/bus_information.cleaned.csv")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args(argv)

    settings = default_settings()
    for name in ("cutoff", "margin", "scorer", "conflict"):
        if getattr(args, name) is not None:
            setattr(settings, name, getattr(args, name))
    if args.route_as_destination:
        settings.route_as_destination = args.route_as_destination
    matcher = DisplayMatcher(Reference(args.reference), settings)
    print(f"Settings: scorer={settings.scorer} cutoff={settings.cutoff:g} margin={settings.margin:g} "
          f"conflict={settings.conflict} route_as_destination={settings.route_as_destination}")

    if args.photo:
        print(f"Detector:  {args.detector}")
        import time
        displays, boxes, timing = run_photo(args.photo, args.detector, make_readers(args), args.save_dir)
        print(f"Detected boxes: " + ", ".join(f"{b['label']} {b['confidence']:.2f}" for b in boxes) if boxes else "Detected boxes: none")
        if not displays:
            show(matcher.match(detected=False), title=f"{args.photo.name}: no display found")
        if len(displays) > 1:
            print("Displays by size (largest = nearest bus): " + ", ".join(
                f"{d['display_id']} ({d['area']} px², number {d['texts'].get('number') or d['texts'].get('panel') or '?'!r})"
                for d in displays))
        timing["matching_ms"] = 0.0
        for rank, d in enumerate(displays[:1] if args.closest_only else displays, 1):
            start = time.perf_counter()
            result = matcher.match(**{k: d["texts"].get(k) for k in ("number", "destination", "route", "panel")})
            timing["matching_ms"] += (time.perf_counter() - start) * 1000
            label = "nearest bus" if rank == 1 and len(displays) > 1 else f"size rank {rank}"
            print(json.dumps({**result, "crops": d["crops"], "display_box": d["box"], "size_rank": rank}, indent=2,
                             ensure_ascii=False)) if args.json \
                else show(result, title=f"{args.photo.name} display {d['display_id']} ({label})")
        total = timing["detection_ms"] + timing["association_ms"] + timing["ocr_ms"] + timing["matching_ms"]
        print(f"\nTiming (this machine, models already loaded): detection {timing['detection_ms']:.0f} ms | "
              f"grouping {timing['association_ms']:.1f} ms | OCR {timing['ocr_ms']:.0f} ms for {timing['ocr_crops']} crops | "
              f"matching {timing['matching_ms']:.1f} ms | total {total:.0f} ms per frame")
        if args.save_dir:
            print(f"Crops and detections.png saved in {Path(args.save_dir) / args.photo.stem}")
        return
    if args.crop_dir:
        import re
        reader, groups = make_readers(args), {}
        for path in sorted(Path(args.crop_dir).glob("*.png")):
            found = re.fullmatch(r"(.+)_(number|destination|route|panel)", path.stem)
            if found:
                groups.setdefault(found.group(1), {})[found.group(2)] = path
        if not groups:
            parser.error(f"no display-N_<field>.png crops in {args.crop_dir}")
        for display, files in groups.items():
            texts = {}
            print(f"\n== {args.crop_dir.name} {display}: OCR of every crop")
            for field in ("number", "destination", "route", "panel"):
                if field in files:
                    text, confidence = reader(files[field], field)
                    texts[field] = text
                    print(f"OCR:    {field:<11} {files[field].name:<28} -> {text!r}"
                          + (f" (confidence {confidence:.2f})" if confidence is not None else ""))
                else:
                    print(f"OCR:    {field:<11} (no crop detected)")
            result = matcher.match(**{k: texts.get(k) for k in ("number", "destination", "route", "panel")})
            print(json.dumps(result, indent=2, ensure_ascii=False)) if args.json else show(result)
        return
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
    texts = {f: getattr(args, f) for f in ("number", "destination", "route", "panel")}
    if any(getattr(args, f"{f}_crop") for f in texts):
        texts, notes = read_crops(args, make_readers(args))
        for line in notes:
            print(f"OCR:    {line}")
    if all(v is None for v in texts.values()):
        parser.error("give OCR text (--number/--destination/--route/--panel), crop images (--number-crop ...) "
                     "or --review-id / --image")
    result = matcher.match(**texts)
    print(json.dumps(result, indent=2, ensure_ascii=False)) if args.json else show(result)


if __name__ == "__main__":
    main()
