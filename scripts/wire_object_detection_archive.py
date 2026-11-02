"""Wire the existing notebook to the results archive without resetting user switches."""

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/object_detection_benchmark.ipynb"
notebook = nbformat.read(NOTEBOOK, as_version=4)


def add_after(source, anchor, addition):
    if addition.strip() in source:
        return source
    if anchor not in source:
        raise ValueError(f"Notebook anchor missing: {anchor}")
    return source.replace(anchor, anchor + addition, 1)


for cell in notebook.cells:
    if cell.cell_type == "markdown":
        cell.source = cell.source.replace(
            "The checkpoint and epoch history are saved under `.runtime/`.",
            "The run is saved under `.runtime/` and mirrored to `evaluation/object_detection/`.",
        )
        continue
    if cell.cell_type != "code":
        continue
    original = cell.source
    if "from collections import Counter" in cell.source:
        cell.source = add_after(
            cell.source,
            "sys.path.insert(0, str(ROOT / 'src'))",
            "\nsys.path.insert(0, str(ROOT / 'scripts'))\n"
            "from object_detection_artifacts import archive_yolo_run, archive_detr_epoch, archive_benchmark",
        )
    elif "def train_yolo(candidate):" in cell.source:
        cell.source = add_after(
            cell.source,
            "        checkpoint = saved_runs / candidate / 'weights/best.pt'",
            "\n        if (saved_runs / candidate / 'results.csv').is_file():\n"
            "            archive_yolo_run(ROOT, DATA_FINGERPRINT, candidate, saved_runs / candidate)",
        )
        cell.source = add_after(
            cell.source,
            "    (run_dir / 'complete.txt').write_text('Finished training; best.pt is selected by validation.\\n', encoding='utf-8')",
            "\n    archive_yolo_run(ROOT, DATA_FINGERPRINT, candidate, run_dir)",
        )
    elif "DETR fine-tuning pending." in cell.source:
        cell.source = add_after(
            cell.source,
            "            processor.save_pretrained(detr_dir)",
            "\n        archive_detr_epoch(ROOT, DATA_FINGERPRINT, history, detr_dir if detr_dir.is_dir() else None)",
        )
        cell.source = add_after(
            cell.source,
            "    (detr_dir / 'complete.txt').write_text('Finished DETR fine-tuning; checkpoint selected by validation loss.\\n', encoding='utf-8')",
            "\n    archive_detr_epoch(ROOT, DATA_FINGERPRINT, history, detr_dir)",
        )
    elif "destination.write_text(json.dumps(report, indent=2)" in cell.source:
        cell.source = add_after(
            cell.source,
            "    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')",
            "\n    for name in BENCHMARK_MODELS:\n"
            "        archive_benchmark(ROOT, DATA_FINGERPRINT, name, phase, report)",
        )
    if cell.source != original:
        cell.outputs = []
        cell.execution_count = None

nbformat.validate(notebook)
nbformat.write(notebook, NOTEBOOK)
print(NOTEBOOK)
