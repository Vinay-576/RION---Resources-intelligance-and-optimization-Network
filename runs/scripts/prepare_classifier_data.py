"""Deduplicate and split Kaggle's folder-labeled waste images for YOLO classification."""

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path

CLASSES = ("battery", "biological", "cardboard", "clothes", "glass", "metal", "paper", "plastic", "shoes", "trash")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def find_class_root(source: Path) -> Path:
    candidates = [source, *(p for p in source.rglob("*") if p.is_dir())]
    for candidate in candidates:
        names = {p.name.lower() for p in candidate.iterdir() if p.is_dir()}
        if set(CLASSES).issubset(names):
            return candidate
    raise SystemExit(f"Could not find the 10 class folders beneath {source}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.hardlink_to(source)
    except OSError:
        shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/kaggle/garbage-classification-v2"))
    parser.add_argument("--output", type=Path, default=Path("data/rion_classifier_training"))
    parser.add_argument("--max-per-class", type=int, default=1000, help="Balanced cap per category; 0 uses all images.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source = find_class_root(args.source.resolve())
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"Output already exists: {output}. Move it aside before preparing a new split.")
    output.mkdir(parents=True)

    rng = random.Random(args.seed)
    seen_hashes: dict[str, str] = {}
    source_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = {split: Counter() for split in ("train", "val", "test")}
    duplicates = 0
    conflicting_labels = 0
    for label in CLASSES:
        candidates = sorted(path for path in (source / label).iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
        source_counts[label] = len(candidates)
        unique: list[Path] = []
        for path in candidates:
            fingerprint = sha256(path)
            prior_label = seen_hashes.get(fingerprint)
            if prior_label is not None:
                duplicates += 1
                if prior_label != label:
                    conflicting_labels += 1
                continue
            seen_hashes[fingerprint] = label
            unique.append(path)
        rng.shuffle(unique)
        if args.max_per_class > 0:
            unique = unique[: args.max_per_class]

        train_end = int(len(unique) * 0.70)
        val_end = train_end + int(len(unique) * 0.15)
        partitions = {
            "train": unique[:train_end],
            "val": unique[train_end:val_end],
            "test": unique[val_end:],
        }
        for split, paths in partitions.items():
            for index, path in enumerate(paths):
                link_or_copy(path, output / split / label / f"{index:05d}_{path.name}")
            split_counts[split][label] = len(paths)

    summary = {
        "dataset": "sumn2u/garbage-classification-v2/versions/8",
        "license": "MIT as listed by Kaggle",
        "source_root": source.relative_to(Path.cwd().resolve()).as_posix(),
        "seed": args.seed,
        "max_per_class": args.max_per_class,
        "source_counts": dict(source_counts),
        "split_counts": {split: dict(counts) for split, counts in split_counts.items()},
        "split_totals": {split: sum(counts.values()) for split, counts in split_counts.items()},
        "duplicates_removed": duplicates,
        "conflicting_duplicate_labels_removed": conflicting_labels,
        "class_names": list(CLASSES),
    }
    report = Path("reports/classifier-dataset-summary.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"YOLO classification folders written to: {output}")


if __name__ == "__main__":
    main()
