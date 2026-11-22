"""One-line announcement for a matched display, e.g. "Bus 64 to Ang Mo Kio Bus Interchange, via Jln Besar."

Only what the matcher confirmed is stated as fact: the service number (exact reference match) and the
destination (reference endpoint name). Route text cannot be checked against the reference (it has no road
names), so it is added only when it reads like a road name, and is never presented as the destination.
"""
from __future__ import annotations

import re

ROAD_ENDINGS = {"RD", "AVE", "ST", "DR", "CRES", "WAY", "LN", "CL", "PL", "HTS", "RING", "LINK", "PK", "CTR",
                "CTRL", "INT", "TER", "MRT", "LRT", "STN", "SQ", "JCT", "BLVD", "GDN", "GDNS", "WALK", "RISE",
                "VIEW", "HILL", "GR", "NTH", "STH", "EST", "QUAY", "LOOP", "CIRCLE", "CIR", "PLAINS", "ROAD",
                "AVENUE", "STREET", "DRIVE", "CRESCENT", "LANE", "CLOSE", "PLACE", "HEIGHTS"}
ROAD_STARTS = {"JLN", "JALAN", "LOR", "LORONG", "UPP", "UPPER", "LOWER"}
KEEP_UPPER = {"MRT", "LRT", "NTU", "NUS", "CBP", "SMU", "ITE"}
CLUTTER = re.compile(r"^\s*(VIA|>|-)\s*|\s*(>|-)\s*$", re.I)


def route_phrase(text: str | None) -> str | None:
    """Tidy route OCR for speech/display, or None if it does not look like a road or place name."""
    if not text:
        return None
    cleaned = CLUTTER.sub("", " ".join(text.replace("\n", " ").split())).strip(" .,>-")
    tokens = re.findall(r"[A-Za-z]+|\d+[A-Za-z]?", cleaned.upper())
    # Drop up to two trailing junk tokens after a road ending ("THOMSON RD WA" from the number column edge).
    for cut in (1, 2):
        if len(tokens) > cut + 1 and tokens[-cut - 1] in ROAD_ENDINGS and not any(t[0].isdigit() for t in tokens[-cut:]) \
                and tokens[-1] not in ROAD_ENDINGS:
            tokens = tokens[:-cut]
            break
    if len(tokens) < 2 or any(len(t) < 2 and not t[0].isdigit() for t in tokens):
        return None
    if any(t[0].isdigit() for t in tokens[:-1]):        # a number mid-name is an OCR split ("SIME 1 RD")
        return None
    last = tokens[-2] if tokens[-1][0].isdigit() and len(tokens) > 2 else tokens[-1]
    if last not in ROAD_ENDINGS and tokens[0] not in ROAD_STARTS:
        return None
    return " ".join(t if t in KEEP_UPPER or t[0].isdigit() else t.capitalize() for t in tokens)


def build_announcement(result: dict) -> str | None:
    """Announcement for one matcher result (DisplayMatcher.match output); None when nothing was detected."""
    status = result.get("status")
    if status in (None, "no_fields", "no_reference"):
        return None
    if status == "not_in_service":
        return "Bus not in service."
    service, destination = result.get("service"), result.get("destination")
    raw = result.get("raw") or {}
    sources = (result.get("sources") or {}).get("destination", [])
    lines = raw.get("panel_lines") or []
    if "panel_line" in sources and len(lines) > 1:
        # Destination came from one whole-display line: the other line is the route.
        used = re.sub(r"\W", "", (result.get("destination_text") or "").upper())
        others = [l for l in lines if used and used not in re.sub(r"\W", "", l.upper())]
        via = next((v for v in map(route_phrase, others) if v), None) or route_phrase(raw.get("route"))
    elif "route_swapped" in sources:
        # With swapped lines the route crop held the destination, so the destination crop holds the route.
        via = route_phrase(raw.get("destination"))
    else:
        via = route_phrase(raw.get("route"))
    if via and destination and via.upper().replace(" ", "") in destination.upper().replace(" ", ""):
        via = None
    via_part = f", via {via}" if via else ""

    if service and destination:
        return f"Bus {service} to {destination}{via_part}."
    if service:
        reason = "could not be confirmed" if result.get("destination_status") in ("conflict", "tie", "below_cutoff") \
            else "could not be read"
        return f"Bus {service} is approaching{via_part}. Destination {reason}."
    number_seen = bool((raw.get("number") or "").strip()) or result.get("service_status") not in (None, "unread")
    number_part = "Bus number could not be confirmed" if number_seen else "Bus number could not be read"
    if destination:
        return f"A bus to {destination} is approaching{via_part}. {number_part}."
    if number_seen:
        return f"A bus is approaching{via_part}. Bus number and destination could not be confirmed."
    if via:
        return f"A bus is approaching, via {via}. Bus number and destination could not be read."
    return "A bus is approaching. Bus number and destination could not be read."
