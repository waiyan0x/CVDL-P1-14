"""Apply fresh-training cells from the builder while preserving notebook controls."""

import re
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
builder = (ROOT / "notebooks/build_object_detection_benchmark.py").read_text(encoding="utf-8")
prefix = builder.split("notebook = {'nbformat':", 1)[0]
namespace = {}
exec(compile(prefix, "build_object_detection_benchmark.py", "exec"), namespace)
templates = namespace["cells"]
notebook_path = ROOT / "notebooks/object_detection_benchmark.ipynb"
notebook = nbformat.read(notebook_path, as_version=4)


def find(cells, marker, kind):
    found = [cell for cell in cells if cell["cell_type"] == kind and marker in cell["source"]]
    if len(found) != 1:
        raise ValueError(f"Expected one {kind} cell containing {marker!r}, got {len(found)}")
    return found[0]


controls = (
    "RUN_TRAINING", "RUN_YOLO11N", "RUN_YOLO11S", "RUN_DETR",
    "RUN_BENCHMARK", "RUN_FINAL_TEST", "BENCHMARK_MODELS",
)
old_config = find(notebook.cells, "RUN_TRAINING =", "code")
new_config = find(templates, "RUN_TRAINING =", "code")["source"]
for name in controls:
    pattern = rf"^{name}\s*=.*$"
    old_line = re.search(pattern, old_config.source, flags=re.MULTILINE)
    if old_line is None:
        raise ValueError(f"Notebook control missing: {name}")
    new_config, count = re.subn(pattern, lambda _: old_line.group(0), new_config, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Builder control missing: {name}")
old_config.source = new_config
old_config.outputs = []
old_config.execution_count = None

for marker, kind in (
    ("Candidates: official COCO-pretrained", "markdown"),
    ("MODEL_PATHS, TRAINING_HISTORY", "code"),
    ("### 3a. YOLO11n", "markdown"),
    ("### 3b. YOLO11s", "markdown"),
    ("DETR fine-tuning pending.", "code"),
    ("Evidence saved:", "code"),
):
    current = find(notebook.cells, marker, kind)
    template = find(templates, marker, kind)
    current.source = template["source"]
    if kind == "code":
        current.outputs = []
        current.execution_count = None

nbformat.validate(notebook)
nbformat.write(notebook, notebook_path)
print(notebook_path)
