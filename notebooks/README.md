# Visual checks only

Open [data_visual_checks.ipynb](data_visual_checks.ipynb) and Run All with a kernel
that has the root `requirements.txt` installed. Run from here or the repository
root; image paths are resolved against the repository automatically.

The notebook has only two displays:

1. Whole-image before/after pairs from three original training images, separately for
   brightness, rotation, salt/pepper noise and Gaussian blur. Fixed endpoint
   parameters make individual effects visible; the production export randomly
   combines transforms. Each pair shows the complete image with no bbox crops or overlays.
2. One Matplotlib row of three manually reviewed examples for each of the eight
   scene categories in [IMAGE_CATEGORIES.md](../data/IMAGE_CATEGORIES.md).

Sample filenames, hashes and observations live in
[preview_samples.json](preview_samples.json).
This JSON is used only by the visual notebook and its plotting helpers.
The preparation and model-data loading commands do not use it.
The samples are illustrative examples, not exhaustive category assignments. Rear views
and information screens illustrate exclusions, not new bbox classes. Missing or
changed sample files raise an actionable error; no substitute image is invented.

Transforms run only in memory for plotting. The notebook never writes datasets,
generates labels, downloads models, resplits images or performs model training.
Execute the [scripts](../scripts/README.md) for those preparation phases.
Plots are generated locally; commit the notebook with outputs cleared to keep
dataset images out of Git. The previous execution notebooks have been removed.
