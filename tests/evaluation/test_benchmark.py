import hashlib
import json

from PIL import Image

from backend.app.evaluation.benchmark import run_benchmark
from backend.app.evaluation.manifest import load_manifest
from backend.app.evaluation.reports import load_reports


class ComparisonFixture:
    def __init__(self, directory):
        model = directory / "fixture-weights.bin"
        model.write_bytes(b"test fixture weights")
        self.artifacts = {str(model): hashlib.sha256(model.read_bytes()).hexdigest()}

    def models(self):
        return {"detector": {"id": "detector", "artifact_files": self.artifacts},
                "ocr_engines": [{"id": engine, "available": engine != "trocr", "artifact_files": self.artifacts}
                                for engine in ("easyocr", "tesseract", "trocr")], "runtime_hardware": {"machine": "test"}}

    def compare(self, path, options):
        self.calls = getattr(self, "calls", 0) + 1
        return {"width": 50, "height": 20, "detections": [], "comparisons": [
            {"backend": "easyocr", "status": "success", "error": None,
             "result": {"results": [{"screen": {"box": [0, 0, 50, 20]},
                                     "fields": {"bus_number": {"raw": "3"}}}],
                        "timings": {"total_ms": 8, "ocr_ms": 5}}},
            {"backend": "tesseract", "status": "error", "result": None, "error": "OCR failed"},
            {"backend": "trocr", "status": "unavailable", "result": None, "error": "Missing weights"}]}


def test_benchmark_records_warmup_failures_identity_and_missing_engine_without_invented_scores(tmp_path):
    image = tmp_path / "bus.png"
    Image.new("RGB", (100, 40)).save(image)
    manifest_file = tmp_path / "reviewed.json"
    manifest_file.write_text(json.dumps({"schema_version": 1,
        "dataset": {"id": "reviewed-fixture", "version": "1", "split": "held_out"},
        "review": {"reviewed": True, "reviewer": "Test reviewer", "reviewed_at": "2026-10-22"},
        "images": [{"id": "bus", "path": "bus.png", "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                    "displays": [{"id": "screen", "box": [0, 0, 100, 40], "bus_number": "3", "destination": None}]}]}))
    fixture = ComparisonFixture(tmp_path)
    report = run_benchmark(load_manifest(manifest_file), tmp_path, fixture, {"detection": .3}, warmup=2)
    assert fixture.calls == 3
    assert report["protocol"]["warmup_requests"] == 2
    assert report["engines"]["easyocr"]["metrics"]["complete_exact_accuracy"] == 1
    assert report["engines"]["tesseract"]["metrics"]["complete_exact_accuracy"] == 0
    assert report["engines"]["tesseract"]["failure_count"] == 1
    assert report["engines"]["trocr"]["metrics"] is None
    assert report["engines"]["trocr"]["failure_count"] == 0
    assert report["engines"]["easyocr"]["metrics"]["latency_ms"]["count"] == 1
    directory = tmp_path / "evaluation/reports"
    directory.mkdir(parents=True)
    (directory / "reviewed.json").write_text(json.dumps(report))
    loaded, warnings = load_reports(tmp_path)
    assert len(loaded) == 1
    assert warnings == []
