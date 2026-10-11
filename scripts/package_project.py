"""Create a portable ZIP without raw Kaggle images, caches, or local environments."""

from pathlib import Path
import os
from zipfile import ZIP_DEFLATED, ZipFile

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".ultralytics",
    "Ultralytics",
    ".matplotlib",
    ".venv",
    ".terraform",
    ".aws",
    ".kaggle",
    "node_modules",
    "dist",
    "runs",
    "raw",
    "material_dataset_kaggle",
    "rion_classifier_dataset",
    "rion_classifier_training",
    "__pycache__",
    "work",
}
EXCLUDED_FILES = {"yolo26n.pt", "yolo26n-cls.pt", "terraform.tfvars"}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    archive_path = root.parent / "RION.zip"
    checkpoint = root / "models" / "material-yolo.pt"
    classifier = root / "models" / "rion-classifier.pt"
    if not checkpoint.is_file() or not classifier.is_file():
        raise SystemExit("Both trained checkpoints are required: models/material-yolo.pt and models/rion-classifier.pt.")
    added = 0
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        # Prune large excluded datasets before descending into them. A sorted
        # rglob would still enumerate and sort every raw image despite omitting
        # those files from the archive.
        for current, directories, filenames in os.walk(root):
            directories[:] = sorted(name for name in directories if name not in EXCLUDED_DIRS)
            for filename in sorted(filenames):
                path = Path(current) / filename
                relative = path.relative_to(root)
                if (
                    path.name in EXCLUDED_FILES
                    or path.name.startswith("terraform.tfstate")
                    or path.suffix in {".cache", ".tfplan"}
                    or (path.name.endswith(".tfvars") and path.name != "terraform.tfvars.example")
                    or path == archive_path
                ):
                    continue
                if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
                    continue
                archive.write(path, Path("RION") / relative)
                added += 1
    print(f"Created {archive_path} with {added} files ({archive_path.stat().st_size:,} bytes).")
    print("Raw Kaggle data, converted image copies, training runs, package caches, and local environments are excluded.")


if __name__ == "__main__":
    main()
