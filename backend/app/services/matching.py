"""App-facing matcher. Keeps the original RouteMatcher.match() contract and
delegates the decision to reference_matching.DisplayMatcher."""
import re
from pathlib import Path

from .reference_matching import DisplayMatcher, Reference, Settings, normalise_place, load_abbreviations

__all__ = ["RouteMatcher", "SERVICE_ID", "normalise"]

SERVICE_ID = re.compile(r"[0-9]{1,3}[A-Z]{0,2}")


def normalise(text: str) -> str:
    """Kept for callers of the old helper; uses the shared abbreviation table."""
    return normalise_place(text, load_abbreviations())


class RouteMatcher:
    def __init__(self, csv_path: Path, margin: float = 10.0, scorer: str = "ratio",
                 conflict: str = "keep_number", route_as_destination: str = "check"):
        cleaned = Path(csv_path).parent / "reference/bus_information.cleaned.csv"
        path = cleaned if cleaned.is_file() else Path(csv_path)
        self.reference = Reference(path)
        self.available = self.reference.available
        self.rows = self.reference.rows
        self.margin, self.scorer = margin, scorer
        self.conflict, self.route_as_destination = conflict, route_as_destination

    def split_display(self, text: str) -> tuple[str, str]:
        """Split whole-display OCR into (service, remaining text).

        The service is the first token shaped like a service ID, preferring one in the
        reference; the remaining text keeps its lines so road names stay separable.
        Nothing is corrected: an unknown token is returned as read.
        """
        tokens = re.findall(r"[A-Za-z0-9]+", text)
        candidates = [t for t in tokens if SERVICE_ID.fullmatch(t.upper())]
        service = next((t for t in candidates if self.reference.has_service(t.upper())),
                       candidates[0] if candidates else "")
        if not service:
            return "", text.strip()
        rest = re.sub(rf"(?<![A-Za-z0-9]){re.escape(service)}(?![A-Za-z0-9])", " ", text, count=1)
        return service.upper(), "\n".join(" ".join(line.split()) for line in rest.splitlines() if line.strip())

    def match(self, service: str, destination: str, threshold: float = .65, route: str = "") -> dict:
        """threshold is 0-1 here (app setting `similarity`, default .65 = cutoff 65); the matcher works on 0-100.
        Margin 10, ratio scoring, keep_number and route check are the settings chosen in
        evaluation/reference_matching (docs/REFERENCE_MATCHING.md). route = route crop OCR: used for the line swap
        and the "via" part of the announcement."""
        matcher = DisplayMatcher(self.reference, Settings(cutoff=threshold * 100, margin=self.margin, scorer=self.scorer,
                                                          conflict=self.conflict,
                                                          route_as_destination=self.route_as_destination))
        result = matcher.match(number=service or None, destination=destination or None, route=route or None)
        # "inferred": the destination belongs to one service only, so the announcement states that number too.
        accepted = result["service_status"] in ("accepted", "inferred")
        destination_confirmed = result["destination_status"] in ("accepted", "inferred")
        routes = [{"origin": r["origin"], "destination": r["destination"]}
                  for r in self.reference.services.get(result["service"], [])] if accepted else []
        if not self.available:
            status, reason = "unmatched", "Reference data unavailable; raw OCR retained."
        elif not accepted:
            status, reason = "unmatched", f"{result['message']} Raw OCR retained."
        elif destination_confirmed:
            status, reason = "matched", "Reference endpoint matched; travel direction is unverified."
        else:
            status, reason = "service_only", "Service found; destination not confirmed. Raw OCR retained."
        score = result["destination_score"]
        return {"status": status, "service": result["service"] if accepted else None,
                "endpoint": result["destination"] if status == "matched" else None,
                # Confirmed destination even when the service is not (shared by several services); read aloud.
                "destination": result["destination"] if destination_confirmed else None,
                "similarity": round(score / 100, 3) if score is not None else None,
                "reason": reason, "routes": routes, "announcement": result.get("announcement"), "detail": result}
