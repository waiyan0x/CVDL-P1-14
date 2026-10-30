"""Put observed training status into the detector notebook and pause all models."""

import csv
from datetime import datetime
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/object_detection_benchmark.ipynb"
RUNS = ROOT / ".runtime/object_detection_benchmark/bf938f526d2c/runs"
MARKER = "### Training progress (recorded from local checkpoints)"


def yolo_status(name: str) -> str:
    run = RUNS / name
    history = run / "results.csv"
    if not history.is_file():
        return f"- **{name}:** not started."
    with history.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return f"- **{name}:** run directory exists; no completed epochs recorded."
    best = max(rows, key=lambda row: float(row["metrics/mAP50-95(B)"]))
    checkpoint = run / "weights/best.pt"
    return (
        f"- **{name}:** {len(rows)} epochs recorded; best observed validation "
        f"mAP50={float(best['metrics/mAP50(B)']):.4f}, "
        f"mAP50:95={float(best['metrics/mAP50-95(B)']):.4f} "
        f"at epoch {best['epoch']}. Best checkpoint "
        f"{'saved' if checkpoint.is_file() else 'missing'}."
    )


notebook = nbformat.read(NOTEBOOK, as_version=4)
for cell in notebook.cells:
    if cell.cell_type == "markdown" and "The notebook defaults to no training. Set `RUN_TRAINING=True`" in cell.source:
        before = "The notebook defaults to no training. Set `RUN_TRAINING=True` in the first code cell after preflight and dependencies are ready. Training can take hours, especially DETR on CPU. After training, set `RUN_TRAINING=False` and `RUN_BENCHMARK=True` to reload the saved checkpoints and calculate train/valid metrics. Once the validation choice is frozen, set `RUN_FINAL_TEST=True` and rerun with training still off for the one-time held-out measurement."
        after = "The notebook defaults to no training. To train one model, set `RUN_TRAINING=True` and only that model's `RUN_YOLO11N`, `RUN_YOLO11S`, or `RUN_DETR` switch to `True`, then run its own cell. Training can take hours, especially DETR. After all three are complete, set `RUN_TRAINING=False` and `RUN_BENCHMARK=True` to reload completed checkpoints and calculate train/valid metrics. Once the validation choice is frozen, set `RUN_FINAL_TEST=True` and rerun with training still off for the one-time held-out measurement."
        cell.source = cell.source.replace(before, after)
    if cell.cell_type != "code":
        continue
    if "RUN_TRAINING = False" in cell.source and "DATASET_ROOT" in cell.source:
        cell.source = cell.source.replace(
            "RUN_TRAINING = False       # Explicitly enable only after the verified-data preflight passes.",
            "RUN_TRAINING = False       # Master pause switch.",
        ).replace("640, 8, 42", "640, 4, 42")
        if "RUN_YOLO11N = False" not in cell.source:
            cell.source = cell.source.replace(
                "RUN_TRAINING = False       # Master pause switch.",
                "RUN_TRAINING = False       # Master pause switch.\n"
                "RUN_YOLO11N = False\nRUN_YOLO11S = False\nRUN_DETR = False",
            )
    elif "saved_runs = OUTPUT_ROOT" in cell.source:
        cell.source = cell.source.replace(
            "if checkpoint.is_file(): MODEL_PATHS[candidate] = str(checkpoint)",
            "if checkpoint.is_file() and (saved_runs / candidate / 'complete.txt').is_file():\n"
            "            MODEL_PATHS[candidate] = str(checkpoint)",
        ).replace(
            "    print(candidate, TRAINING_HISTORY[candidate])",
            "    (run_dir / 'complete.txt').write_text('Finished training; best.pt is selected by validation.\\n', encoding='utf-8')\n"
            "    print(candidate, TRAINING_HISTORY[candidate])",
        )
    elif "YOLO_DATA_YAML = make_yolo_view()" in cell.source:
        cell.source = cell.source.replace(
            "if DATA_READY and RUN_TRAINING:",
            "if DATA_READY and RUN_TRAINING and (RUN_YOLO11N or RUN_YOLO11S):",
        )
    elif "train_yolo('yolo11n')" in cell.source:
        cell.source = cell.source.replace(
            "if DATA_READY and RUN_TRAINING:",
            "if DATA_READY and RUN_TRAINING and RUN_YOLO11N:",
        )
    elif "train_yolo('yolo11s')" in cell.source:
        cell.source = cell.source.replace(
            "if DATA_READY and RUN_TRAINING:",
            "if DATA_READY and RUN_TRAINING and RUN_YOLO11S:",
        )
    elif "'detr-resnet-50' not in MODEL_PATHS" in cell.source:
        cell.source = cell.source.replace(
            "if DATA_READY and RUN_TRAINING and 'detr-resnet-50' not in MODEL_PATHS:",
            "if DATA_READY and RUN_TRAINING and RUN_DETR and 'detr-resnet-50' not in MODEL_PATHS:",
        )
    elif "benchmark_{suffix}.json" in cell.source:
        cell.source = cell.source.replace(
            "destination = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / f'benchmark_{suffix}.json'",
            "phase = 'test' if RUN_FINAL_TEST else 'validation'\n"
            "    destination = OUTPUT_ROOT / DATA_FINGERPRINT[:12] / f'benchmark_{suffix}_{phase}.json'",
        )

timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
status = "\n".join(
    [
        MARKER,
        "",
        f"Updated {timestamp}. These are training-time Ultralytics validation metrics; the common train/validation/test benchmark below has not run.",
        "",
        yolo_status("yolo11n"),
        yolo_status("yolo11s"),
        "- **DETR:** not started.",
        "",
        "YOLO11n finished under the 10-epoch early-stopping patience. YOLO11s began in the previous shared cell and was interrupted on request; its checkpoint is **partial** and must not be compared as a completed 30-epoch run. Training is paused by default. To train one model later, set `RUN_TRAINING=True` and only that model's `RUN_*` switch to `True`, then run its cell.",
    ]
)
for cell in notebook.cells:
    if cell.cell_type == "markdown" and cell.source.startswith(MARKER):
        cell.source = status
        break
else:
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "markdown" and "### 3a. YOLO11n" in cell.source:
            notebook.cells.insert(index, nbformat.v4.new_markdown_cell(status))
            break
nbformat.validate(notebook)
nbformat.write(notebook, NOTEBOOK)
print(NOTEBOOK)
