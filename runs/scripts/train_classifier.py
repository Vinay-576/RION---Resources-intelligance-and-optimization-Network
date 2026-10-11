"""Fine-tune and test the RION 10-class YOLO image classifier."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/rion_classifier_training"))
    parser.add_argument("--model", default="yolo26n-cls.pt")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--evaluate-checkpoint",
        type=Path,
        help="Evaluate and package an existing best.pt without starting another training run.",
    )
    parser.add_argument(
        "--trained-epochs",
        type=int,
        help="Completed epoch count for --evaluate-checkpoint, used in its report.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    data = args.data.resolve()
    if not all((data / split).is_dir() for split in ("train", "val", "test")):
        raise SystemExit("Expected train/, val/, and test/ class folders. Run scripts/prepare_classifier_data.py first.")
    os.environ.setdefault("YOLO_CONFIG_DIR", str(root / ".ultralytics"))
    os.environ.setdefault("MPLCONFIGDIR", str(root / ".matplotlib"))
    Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    import torch
    import ultralytics
    import yaml
    from ultralytics import YOLO

    if args.evaluate_checkpoint:
        best = args.evaluate_checkpoint.resolve()
        if not best.is_file():
            raise SystemExit(f"Checkpoint not found: {best}")
        completed_epochs = args.trained_epochs
        if completed_epochs is None:
            raise SystemExit("Pass --trained-epochs when evaluating a checkpoint without training.")
    else:
        model = YOLO(args.model)
        result = model.train(
            data=str(data),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=0,
            project=str(root / "runs" / "classify"),
            name="rion-garbage-v2",
            exist_ok=True,
            plots=False,
            patience=max(3, args.epochs),
        )
        best = Path(result.save_dir) / "weights" / "best.pt"
        completed_epochs = args.epochs
    if not best.is_file():
        raise SystemExit(f"Training completed but best checkpoint was not found: {best}")

    model = YOLO(str(best))
    metrics = model.val(
        data=str(data),
        split="test",
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=0,
        plots=False,
    )
    checkpoint = root / "models" / "rion-classifier.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, checkpoint)
    class_dirs = sorted(p.name for p in (data / "train").iterdir() if p.is_dir())
    dataset_summary_path = root / "reports" / "classifier-dataset-summary.json"
    dataset_summary = json.loads(dataset_summary_path.read_text(encoding="utf-8")) if dataset_summary_path.is_file() else {}
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "sumn2u/garbage-classification-v2/versions/8",
        "license": "MIT as listed by Kaggle",
        "class_names": class_dirs,
        "training": {"base_model": args.model, "epochs": completed_epochs, "image_size": args.imgsz, "batch": args.batch, "device": args.device},
        "software": {"python": sys.version.split()[0], "platform": platform.platform(), "torch": torch.__version__, "ultralytics": ultralytics.__version__},
        "test_metrics": {"top1_accuracy": float(metrics.top1), "top5_accuracy": float(metrics.top5)},
        "checkpoint": {
            "path": "models/rion-classifier.pt",
            "size_bytes": checkpoint.stat().st_size,
            "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        },
        "dataset_split_summary": dataset_summary,
    }
    report_path = root / "reports" / "classifier-evaluation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Best classifier saved to {checkpoint}")


if __name__ == "__main__":
    main()
