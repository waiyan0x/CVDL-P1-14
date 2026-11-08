"""Execute the detector notebook and persist outputs after each cell."""

from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient


def main() -> None:
    notebook_path = Path(__file__).resolve().parents[1] / "notebooks" / "object_detection_benchmark.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=None,
        kernel_name="cvdl-detector",
        resources={"metadata": {"path": str(notebook_path.parent.parent)}},
    )
    with client.setup_kernel():
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type != "code":
                continue
            print(f"Running notebook cell {index + 1}/{len(notebook.cells)}", flush=True)
            try:
                client.execute_cell(cell, index)
            finally:
                nbformat.write(notebook, notebook_path)
    print(f"Saved executed notebook: {notebook_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Notebook execution stopped: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
