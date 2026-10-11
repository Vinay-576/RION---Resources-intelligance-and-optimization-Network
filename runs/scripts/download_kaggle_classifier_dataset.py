"""Download the expanded 10-class Kaggle image-classification dataset."""

import argparse
from pathlib import Path

DATASET = "sumn2u/garbage-classification-v2/versions/8"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/kaggle/garbage-classification-v2"),
        help="Directory for the Kaggle download (version 8 archive is about 744 MB).",
    )
    args = parser.parse_args()
    try:
        import kagglehub
    except ImportError as exc:
        raise SystemExit("Install data tools with: python -m pip install -r backend/requirements-data.txt") from exc

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = kagglehub.dataset_download(DATASET, output_dir=str(output))
    print(f"Dataset downloaded to: {result}")
    print("Source: https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2")
    print("Kaggle lists this dataset as MIT licensed; retain the source attribution in DATASET_ATTRIBUTION.md.")
    print("Next: python scripts/prepare_classifier_data.py")


if __name__ == "__main__":
    main()
