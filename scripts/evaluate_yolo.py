"""Evaluate a trained YOLO detector on the configured held-out test split."""

import argparse
import json
import os
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/kaggle_malaysian.yaml"))
    parser.add_argument("--weights", type=Path, default=Path("models/material-yolo.pt"))
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    config_dir = Path(os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics")))
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(project_root / ".matplotlib"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    data_yaml = args.data.resolve()
    weights = args.weights.resolve()
    if not data_yaml.is_file():
        raise SystemExit(f"Dataset YAML not found: {data_yaml}")
    if not weights.is_file():
        raise SystemExit(f"Trained checkpoint not found: {weights}")
    config = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    if not config.get("test"):
        raise SystemExit("Dataset YAML has no 'test' split. Keep a frozen held-out split for evaluation.")

    from ultralytics import YOLO

    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data_yaml),
        split="test",
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(project_root / "runs" / "test"),
        name="kaggle-materials",
        exist_ok=True,
        plots=False,
    )
    box = metrics.box
    report = {
        "checkpoint": weights.name,
        "data_config": data_yaml.name,
        "split": "test",
        "image_size": args.imgsz,
        "device": args.device,
        "metrics": {
            "precision": float(box.mp),
            "recall": float(box.mr),
            "map50": float(box.map50),
            "map50_95": float(box.map),
        },
        "per_class_map50_95": {
            str(model.names[index]): float(score) for index, score in enumerate(box.maps)
        },
    }
    report_path = project_root / "reports" / "model-evaluation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved evaluation report to {report_path}")


if __name__ == "__main__":
    main()
