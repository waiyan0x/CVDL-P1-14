"""Ground-truth-based text metrics and spatial one-to-one display association."""
import math
import re
import statistics
import unicodedata

FIELD_NAMES = ("bus_number", "destination")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).upper()).strip()


def edit_distance(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for row, left in enumerate(first, 1):
        current = [row]
        for column, right in enumerate(second, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (left != right)))
        previous = current
    return previous[-1]


def iou(first: list, second: list) -> float:
    overlap = max(0, min(first[2], second[2]) - max(first[0], second[0])) * max(
        0, min(first[3], second[3]) - max(first[1], second[1]))
    area = (first[2] - first[0]) * (first[3] - first[1]) + (
        second[2] - second[0]) * (second[3] - second[1]) - overlap
    return overlap / area if area > 0 else 0


def associate(truth: list[dict], predictions: list[dict], threshold: float) -> dict[int, int]:
    candidates = sorted(((iou(t["box"], p["box"]), ti, pi)
                         for ti, t in enumerate(truth) for pi, p in enumerate(predictions)), reverse=True)
    matches, used = {}, set()
    for overlap, ti, pi in candidates:
        if overlap >= threshold and ti not in matches and pi not in used:
            matches[ti] = pi
            used.add(pi)
    return matches


def prediction_box(display: dict) -> list | None:
    if (display.get("screen") or {}).get("box"):
        return display["screen"]["box"]
    boxes = [field["box"] for field in display.get("fields", {}).values() if field.get("box")]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def score_image(truth: list[dict], predictions: list[dict]) -> dict:
    usable = [{"box": prediction_box(display), "display": display} for display in predictions]
    usable = [display for display in usable if display["box"] is not None]
    matches = associate(truth, usable, .1)
    outcomes = []
    for index, expected in enumerate(truth):
        prediction = usable[matches[index]]["display"] if index in matches else {}
        fields = {}
        for name in FIELD_NAMES:
            text = expected.get(name)
            if text is None:
                continue
            raw = prediction.get("fields", {}).get(name, {}).get("raw", "")
            fields[name] = {"truth": text, "raw": raw, "exact": raw == text,
                            "normalized_exact": normalize(raw) == normalize(text),
                            "errors": edit_distance(text, raw), "characters": len(text),
                            "normalized_errors": edit_distance(normalize(text), normalize(raw)),
                            "normalized_characters": len(normalize(text))}
        outcomes.append({"display_id": expected["id"], "detected": index in matches, "fields": fields,
                         "match": prediction.get("match"),
                         "complete_exact": all(f["exact"] for f in fields.values()),
                         "complete_normalized_exact": all(f["normalized_exact"] for f in fields.values())})
    return {"displays": outcomes, "missed_displays": len(truth) - len(matches),
            "extra_displays": len(predictions) - len(matches)}


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    return round(ordered[lower] + (ordered[math.ceil(position)] - ordered[lower]) * (position - lower), 3)


def aggregate_engine(images: list[dict], latency: list[float]) -> dict:
    displays = [display for image in images for display in image["displays"]]
    fields = {}
    for name in FIELD_NAMES:
        outcomes = [display["fields"][name] for display in displays if name in display["fields"]]
        count, characters = len(outcomes), sum(outcome["characters"] for outcome in outcomes)
        normalized_characters = sum(outcome["normalized_characters"] for outcome in outcomes)
        fields[name] = {"count": count,
                        "exact_accuracy": sum(o["exact"] for o in outcomes) / count if count else None,
                        "normalized_accuracy": sum(o["normalized_exact"] for o in outcomes) / count if count else None,
                        "cer": sum(o["errors"] for o in outcomes) / characters if characters else None,
                        "normalized_cer": sum(o["normalized_errors"] for o in outcomes) / normalized_characters
                        if normalized_characters else None}
    return {"fields": fields, "display_count": len(displays),
            "complete_exact_accuracy": sum(d["complete_exact"] for d in displays) / len(displays) if displays else None,
            "complete_normalized_accuracy": sum(d["complete_normalized_exact"] for d in displays) / len(displays) if displays else None,
            "missed_displays": sum(image["missed_displays"] for image in images),
            "extra_displays": sum(image["extra_displays"] for image in images),
            "latency_ms": {"median": statistics.median(latency) if latency else None,
                           "p95": percentile(latency, .95), "count": len(latency)}}


def screen_detection_counts(truth: list[dict], detections: list[dict]) -> dict:
    screens = [d for d in detections if d.get("label") == "eds"]
    predictions = [d for d in screens if d.get("source", "model") == "model"]
    matched = len(associate(truth, predictions, .5))
    return {"true_positive": matched, "false_positive": len(predictions) - matched,
            "false_negative": len(truth) - matched, "excluded_estimates": len(screens) - len(predictions)}
