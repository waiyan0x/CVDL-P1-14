"""App-facing matcher. Keeps the original RouteMatcher.match() contract and
delegates the decision to reference_matching.DisplayMatcher."""
from pathlib import Path

from .reference_matching import DisplayMatcher, Reference, Settings, normalise_place, load_abbreviations

__all__ = ["RouteMatcher", "normalise"]


def normalise(text: str) -> str:
    """Kept for callers of the old helper; uses the shared abbreviation table."""
    return normalise_place(text, load_abbreviations())


class RouteMatcher:
    def __init__(self, csv_path: Path, margin: float = 5.0, scorer: str = "ratio"):
        cleaned = Path(csv_path).parent / "reference/bus_information.cleaned.csv"
        path = cleaned if cleaned.is_file() else Path(csv_path)
        self.reference = Reference(path)
        self.available = self.reference.available
        self.rows = self.reference.rows
        self.margin, self.scorer = margin, scorer

    def match(self, service: str, destination: str, threshold: float = .7) -> dict:
        """threshold is 0-1 here (app setting); the matcher works on 0-100."""
        matcher = DisplayMatcher(self.reference, Settings(cutoff=threshold * 100, margin=self.margin, scorer=self.scorer))
        result = matcher.match(number=service or None, destination=destination or None)
        accepted = result["service_status"] == "accepted"
        routes = [{"origin": r["origin"], "destination": r["destination"]}
                  for r in self.reference.services.get(result["service"], [])] if accepted else []
        if not self.available:
            status, reason = "unmatched", "Reference data unavailable; raw OCR retained."
        elif not accepted:
            status, reason = "unmatched", f"{result['message']} Raw OCR retained."
        elif result["destination_status"] in ("accepted", "inferred"):
            status, reason = "matched", "Reference endpoint matched; travel direction is unverified."
        else:
            status, reason = "service_only", "Service found; destination not confirmed. Raw OCR retained."
        score = result["destination_score"]
        return {"status": status, "service": result["service"] if accepted else None,
                "endpoint": result["destination"] if status == "matched" else None,
                "similarity": round(score / 100, 3) if score is not None else None,
                "reason": reason, "routes": routes, "detail": result}
