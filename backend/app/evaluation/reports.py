"""Read explicitly identified evaluation artifacts without fabricating missing metrics."""
import json
import re
from pathlib import Path

from .provenance import file_hash


def _is_hash(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_report(report: dict) -> None:
    if not isinstance(report, dict):
        raise ValueError("Report must be a JSON object.")
    if report.get("schema_version") != 1 or not report.get("run_id") or not report.get("created_at"):
        raise ValueError("Missing report identity or supported schema.")
    kind = report.get("report_type")
    if kind == "reviewed_manifest_benchmark":
        provenance = report.get("provenance", {})
        review = provenance.get("review", {})
        if not _is_hash(provenance.get("manifest_sha256")) or review.get("reviewed") is not True:
            raise ValueError("Missing reviewed transcription provenance.")
        if not review.get("reviewer") or not review.get("reviewed_at") or not report.get("engines"):
            raise ValueError("Missing reviewer or engine measurements.")
        if not provenance.get("manifest_path") or not provenance.get("images") or not provenance.get("model_files"):
            raise ValueError("Missing re-verifiable image, manifest or model evidence.")
    elif kind == "detection_benchmark":
        if not _is_hash(report.get("detector", {}).get("sha256")) or not report.get("metrics"):
            raise ValueError("Missing detector identity or measured metrics.")
        if not report.get("dataset", {}).get("included"):
            raise ValueError("Missing labelled evaluation image evidence.")
    else:
        raise ValueError("Unknown evaluation report type.")
    if not report.get("dataset", {}).get("id") or not report.get("protocol"):
        raise ValueError("Missing dataset identity or evaluation protocol.")


def _verify_file(root: Path, name: str, expected: str) -> None:
    path = Path(name)
    path = path if path.is_absolute() else root / path
    if not _is_hash(expected) or not path.is_file() or file_hash(path) != expected:
        raise ValueError(f"Evidence is missing or changed: {path.name}")


def verify_evidence(report: dict, root: Path) -> None:
    if report["report_type"] == "detection_benchmark":
        detector = report["detector"]
        _verify_file(root, detector["path"], detector["sha256"])
        for image in report["dataset"]["included"]:
            _verify_file(root, image["image"], image["sha256"])
            _verify_file(root, image["label"], image["label_sha256"])
    else:
        provenance = report["provenance"]
        _verify_file(root, provenance["manifest_path"], provenance["manifest_sha256"])
        for image in provenance["images"]:
            _verify_file(root, image["path"], image["sha256"])
        for files in provenance["model_files"].values():
            for name, digest in files.items():
                _verify_file(root, name, digest)


def load_reports(root: Path) -> tuple[list[dict], list[str]]:
    candidates = set((root / "evaluation/reports").glob("*.json"))
    runtime_report = root / ".runtime/evaluation/detection.json"
    if runtime_report.is_file():
        candidates.add(runtime_report)
    reports, warnings = [], []
    for path in sorted(candidates):
        try:
            if path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Report exceeds the supported 32 MB size.")
            report = json.loads(path.read_text(encoding="utf-8"))
            validate_report(report)
            verify_evidence(report, root)
            report["evidence_status"] = "Current source files match recorded SHA256 evidence."
            report["file"] = str(path.relative_to(root))
            # Full outcomes remain in the report artifact; the web page receives representative examples.
            report.pop("outcomes", None)
            report["examples"] = report.get("examples", [])[:12]
            reports.append(report)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            warnings.append(f"Ignored {path.name}: {exc}")
    return sorted(reports, key=lambda report: report["created_at"], reverse=True), warnings
