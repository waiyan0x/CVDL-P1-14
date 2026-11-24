"""Pin and fetch the official English PaddleOCR v5 inference artifact only."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.request


REPOSITORY = "PaddlePaddle/en_PP-OCRv5_mobile_rec"
FILES = ("inference.json", "inference.pdiparams", "inference.yml")


def fetch(output, revision=None):
    if output.exists():
        raise FileExistsError(f"Refusing existing model directory: {output}")
    url = f"https://huggingface.co/api/models/{REPOSITORY}" + (f"/revision/{revision}" if revision else "")
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    resolved = metadata["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise ValueError("Expected immutable upstream commit SHA")
    names = {item["rfilename"] for item in metadata["siblings"]}
    if not set(FILES) <= names:
        raise ValueError("Official model is missing expected inference files")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".paddle-fetch-", dir=output.parent) as tmp:
        model = Path(tmp)/"model"
        model.mkdir()
        hashes = {}
        for name in FILES:
            with urllib.request.urlopen(f"https://huggingface.co/{REPOSITORY}/resolve/{resolved}/{name}", timeout=60) as response:
                with (model/name).open("xb") as handle:
                    while chunk := response.read(1024*1024):
                        handle.write(chunk)
            hashes[name] = hashlib.sha256((model/name).read_bytes()).hexdigest()
        (model/"provenance.json").write_text(json.dumps({"repository": REPOSITORY,
            "revision": resolved, "files_sha256": hashes, "role": "public_pretrained_baseline"}, indent=2)+'\n')
        if output.exists():
            raise FileExistsError(output)
        model.rename(output)
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", help="Optional upstream commit; otherwise resolve and record main once")
    args = parser.parse_args()
    print(fetch(args.output, args.revision))


if __name__ == "__main__":
    main()
