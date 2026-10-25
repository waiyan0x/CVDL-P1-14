"""Compatibility CLI; implementation lives in src/data_preparation/annotation.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from data_preparation.annotation_cli import main

if __name__ == "__main__":
    main()
