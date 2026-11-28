"""Format measured detector benchmarks as separate train, validation and test tables."""

from statistics import mean


SPLITS = (("train", "Train"), ("valid", "Validation"), ("test", "Test"))


def percentage(value):
    if value is None or value < 0:
        return "—"
    return f"{100 * value:.1f}"


def render_split_tables(benchmark, inventory, class_names, run_id):
    """Return Markdown; an unmeasured test split is explicitly left pending."""
    lines = [f"# Detector benchmark: {run_id}", ""]
    for split_key, title in SPLITS:
        lines.extend((f"## {title}", ""))
        measured = [(name, splits[split_key]) for name, splits in benchmark.items()
                    if split_key in splits]
        if not measured:
            lines.extend(("Held out; no measured results for this split yet.", ""))
            continue
        split_inventory = inventory.get(split_key, {})
        counts = split_inventory.get("boxes_by_class", {})
        lines.extend((
            f"Images: {split_inventory.get('images', '—')}; "
            f"negative images: {split_inventory.get('negative_images', '—')}.",
            "",
            "| Model | Class | Boxes (n) | mAP50 (%) | mAP50:95 (%) | Recall mAR@100 (%) |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ))
        for model, metrics in measured:
            by_class = metrics.get("by_class", {})
            for class_name in class_names:
                class_metrics = by_class.get(class_name, {})
                lines.append(
                    f"| {model} | {class_name} | {counts.get(class_name, 0):,} | "
                    f"{percentage(class_metrics.get('map50'))} | "
                    f"{percentage(class_metrics.get('map50_95'))} | "
                    f"{percentage(class_metrics.get('mar_100'))} |"
                )
            recall = metrics.get("mar_100")
            if recall is None:
                measured_recall = [by_class[name]["mar_100"] for name in class_names
                                   if name in by_class and by_class[name].get("mar_100") is not None
                                   and by_class[name]["mar_100"] >= 0]
                recall = mean(measured_recall) if measured_recall else None
            lines.append(
                f"| **{model}** | **All (avg)** | **{sum(counts.values()):,}** | "
                f"**{percentage(metrics.get('map50'))}** | "
                f"**{percentage(metrics.get('map50_95'))}** | "
                f"**{percentage(recall)}** |"
            )
        lines.append("")
    lines.append("Values are measured on the named split. A dash means the class metric is unavailable.")
    lines.append("")
    return "\n".join(lines)
