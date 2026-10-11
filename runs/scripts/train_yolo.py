"""Train a YOLO detector on a prepared YOLO-format material dataset."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def validate_dataset(data_yaml: Path) -> None:
    config = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise SystemExit(f"Invalid dataset YAML: {data_yaml}")
    dataset_root = Path(config.get("path") or data_yaml.parent)
    if not dataset_root.is_absolute():
        dataset_root = Path.cwd() / dataset_root
    for key in ("train", "val"):
        split = config.get(key)
        if not split:
            raise SystemExit(f"Dataset YAML is missing the required '{key}' path: {data_yaml}")
        image_dir = Path(split)
        if not image_dir.is_absolute():
            image_dir = dataset_root / image_dir
        label_dir = Path(str(image_dir).replace("images", "labels"))
        if not image_dir.is_dir() or not any(image_dir.iterdir()):
            raise SystemExit(f"Dataset image directory is missing or empty: {image_dir}")
        if not label_dir.is_dir() or not any(label_dir.glob("*.txt")):
            raise SystemExit(f"YOLO label directory is missing or empty: {label_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/kaggle_malaysian.yaml", help="YOLO dataset YAML")
    parser.add_argument("--model", default="yolo26n.pt", help="Pretrained model checkpoint or model name")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default=None, help="Optional device such as cpu, 0, or 0,1")
    parser.add_argument("--name", default="kaggle-materials", help="Ultralytics training run name")
    args = parser.parse_args()

    data_yaml = Path(args.data).resolve()
    if not data_yaml.is_file():
        raise SystemExit(
            f"Dataset YAML not found: {data_yaml}\n"
            "Download and convert the Kaggle dataset first; see the README training steps."
        )
    validate_dataset(data_yaml)

    try:
        config_dir = Path(os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / ".ultralytics")))
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib"))
        Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install backend dependencies first: python -m pip install -r backend/requirements.txt") from exc

    model = YOLO(args.model)
    options = {
        "data": str(data_yaml),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": str(Path(__file__).resolve().parents[1] / "runs" / "train"),
        "name": args.name,
        "exist_ok": False,
        "seed": 42,
        "deterministic": True,
        "workers": 2,
        "cache": False,
    }
    if args.device:
        options["device"] = args.device
    model.train(**options)
    best_weights = Path(model.trainer.best)
    if not best_weights.is_file():
        raise SystemExit(f"Training ended but best weights were not found: {best_weights}")
    destination = Path("models/material-yolo.pt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, destination)
    print(f"Training finished. Best weights copied to {destination.resolve()}")
    print(f"Training outputs and validation metrics: {Path(model.trainer.save_dir).resolve()}")
    dataset_config = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    test_metrics_report = None
    test_split = dataset_config.get("test")
    dataset_root = Path(dataset_config.get("path") or data_yaml.parent)
    if not dataset_root.is_absolute():
        dataset_root = Path.cwd() / dataset_root
    test_images = Path(test_split) if test_split else None
    if test_images is not None and not test_images.is_absolute():
        test_images = dataset_root / test_images
    if test_images is not None and test_images.is_dir() and any(test_images.iterdir()):
        test_model = YOLO(str(destination.resolve()))
        test_metrics = test_model.val(
            data=str(data_yaml),
            split="test",
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device or "cpu",
            project=str(Path(__file__).resolve().parents[1] / "runs" / "test"),
            name=args.name,
            exist_ok=True,
            plots=False,
        )
        box = test_metrics.box
        report = {
            "checkpoint": str(destination.as_posix()),
            "data_config": str(data_yaml.as_posix()),
            "split": "test",
            "epochs": args.epochs,
            "image_size": args.imgsz,
            "device": args.device or "cpu",
            "metrics": {
                "precision": float(box.mp),
                "recall": float(box.mr),
                "map50": float(box.map50),
                "map50_95": float(box.map),
            },
        }
        report_path = Path("reports/model-evaluation.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        test_metrics_report = report["metrics"]
        print(f"Held-out test metrics written to {report_path.resolve()}: {report['metrics']}")
    else:
        print("No test split was found; review validation metrics and add a frozen held-out test set.")
    checkpoint_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    try:
        import torch
        import ultralytics

        torch_version = torch.__version__
        ultralytics_version = ultralytics.__version__
    except Exception:
        torch_version = ultralytics_version = "unavailable"
    configured_names = dataset_config.get("names", {})
    class_names = list(configured_names.values()) if isinstance(configured_names, dict) else list(configured_names)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": "larmkaixian/malaysian-trash-annotation/versions/4",
        "dataset_license": "CC BY 4.0",
        "model_base": args.model,
        "command": f"python scripts/train_yolo.py --data {args.data} --model {args.model} --epochs {args.epochs} --imgsz {args.imgsz} --batch {args.batch} --device {args.device or 'auto'}",
        "epochs_requested": args.epochs,
        "image_size": args.imgsz,
        "batch": args.batch,
        "device": args.device or "auto",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch_version,
        "ultralytics": ultralytics_version,
        "classes": class_names,
        "checkpoint": destination.as_posix(),
        "checkpoint_sha256": checkpoint_hash,
        "test_metrics": test_metrics_report,
    }
    summary_path = Path("reports/training-summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Training summary written to {summary_path.resolve()}")
    print("Review per-class errors and class counts before relying on the checkpoint.")


if __name__ == "__main__":
    main()
