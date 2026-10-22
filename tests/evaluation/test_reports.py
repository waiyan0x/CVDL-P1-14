import json
import hashlib

from backend.app.evaluation.reports import load_reports


def test_reports_without_reviewed_manifest_provenance_do_not_become_accuracy(tmp_path):
    directory = tmp_path / "evaluation/reports"
    directory.mkdir(parents=True)
    (directory / "invented.json").write_text(json.dumps({"accuracy": 0.99}))
    reports, warnings = load_reports(tmp_path)
    assert reports == []
    assert "invented.json" in warnings[0]


def test_detection_report_is_withheld_if_its_label_evidence_changes(tmp_path):
    directory = tmp_path / "evaluation/reports"
    directory.mkdir(parents=True)
    evidence = {}
    for name in ("model.pt", "image.jpg", "label.txt"):
        path = tmp_path / name
        path.write_bytes(name.encode())
        evidence[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {"schema_version": 1, "report_type": "detection_benchmark", "run_id": "run", "created_at": "2026-10-22",
              "dataset": {"id": "reviewed", "included": [{"image": "image.jpg", "sha256": evidence["image.jpg"],
                                                           "label": "label.txt", "label_sha256": evidence["label.txt"]}]},
              "detector": {"path": "model.pt", "sha256": evidence["model.pt"]},
              "protocol": {"iou": .5}, "metrics": {"recall": 1}}
    (directory / "detection.json").write_text(json.dumps(report))
    assert len(load_reports(tmp_path)[0]) == 1
    (tmp_path / "label.txt").write_text("changed annotation")
    reports, warnings = load_reports(tmp_path)
    assert reports == []
    assert "changed" in warnings[0]
