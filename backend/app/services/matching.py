"""Conservative matching: recognised service restricts endpoint candidates."""
import csv
import re
from pathlib import Path

from rapidfuzz import fuzz

SERVICE_ID = re.compile(r"[0-9]{1,3}[A-Z]{0,2}")


def normalise(text: str) -> str:
    text = re.sub(r"[^A-Z0-9 ]", " ", text.upper())
    for long, short in [("INTERCHANGE", "INT"), ("TERMINAL", "TER"), ("STATION", "STN")]:
        text = re.sub(rf"\b{long}\b", short, text)
    text = re.sub(r"\bBUS (?=INT\b|TER\b)", "", text)
    return " ".join(text.split())


class RouteMatcher:
    def __init__(self, csv_path: Path):
        with csv_path.open(newline="", encoding="utf-8-sig") as stream:
            self.rows = list(csv.DictReader(stream))
        self.services = {r["Route number"].upper() for r in self.rows}

    def split_display(self, text: str) -> tuple[str, str]:
        """Split whole-display OCR into (service, remaining text).

        The service is the first token shaped like a service ID, preferring one in the
        reference; the remaining text keeps its lines so road names stay separable.
        Nothing is corrected: an unknown token is returned as read.
        """
        tokens = re.findall(r"[A-Za-z0-9]+", text)
        candidates = [t for t in tokens if SERVICE_ID.fullmatch(t.upper())]
        service = next((t for t in candidates if t.upper() in self.services), candidates[0] if candidates else "")
        if not service:
            return "", text.strip()
        rest = re.sub(rf"(?<![A-Za-z0-9]){re.escape(service)}(?![A-Za-z0-9])", " ", text, count=1)
        return service.upper(), "\n".join(" ".join(line.split()) for line in rest.splitlines() if line.strip())

    def match(self, service: str, destination: str, threshold: float = .7) -> dict:
        service = re.sub(r"\s+", "", service.upper())
        # Number correction is deliberately avoided: 133 must not become 13.
        candidates = [r for r in self.rows if r["Route number"].upper() == service]
        if not candidates:
            return {"status": "unmatched", "service": None, "endpoint": None,
                    "similarity": None, "reason": "No exact service match; raw OCR retained.", "routes": []}
        routes = list(dict.fromkeys((r["Origin"], r["Destination"]) for r in candidates))
        reference = [{"origin": a, "destination": b} for a, b in routes]
        observed = normalise(destination)
        if len(observed.replace(" ", "")) < 4:
            return {"status": "service_only", "service": service, "endpoint": None,
                    "similarity": None, "reason": "Service found; destination not confirmed.", "routes": reference}
        observations = [observed] + [normalise(line) for line in destination.splitlines()
                                      if len(normalise(line).replace(' ', '')) >= 4]
        scored = [(max(fuzz.ratio(line, normalise(r[key])) for line in observations) / 100, r[key])
                  for r in candidates for key in ("Origin", "Destination") if r[key].strip()]
        score, endpoint = max(scored, key=lambda pair: pair[0], default=(0, None))
        accepted = score >= threshold
        return {"status": "matched" if accepted else "service_only", "service": service,
                "endpoint": endpoint if accepted else None, "similarity": round(score, 3),
                "reason": "Reference endpoint matched; travel direction is unverified." if accepted
                          else "Destination similarity below threshold; raw OCR retained.", "routes": reference}
