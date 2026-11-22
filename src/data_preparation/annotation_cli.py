"""Lightweight annotation planning; model dependencies load only with --run."""
from pathlib import Path
import argparse
import json
from .config import ROOT, CUTOFF, IMAGE_EXTENSIONS

SPLIT_ALIASES = {"train": ("train",), "val": ("val", "valid", "validation"), "test": ("test",)}


def discover_images(input_root: Path, limit: int | None = 3) -> dict[str, list[Path]]:
    """Read existing splits without shuffling, moving, or inventing images."""
    input_root = Path(input_root)
    if limit is not None and limit < 1:
        raise ValueError("Image limit must be positive or None")
    result = {}
    for split, aliases in SPLIT_ALIASES.items():
        folders = [input_root / name for name in aliases if (input_root / name).is_dir()]
        if len(folders) != 1:
            raise ValueError(f"Expected one {split} input folder: {folders}")
        paths = sorted(p for p in folders[0].rglob("*")
                       if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                       and not p.name.lower().startswith("annotated_"))
        if not paths:
            raise ValueError(f"No images in {folders[0]}")
        result[split] = paths if limit is None else paths[:limit]
    return result


def main():
    parser = argparse.ArgumentParser(description="Plan or run isolated Autodistill EDS annotation")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/eds_autodistill/outputs/trial-001")
    parser.add_argument("--cutoff", default=CUTOFF)
    parser.add_argument("--limit", type=int, default=3, help="Images per split; 0 selects all")
    parser.add_argument("--run", action="store_true", help="Download weights and perform actual inference")
    parser.add_argument("--review", action="store_true", help="Open the local box editor immediately after inference")
    parser.add_argument("--negatives", type=Path, help="JSON list of explicitly reviewed negative input-relative paths")
    args = parser.parse_args()
    limit = None if args.limit == 0 else args.limit
    input_root = (args.input or ROOT / "data/raw" / args.cutoff / "splits").resolve()
    selected = discover_images(input_root, limit)
    print({split: len(paths) for split, paths in selected.items()})
    if not args.run:
        print("Plan only. Add --run to generate actual draft annotations.")
        return
    output = args.output.resolve()
    allowed = (ROOT / "experiments/eds_autodistill/outputs").resolve()
    if output == allowed or not output.is_relative_to(allowed):
        raise ValueError("Output must be a new subdirectory of experiments/eds_autodistill/outputs")
    if output.exists():
        raise FileExistsError(output)
    if not args.cutoff or Path(args.cutoff).name != args.cutoff or args.cutoff in {'.', '..'}:
        raise ValueError("Cutoff must be a single directory name")
    negatives = json.loads(args.negatives.read_text(encoding='utf-8')) if args.negatives else []
    if not isinstance(negatives, list) or not all(isinstance(path,str) for path in negatives):
        raise ValueError("Negatives JSON must be a list of input-relative paths")
    available = {path.relative_to(input_root).as_posix() for paths in selected.values() for path in paths}
    if set(negatives) - available:
        raise ValueError("Declared negatives must belong to the selected input images")
    from .annotation import LocalGroundingDINO, run_experiment
    result = run_experiment(LocalGroundingDINO(), input_root, output, args.cutoff, limit, set(negatives))
    print(result)
    print(f"Automatic checks: {output / 'automatic_review.json'}")
    print(f"Box overlays: {output / 'overlays'}")
    print(f'Open editor: python scripts/review_annotations.py --run-dir "{output}" --serve')
    if args.review:
        from .annotation_review import ReviewProject
        from .review_cli import serve
        serve(ReviewProject(output))


if __name__ == '__main__':
    main()
