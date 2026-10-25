# Project datasets

Dataset payloads are local and excluded from Git. Documentation and checksum
manifests remain tracked so the team can identify the exact files used.

```text
data/
  README.md
  manifests/
    2026-10-24.csv
  raw/YYYY-MM-DD/                     # Original collected images
  labelled/YYYY-MM-DD/roboflow/        # Base COCO export, including splits
  processed/YYYY-MM-DD/roboflow-augmented/ # Augmented COCO export
```

The previous `cutoff_24-10` and `cutoff_30-10` directories are now named
`2026-10-24` and `2026-10-30`. Dates identify the existing cutoff folders;
they do not establish whether batches are cumulative. The October 30 folders
are currently empty placeholders and are not stored by Git.

The augmented export was moved from `labelled` to `processed`. Image names,
annotations, and train/valid/test membership are unchanged. Its bundled README
identifies the export as Front EDS v2, generated on October 24, 2026.

## Retrieving data

Shared storage and an automated download workflow have not been configured yet.
Until they are, obtain the exact dataset from the data-preparation maintainer
and place it at the paths recorded in `manifests/2026-10-24.csv`. The manifest
records relative paths, byte sizes, and SHA-256 checksums for all 898 files.
Do not substitute a newly generated Roboflow export without recording a new
manifest and its source version.

For a future Roboflow download script, record the workspace, project, version,
and export format; supply credentials through environment variables. Raw
originals need their own shared storage location. DVC is an alternative for
versioning the complete raw and labelled snapshots against shared storage.

## Preparing new snapshots

Preserve raw originals. Record sources, cutoff semantics, class definitions,
split membership, preprocessing, and augmentation settings for each snapshot.
Keep validation and test sets consistent when comparing experiments and apply
training augmentation only to training images.

Ignoring dataset paths does not upload or back them up. Local data remains on
disk when switching branches. A cleanup commit removes payloads from the branch's
current tree; copies in earlier Git commits remain in repository history.
