"""Copy recorded result/checklist markdown from the builder into the notebook."""

from pathlib import Path
import os
import shutil

import nbformat


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "notebooks/build_object_detection_benchmark.py"
NOTEBOOK = ROOT / "notebooks/object_detection_benchmark.ipynb"

source = BUILDER.read_text(encoding="utf-8")
namespace = {}
exec(compile(source.split("notebook = {'nbformat':", 1)[0], str(BUILDER), "exec"), namespace)
templates = namespace["cells"]
notebook = nbformat.read(NOTEBOOK, as_version=4)


def one(cells, markers):
    matches = [
        cell for cell in cells
        if cell["cell_type"] == "markdown" and any(marker in cell["source"] for marker in markers)
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one markdown cell for {markers}, found {len(matches)}")
    return matches[0]


result_template = one(templates, ("### Recorded `baseline-01` benchmark results",))
result_cell = one(notebook.cells, ("### Result and interpretation log", "### Recorded `baseline-01` benchmark results"))
result_cell.source = result_template["source"]

checklist_template = one(templates, ("## 7. Outstanding task-allocation checklist",))
checklist_cell = one(notebook.cells, ("## 7. Outstanding task-allocation checklist",))
checklist_cell.source = checklist_template["source"]

config_matches = [
    cell for cell in notebook.cells
    if cell.cell_type == "code" and "RUN_TRAINING =" in cell.source and "RUN_FINAL_TEST =" in cell.source
]
if len(config_matches) != 1:
    raise ValueError(f"Expected one run-control cell, found {len(config_matches)}")
config = config_matches[0]
replacements = {
    "RUN_TRAINING = True": "RUN_TRAINING = False",
    "RUN_BENCHMARK = True": "RUN_BENCHMARK = False",
    "RUN_FINAL_TEST = True": "RUN_FINAL_TEST = False",
    "BENCHMARK_MODELS = ('yolo11n', 'yolo11s', 'detr-resnet-50')": "BENCHMARK_MODELS = ('yolo11s',)",
    "OPERATING_CONF, YOLO_NMS_IOU = 0.30, 0.70": "OPERATING_CONF, YOLO_NMS_IOU = 0.20, 0.70",
    "BENCHMARK_MODELS = ('yolo11s',)  # Choose one completed model per run, or list all three.": "BENCHMARK_MODELS = ('yolo11s',)  # Validation-selected model; list all three only for validation comparison.",
    "OPERATING_CONF, YOLO_NMS_IOU = 0.20, 0.70  # Freeze from validation before opening test.": "OPERATING_CONF, YOLO_NMS_IOU = 0.20, 0.70  # Validation-selected deployment settings.",
}
for before, after in replacements.items():
    config.source = config.source.replace(before, after)

nbformat.validate(notebook)
temporary = NOTEBOOK.with_suffix(".ipynb.tmp")
temporary.write_text(nbformat.writes(notebook), encoding="utf-8")
os.replace(temporary, NOTEBOOK)

run_root = ROOT / ".runtime/object_detection_benchmark/bf938f526d2c/runs/baseline-01"
archive_root = ROOT / "evaluation/object_detection/bf938f526d2c/runs/baseline-01"
for phase in ("validation", "test"):
    source_report = run_root / f"benchmark_yolo11n_yolo11s_detr-resnet-50_{phase}.json"
    if not source_report.is_file():
        raise FileNotFoundError(source_report)
    shutil.copy2(source_report, archive_root / f"combined_{phase}.json")
print(NOTEBOOK)
