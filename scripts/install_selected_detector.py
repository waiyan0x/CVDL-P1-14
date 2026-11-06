"""Install the current v4 YOLO11s checkpoint; old baseline config stays selectable."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "evaluation/object_detection/01760a841333/runs/v4-reviewed-01/detector_config.json"
BASELINE_SOURCE = ROOT / ".runtime/object_detection_benchmark/bf938f526d2c/runs/baseline-01/yolo11s/weights/best.pt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    config_path = args.config.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = (args.source or ROOT / config.get("checkpoint_local_path", BASELINE_SOURCE)).expanduser().resolve()
    destination = (ROOT / config["checkpoint_install_path"]).resolve()
    expected = config["checkpoint_sha256"]
    target = destination if args.verify_only else source
    if not target.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {target}")
    actual = sha256(target)
    if actual != expected:
        raise RuntimeError(f"Checkpoint SHA-256 mismatch: expected {expected}, found {actual}")
    if not args.verify_only:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if sha256(destination) != expected:
            raise RuntimeError("Copied checkpoint failed SHA-256 verification.")
    print(json.dumps({"status": "verified" if args.verify_only else "installed",
                      "checkpoint": str(destination), "sha256": expected}, indent=2))


if __name__ == "__main__":
    main()
