"""Download the pinned public printed-text baseline, not the app's private model."""

import argparse
import json
from pathlib import Path

REPOSITORY = "microsoft/trocr-base-printed"
REVISION = "93450be3f1ed40a930690d951ef3932687cc1892"
ROOT = Path(__file__).resolve().parents[1]


def main():
    from huggingface_hub import snapshot_download

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/trocr-base-printed")
    args = parser.parse_args()
    snapshot_download(REPOSITORY, revision=REVISION, local_dir=args.cache,
                      allow_patterns=["*.json", "merges.txt", "vocab.json", "model.safetensors"],
                      max_workers=2)
    (args.cache / "provenance.json").write_text(json.dumps(
        {"repository": REPOSITORY, "revision": REVISION}, indent=2)+"\n")
    print(f"Public pretrained baseline cached at {args.cache}; revision {REVISION}")


if __name__ == "__main__":
    main()
