"""Reference matching: OCR text from one bus display -> bus_information.csv entries.

Decision rules (one display at a time; see docs/REFERENCE_MATCHING.md):

* Number only: accept a normalised number only if it exactly equals a reference
  service. A destination is inferred only when that service has one distinct
  endpoint in the reference.
* Destination only: score every distinct reference endpoint. Accept the best
  one if it reaches the cutoff and leads the next distinct endpoint by the
  margin. Infer the number only if that endpoint belongs to one service.
* Number and destination: the exact service narrows the destination search.
  Below the cutoff, or tied, the destination stays unresolved. If the
  destination strongly matches an endpoint of a different service instead,
  the display is flagged as a conflict and both fields are withheld.
* Route text only: kept as read; the reference has no road names.
* No usable fields: the reason is recorded (no crops, unreadable, not matched).

A number that is read but is not a reference service gives "unable to detect"
for the service. Raw OCR text is always returned next to any matched value.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ABBREVIATIONS = ROOT / "data/reference/abbreviations.csv"

SCORERS = {
    "ratio": fuzz.ratio,
    "token_sort_ratio": fuzz.token_sort_ratio,
    "token_set_ratio": fuzz.token_set_ratio,
    "WRatio": fuzz.WRatio,
}

# Display clutter that is not part of the destination name.
NOT_IN_SERVICE = re.compile(r"\b(DEPOT|NOT IN SERVICE|OFF SERVICE|NO SERVICE|OUT OF SERVICE)\b")
SERVICE_TOKEN = re.compile(r"^[0-9]{1,3}[A-Z]{0,2}$")
MESSAGES = {
    "matched": "Service and destination matched to the reference.",
    "service_only": "Service matched; destination not confirmed.",
    "destination_only": "Destination matched; service not confirmed.",
    "conflict": "Service and destination point to different reference routes; both withheld.",
    "conflict_service_kept": "Destination fits a different service; destination withheld, exact service kept.",
    "not_in_service": "Display shows a depot or not-in-service message.",
    "unable_to_detect": "Unable to detect: the service read is not in the reference.",
    "route_text_only": "Only route text was read; service unresolved.",
    "unresolved": "Text was read but did not match the reference.",
    "unreadable": "Display found, but no text could be read.",
    "no_fields": "No display fields were detected.",
}


# ---------------------------------------------------------------- normalisation

def load_abbreviations(path: Path | None = DEFAULT_ABBREVIATIONS) -> dict[str, str]:
    """variant -> standard form. Missing file means no substitutions."""
    if path is None or not Path(path).is_file():
        return {}
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return {row["variant"].strip().upper(): row["standard"].strip().upper()
                for row in csv.DictReader(stream) if row.get("variant", "").strip()}


def normalise_service(text: str | None) -> str:
    """Upper case, no spaces, no surrounding punctuation. Letters and zeros are kept."""
    text = unicodedata.normalize("NFKC", text or "").upper()
    text = re.sub(r"\s+", "", text)
    return re.sub(r"^[^A-Z0-9]+|[^A-Z0-9]+$", "", text)


def strip_display_clutter(text: str) -> str:
    """Remove EDS decorations that are not part of a destination name."""
    text = unicodedata.normalize("NFKC", text or "").upper().replace("\n", " ")
    text = re.sub(r"^[\s>→<\-–—:]+", "", text)             # leading arrows / dashes
    text = re.sub(r"\bTERMINATES? AT\b", " ", text)
    text = re.sub(r"\bVIA\b.*$", " ", text)                # route text follows VIA
    text = re.sub(r"[\s\-–—>]+$", "", text)                 # trailing dash / arrow
    return text


def normalise_place(text: str | None, abbreviations: dict[str, str], *, display: bool = True) -> str:
    """Shared normalisation for OCR destinations and reference endpoints."""
    text = strip_display_clutter(text or "") if display else unicodedata.normalize("NFKC", text or "").upper()
    text = re.sub(r"['’`]", "", text)                       # ST MICHAEL'S == ST MICHAELS
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    words = []
    for token in text.split():
        words.extend(abbreviations.get(token, token).split())
    words = [w for i, w in enumerate(words)
             if not (w == "BUS" and i + 1 < len(words) and words[i + 1] in ("INT", "TER"))]
    words = [w for w in words if w != "LOOP"]                 # "(loop)" annotation in the reference
    return " ".join(words)


# ---------------------------------------------------------------- reference

@dataclass
class Endpoint:
    key: str                      # normalised name
    name: str                     # first reference spelling, returned to the user
    services: set = field(default_factory=set)


class Reference:
    """Cleaned, indexed view of bus_information.csv."""

    def __init__(self, csv_path: Path, abbreviations: dict[str, str] | None = None):
        self.path = Path(csv_path)
        self.abbreviations = load_abbreviations() if abbreviations is None else abbreviations
        self.available = self.path.is_file()
        self.rows, self.issues = [], []
        if self.available:
            self._load()
        self.services: dict[str, list[dict]] = {}
        self.endpoints: dict[str, Endpoint] = {}
        for row in self.rows:
            self.services.setdefault(row["service"], []).append(row)
            for key in ("origin", "destination"):
                name = row[key]
                if not name:
                    continue
                norm = normalise_place(name, self.abbreviations, display=False)
                endpoint = self.endpoints.setdefault(norm, Endpoint(norm, name))
                endpoint.services.add(row["service"])
        self.service_endpoints = {service: sorted({normalise_place(r[k], self.abbreviations, display=False)
                                                   for r in rows for k in ("origin", "destination") if r[k]})
                                  for service, rows in self.services.items()}

    def _load(self):
        seen = set()
        with self.path.open(newline="", encoding="utf-8-sig") as stream:
            for number, raw in enumerate(csv.DictReader(stream), 2):
                row = {"service": normalise_service(raw.get("Route number")),
                       "origin": " ".join((raw.get("Origin") or "").split()),
                       "destination": " ".join((raw.get("Destination") or "").split()),
                       "line": number}
                key = (row["service"], row["origin"], row["destination"])
                if key in seen:
                    self.issues.append({"line": number, "issue": "exact duplicate row dropped"})
                    continue
                seen.add(key)
                if not row["origin"] or not row["destination"]:
                    self.issues.append({"line": number, "issue": "blank endpoint kept; only the filled endpoint is matchable"})
                self.rows.append(row)

    def has_service(self, service: str) -> bool:
        return service in self.services


# ---------------------------------------------------------------- scoring

@dataclass
class Settings:
    cutoff: float = 65.0          # 0-100 similarity needed to accept
    margin: float = 5.0           # lead over the next distinct endpoint
    scorer: str = "ratio"
    conflict: str = "withhold_both"   # or "keep_number": keep an exact service, withhold only the destination
    # No destination crop: "off" ignores the route crop; "check" uses it only to flag a number that does not
    # fit (never shown as the destination); "use" may also show it as the destination.
    route_as_destination: str = "off"
    # Destination crop present but it does not fit the service read: also try the route crop (the detector
    # sometimes swaps the two lines) and the whole display; either may then be shown.
    line_swap: bool = True

    def __post_init__(self):
        if isinstance(self.route_as_destination, bool):
            self.route_as_destination = "use" if self.route_as_destination else "off"


def score_candidates(text: str, keys, reference: Reference, scorer: str) -> list[tuple[float, str]]:
    """Score OCR text (whole and per line) against endpoint keys; best first."""
    function = SCORERS[scorer]
    whole = normalise_place(text, reference.abbreviations)
    lines = [normalise_place(line, reference.abbreviations) for line in (text or "").splitlines()]
    observations = [o for o in dict.fromkeys([whole, *lines]) if len(o.replace(" ", "")) >= 3]
    if not observations:
        return []
    scored = [(max(function(o, key) for o in observations), key) for key in keys]
    return sorted(scored, key=lambda pair: (-pair[0], pair[1]))


def decide(scored, settings: Settings) -> dict:
    """Accept the best candidate only above the cutoff and ahead of the next one."""
    if not scored:
        return {"status": "unread", "key": None, "score": None, "runner_up": None,
                "runner_up_score": None, "tied": []}
    (best, key), runner = scored[0], (scored[1] if len(scored) > 1 else (None, None))
    result = {"key": key, "score": round(best, 2), "runner_up": runner[1],
              "runner_up_score": round(runner[0], 2) if runner[0] is not None else None,
              "tied": [k for score, k in scored if score >= settings.cutoff and best - score < settings.margin]}
    if best < settings.cutoff:
        return {**result, "status": "below_cutoff"}
    if runner[0] is not None and best - runner[0] < settings.margin:
        return {**result, "status": "tie"}
    return {**result, "status": "accepted"}


# ---------------------------------------------------------------- matcher

def panel_parts(text: str | None, reference: Reference) -> tuple[list[str], str]:
    """Split whole-display OCR into service-number tokens (reference services only) and the rest."""
    tokens = (text or "").upper().replace("\n", " ").split()
    numbers = [t for t in (normalise_service(t) for t in tokens) if SERVICE_TOKEN.match(t) and reference.has_service(t)]
    rest = " ".join(t for t in tokens if normalise_service(t) not in numbers)
    return list(dict.fromkeys(numbers)), rest


class DisplayMatcher:
    def __init__(self, reference: Reference, settings: Settings | None = None):
        self.reference = reference
        self.settings = settings or Settings()

    def _destination(self, text, keys):
        return decide(score_candidates(text, keys, self.reference, self.settings.scorer), self.settings)

    def _name(self, key):
        return self.reference.endpoints[key].name if key else None

    def match(self, number: str | None = None, destination: str | None = None,
              route: str | None = None, panel: str | None = None, detected: bool = True) -> dict:
        """Match one display. Arguments are raw OCR strings; None means no crop."""
        ref, log = self.reference, []
        out = {"raw": {"number": number, "destination": destination, "route": route, "panel": panel},
               "service": None, "service_status": "unread", "destination": None,
               "destination_status": "unread", "destination_score": None,
               "runner_up": None, "runner_up_score": None, "candidate": None, "route_text": (route or "").strip() or None,
               "sources": {}, "log": log}

        if not detected or all(v is None for v in (number, destination, route, panel)):
            return self._finish(out, "no_fields", "no display fields detected")
        if not ref.available:
            return self._finish(out, "unresolved", "reference data unavailable; raw OCR kept")

        # ---- service number: dedicated crop and whole-display OCR
        crop_number = normalise_service(number) or None
        panel_numbers, panel_rest = panel_parts(panel, ref) if panel else ([], "")
        panel_number = panel_numbers[0] if len(panel_numbers) == 1 else None
        if len(panel_numbers) > 1:
            log.append(f"whole-display OCR has several service tokens {panel_numbers}; not used")
        valid_crop = crop_number if crop_number and ref.has_service(crop_number) else None

        if valid_crop and panel_number and valid_crop != panel_number and \
                (panel_number in valid_crop or valid_crop in panel_number):
            log.append(f"whole-display number {panel_number} looks like a partial read of crop number {valid_crop}; crop kept")
            panel_number = valid_crop if panel_number in valid_crop else panel_number
        candidates_numbers = []
        if valid_crop and panel_number and valid_crop != panel_number:
            candidates_numbers = [valid_crop, panel_number]
            log.append(f"crop number {valid_crop} and whole-display number {panel_number} disagree")
        elif valid_crop:
            candidates_numbers = [valid_crop]
            out["sources"]["service"] = ["crop", "panel"] if panel_number == valid_crop else ["crop"]
        elif panel_number and not crop_number:
            candidates_numbers = [panel_number]
            out["sources"]["service"] = ["panel"]
        elif crop_number and panel_number:
            log.append(f"crop number {crop_number} is not a reference service; whole-display number {panel_number} not substituted")
        not_in_reference = bool(crop_number) and not valid_crop

        # ---- destination evidence: the dedicated crop if there is one; otherwise the route crop
        #      (the detector sometimes labels the destination as route) and the whole display
        options, fallbacks = [], []
        if (destination or "").strip():
            options.append((destination, "crop"))
            if self.settings.line_swap:
                if (route or "").strip():
                    fallbacks.append((route, "route_swapped"))
                if panel_rest.strip():
                    fallbacks.append((panel_rest, "panel"))
        else:
            if self.settings.route_as_destination in ("check", "use") and (route or "").strip():
                options.append((route, "route"))
                log.append(f"no destination crop; route crop used ({self.settings.route_as_destination})")
            if panel_rest.strip():
                options.append((panel_rest, "panel"))
        for text, _ in options + fallbacks:
            if NOT_IN_SERVICE.search(strip_display_clutter(text)):
                out["destination_status"] = "not_in_service"
                return self._finish(out, "not_in_service", "depot / not-in-service message")

        all_keys = list(ref.endpoints)
        if candidates_numbers and options:
            # Number and destination: number narrows the search.
            def evaluate(items):
                return [(text, source, {s: self._destination(text, ref.service_endpoints[s]) for s in candidates_numbers})
                        for text, source in items]

            def showable(source):
                return source != "route" or self.settings.route_as_destination == "use"

            tried = evaluate(options)
            accepted = sorted({s for _, src, d in tried for s, x in d.items() if x["status"] == "accepted" and showable(src)})
            if not accepted and fallbacks:
                extra = evaluate(fallbacks)
                if any(x["status"] == "accepted" for _, _, d in extra for x in d.values()):
                    log.append("destination crop does not fit the service read; route crop / whole display tried "
                               "(detector may have swapped the lines)")
                    tried += extra
                    accepted = sorted({s for _, src, d in tried for s, x in d.items() if x["status"] == "accepted" and showable(src)})
            if len(candidates_numbers) > 1:
                if len(accepted) == 1:
                    service = accepted[0]
                    log.append(f"number dispute resolved by destination: {service}")
                else:
                    out["service_status"] = "disputed"
                    return self._finish(out, "unresolved", "crop and whole-display numbers disagree; destination did not resolve it")
            else:
                service = candidates_numbers[0]
            route_shown = self.settings.route_as_destination == "use"
            hits = sorted([(text, source, d[service]) for text, source, d in tried
                           if d[service]["status"] == "accepted" and showable(source)],
                          key=lambda h: -h[2]["score"])
            if len({h[2]["key"] for h in hits}) > 1:
                out.update(service=service, service_status="accepted", destination_status="tie",
                           sources={**out["sources"], "destination": [h[1] for h in hits]})
                log.append("route crop and whole display point to different endpoints of this service")
                return self._finish(out, "service_only", "destination sources disagree")
            if hits:
                text, source, restricted = hits[0]
                if len(hits) > 1:
                    source = [h[1] for h in hits]
            else:
                text, source, restricted = tried[0][0], tried[0][1], tried[0][2][service]
                if source == "route" and not route_shown and restricted["status"] == "accepted":
                    restricted = {**restricted, "status": "checked_only"}   # route fits this service: no conflict, not shown
            overall = self._destination(text, all_keys)
            other = overall["key"] and service not in ref.endpoints[overall["key"]].services
            strong_other = (not hits and restricted["status"] != "checked_only" and other and overall["score"] is not None and overall["score"] >= self.settings.cutoff
                            and overall["score"] - (restricted["score"] or 0) >= self.settings.margin)
            out["sources"]["destination"] = source if isinstance(source, list) else [source]
            if strong_other and self.settings.conflict == "keep_number":
                out.update(service=service, service_status="accepted", destination_status="conflict",
                           runner_up=self._name(overall["key"]), runner_up_score=overall["score"],
                           destination_score=restricted["score"])
                log.append(f"destination fits {self._name(overall['key'])} ({overall['score']}) better than service {service} ({restricted['score']}); destination withheld")
                self._finish(out, "conflict", "destination strongly matches a different service; service kept")
                out["message"] = MESSAGES["conflict_service_kept"]
                return out
            if strong_other:
                out.update(service_status="withheld", destination_status="conflict",
                           runner_up=self._name(overall["key"]), runner_up_score=overall["score"],
                           destination_score=restricted["score"])
                log.append(f"destination fits {self._name(overall['key'])} ({overall['score']}) better than service {service} ({restricted['score']})")
                return self._finish(out, "conflict", "destination strongly matches a different service")
            out.update(service=service, service_status="accepted")
            self._apply_destination(out, restricted)
            status = "matched" if out["destination_status"] == "accepted" else "service_only"
            return self._finish(out, status, f"destination {restricted['status']}")

        if candidates_numbers:
            if len(candidates_numbers) > 1:
                out["service_status"] = "disputed"
                return self._finish(out, "unresolved", "crop and whole-display numbers disagree; no destination to resolve it")
            service = candidates_numbers[0]
            out.update(service=service, service_status="accepted")
            endpoints = ref.service_endpoints[service]
            if len(endpoints) == 1:
                out.update(destination=self._name(endpoints[0]), destination_status="inferred")
                return self._finish(out, "matched", "destination inferred: service has one endpoint")
            if out["route_text"]:
                log.append("route text kept as read; reference has no road names")
            return self._finish(out, "service_only", "service has more than one endpoint; direction unknown")

        if options:
            # Destination only (no number, or a number missing from the reference).
            results = [(source, self._destination(text, all_keys)) for text, source in options
                       if source != "route" or self.settings.route_as_destination == "use"]
            if not results:
                if not_in_reference:
                    out["service_status"] = "not_in_reference"
                    return self._finish(out, "unable_to_detect", f"service {crop_number} not in reference")
                return self._finish(out, "route_text_only", "route text kept; reference has no road names")
            hits = sorted([(source, d) for source, d in results if d["status"] == "accepted"], key=lambda h: -h[1]["score"])
            if len({d["key"] for _, d in hits}) > 1:
                out["destination_status"] = "tie"
                out["sources"]["destination"] = [source for source, _ in hits]
                return self._finish(out, "unresolved", "route crop and whole display point to different destinations")
            source, overall = hits[0] if hits else results[0]
            out["sources"]["destination"] = [source for source, _ in hits] if hits else [source]
            self._apply_destination(out, overall)
            if not_in_reference:
                out["service_status"] = "not_in_reference"
                status = "destination_only" if out["destination_status"] == "accepted" else "unable_to_detect"
                return self._finish(out, status, f"service {crop_number} not in reference")
            if out["destination_status"] == "accepted":
                services = sorted(ref.endpoints[overall["key"]].services)
                if len(services) == 1:
                    out.update(service=services[0], service_status="inferred")
                    return self._finish(out, "matched", "service inferred: destination belongs to one service")
                out["service_status"] = "ambiguous"
                log.append(f"destination served by {len(services)} services")
                return self._finish(out, "destination_only", "destination accepted; several services share it")
            if overall["status"] == "tie":
                shared = set.intersection(*(ref.endpoints[k].services for k in overall["tied"]))
                if len(shared) == 1:
                    out.update(service=shared.pop(), service_status="inferred")
                    log.append(f"tied destinations {[self._name(k) for k in overall['tied']]} share one service")
                    return self._finish(out, "service_only", "destination tied; tied candidates share one service")
            return self._finish(out, "unresolved", f"destination {overall['status']}")

        if not_in_reference:
            out["service_status"] = "not_in_reference"
            return self._finish(out, "unable_to_detect", f"service {crop_number} not in reference")
        if out["route_text"]:
            return self._finish(out, "route_text_only", "route text kept; reference has no road names")
        if any((v or "").strip() for v in (number, destination, route, panel)):
            return self._finish(out, "unresolved", "text read but nothing matched")
        return self._finish(out, "unreadable", "fields detected but OCR returned no text")

    def _apply_destination(self, out, decision):
        out["destination_score"] = decision["score"]
        out["runner_up"] = self._name(decision.get("runner_up"))
        out["runner_up_score"] = decision.get("runner_up_score")
        if decision["status"] == "accepted":
            out.update(destination=self._name(decision["key"]), destination_status="accepted")
        else:
            out["destination_status"] = decision["status"]
            out["candidate"] = self._name(decision["key"])

    @staticmethod
    def _finish(out, status, reason):
        out.update(status=status, message=MESSAGES[status], reason=reason)
        return out
