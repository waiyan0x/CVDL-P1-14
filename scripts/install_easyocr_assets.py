"""Download EasyOCR English assets into the app's ignored local cache."""

from pathlib import Path

import easyocr


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "easyocr"


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    easyocr.Reader(["en"], gpu=False, model_storage_directory=str(CACHE),
                   download_enabled=True, verbose=False)
    print(f"EasyOCR assets ready: {CACHE}")


if __name__ == "__main__":
    main()
