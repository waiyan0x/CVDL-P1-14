"""Check v9 A/B settings and artifact separation without running a detector."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import train_object_detection as trainer


@pytest.mark.parametrize("base,variant,size,translate,scale,hsv_v,box", [
    ("yolo11n", "gentle_aug", 640, 0.02, 0.10, 0.08, 7.5),
    ("yolo11n", "localization", 800, 0.0, 0.0, 0.0, 8.5),
    ("yolo11s", "gentle_aug", 640, 0.02, 0.10, 0.08, 7.5),
    ("yolo11s", "localization", 800, 0.0, 0.0, 0.0, 8.5),
])
def test_yolo_variant_uses_published_weight_and_separate_archive(
        tmp_path, monkeypatch, base, variant, size, translate, scale, hsv_v, box):
    fingerprint = "a" * 64
    run_id = "v9-tuning-01"
    run_name = f"{base}-{variant}"
    output = tmp_path / "output"
    run_dir = output / fingerprint[:12] / "runs" / run_id / run_name
    pretrained_root = tmp_path / "pretrained"
    pretrained_root.mkdir()
    pretrained = pretrained_root / f"{base}.pt"
    pretrained.write_bytes(b"published weight")
    monkeypatch.setenv("EDS_PRETRAINED_ROOT", str(pretrained_root))
    monkeypatch.setenv("EDS_ARCHIVE_ROOT", str(output))
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("EDS_YOLO_BACKUP_ROOT", str(backup_root))
    monkeypatch.setattr(trainer, "yolo_view", lambda *unused: tmp_path / "data.yaml")
    calls = {}

    class FakeYOLO:
        def __init__(self, weight):
            calls["weight"] = weight

        def train(self, **settings):
            calls["settings"] = settings
            chosen = Path(settings["project"]) / settings["name"]
            (chosen / "weights").mkdir(parents=True)
            (chosen / "weights/best.pt").write_bytes(b"best")
            (chosen / "weights/last.pt").write_bytes(b"last")
            (chosen / "results.csv").write_text("epoch,metrics/mAP50-95(B)\n1,0.2\n", encoding="utf-8")
            (chosen / "args.yaml").write_text(f"imgsz: {size}\nbatch: 4\n", encoding="utf-8")
            self.trainer = SimpleNamespace(save_dir=chosen)

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    args = SimpleNamespace(model=base, variant=variant, epochs=60,
                           image_size=size, batch_size=4, seed=42,
                           workers=4, run_id=run_id)
    trainer.train_yolo(args, {}, fingerprint, output, run_dir, "cuda")

    assert calls["weight"] == str(pretrained)
    settings = calls["settings"]
    assert settings["name"] == run_name
    assert settings["imgsz"] == size
    assert settings["translate"] == translate
    assert settings["scale"] == scale
    assert settings["hsv_v"] == hsv_v
    assert settings["box"] == box
    assert settings["mosaic"] == settings["mixup"] == settings["fliplr"] == 0.0
    assert (run_dir / "complete.txt").is_file()
    experiment = json.loads((run_dir / "experiment.json").read_text(encoding="utf-8"))
    assert experiment["dataset_manifest_sha256"] == fingerprint
    assert experiment["published_starting_weight"] == str(pretrained)
    assert (run_dir / "checkpoints/best.pt").read_bytes() == b"best"
    assert (backup_root / fingerprint[:12] / "runs" / run_id / run_name / "best.pt").read_bytes() == b"best"
    assert not (output / fingerprint[:12] / "runs" / run_id / base).exists()
