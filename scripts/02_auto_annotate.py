"""Annotation CLI; --help and the default plan never load a model."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from data_preparation.annotation_cli import main
    main()
