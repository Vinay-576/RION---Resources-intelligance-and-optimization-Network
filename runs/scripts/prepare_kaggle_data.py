"""Convert the Kaggle COCO bounding-box annotations into YOLO format."""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path


def locate_split(source: Path, names: tuple[str, ...]) -> tuple[str, Path] | None:
    """Find a dataset split even if KaggleHub nested the extracted directory."""
    for name in names:
        candidates = [source / name, *source.glob(f"**/{name}")]
        for candidate in candidates:
            if candidate.is_dir() and (candidate / "_annotations.coco.json").is_file():
                return name, candidate
    return None


def safe_image_path(split_dir: Path, file_name: str) -> Path:
    candidate = (split_dir / file_name).resolve()
    if split_dir.resolve() not in candidate.parents:
        raise ValueError(f"Unsafe image path in COCO annotation: {file_name}")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/kaggle/malaysian-trash-annotation"))
    parser.add_argument("--output", type=Path, default=Path("data/material_dataset_kaggle"))
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    project_root = Path(__file__).resolve().parents[1]
    split_specs = [("train", ("train",)), ("val", ("valid", "val")), ("test", ("test",))]
    split_payloads: list[tuple[str, Path, dict[str, object]]] = []
    instance_counts: Counter[str] = Counter()
    image_counts: dict[str, int] = {}
    reference_classes: list[str] | None = None

    for target_split, source_names in split_specs:
        located = locate_split(source, source_names)
        if located is None:
            if target_split == "val":
                raise FileNotFoundError(f"Could not find a validation split ({', '.join(source_names)}) below {source}")
            if target_split == "test":
                continue
            raise FileNotFoundError(f"Could not find the train split below {source}")
        _, split_dir = located
        payload = json.loads((split_dir / "_annotations.coco.json").read_text(encoding="utf-8"))
        categories = sorted(payload["categories"], key=lambda category: int(category["id"]))
        names = [str(category["name"]).strip().lower().replace("-", "_").replace(" ", "_") for category in categories]
        if reference_classes is None:
            reference_classes = names
        elif names != reference_classes:
            raise ValueError(f"Class list differs in {split_dir}; dataset splits must share one taxonomy.")
        category_to_name = {
            int(category["id"]): str(category["name"]).strip().lower().replace("-", "_").replace(" ", "_")
            for category in categories
        }
        for annotation in payload["annotations"]:
            if not int(annotation.get("iscrowd", 0)):
                instance_counts[category_to_name[int(annotation["category_id"])]] += 1
        split_payloads.append((target_split, split_dir, payload))
        image_counts[target_split] = len(payload["images"])

    if not reference_classes:
        raise SystemExit(f"No COCO categories found below {source}")
    classes = [name for name in reference_classes if instance_counts[name] > 0]
    class_to_index = {name: index for index, name in enumerate(classes)}
    converted_counts: Counter[str] = Counter()

    for target_split, split_dir, payload in split_payloads:
        category_to_name = {
            int(category["id"]): str(category["name"]).strip().lower().replace("-", "_").replace(" ", "_")
            for category in payload["categories"]
        }
        image_by_id = {int(image["id"]): image for image in payload["images"]}
        annotations: dict[int, list[dict[str, object]]] = {image_id: [] for image_id in image_by_id}
        for annotation in payload["annotations"]:
            if not int(annotation.get("iscrowd", 0)):
                annotations.setdefault(int(annotation["image_id"]), []).append(annotation)

        for image_id, image in image_by_id.items():
            image_path = safe_image_path(split_dir, str(image["file_name"]))
            if not image_path.is_file():
                raise FileNotFoundError(f"Image referenced by annotation is missing: {image_path}")
            image_dir = output / "images" / target_split
            label_dir = output / "labels" / target_split
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            destination = image_dir / image_path.name
            if image_path.resolve() != destination.resolve() and (
                not destination.is_file() or destination.stat().st_size != image_path.stat().st_size
            ):
                shutil.copy2(image_path, destination)

            width, height = float(image["width"]), float(image["height"])
            rows: list[str] = []
            for annotation in annotations.get(image_id, []):
                class_name = category_to_name[int(annotation["category_id"])]
                if class_name not in class_to_index:
                    continue
                x, y, box_width, box_height = (float(value) for value in annotation["bbox"])
                x1, y1 = max(0.0, x), max(0.0, y)
                x2, y2 = min(width, x + box_width), min(height, y + box_height)
                box_width, box_height = x2 - x1, y2 - y1
                if box_width <= 0 or box_height <= 0:
                    continue
                center_x, center_y = (x1 + x2) / 2 / width, (y1 + y2) / 2 / height
                class_id = class_to_index[class_name]
                rows.append(f"{class_id} {center_x:.6f} {center_y:.6f} {box_width / width:.6f} {box_height / height:.6f}")
                converted_counts[class_name] += 1
            (label_dir / f"{image_path.stem}.txt").write_text(
                "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8"
            )

    dataset_path = output.relative_to(project_root).as_posix() if output.is_relative_to(project_root) else output.as_posix()
    yaml_lines = [f"path: {dataset_path}", "train: images/train", "val: images/val", "test: images/test", "names:"]
    yaml_lines.extend(f"  {index}: {name}" for index, name in enumerate(classes))
    config_path = project_root / "data" / "kaggle_malaysian.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    summary = {
        "source_dataset": "larmkaixian/malaysian-trash-annotation/versions/4",
        "license": "CC BY 4.0",
        "source_format": "COCO bounding boxes",
        "converted_format": "YOLO detection boxes",
        "images_per_split": image_counts,
        "total_images": sum(image_counts.values()),
        "non_empty_classes": classes,
        "annotations_per_class": {name: converted_counts[name] for name in classes},
        "total_annotations": sum(converted_counts.values()),
    }
    report_dir = project_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "dataset-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"YOLO dataset written to {output}")
    print(f"Dataset config: {config_path} ({len(classes)} non-empty classes)")
    print(f"Dataset summary: {report_dir / 'dataset-summary.json'}")
    print("Annotated instances by class:")
    for name in classes:
        print(f"  {name}: {converted_counts[name]}")


if __name__ == "__main__":
    main()
