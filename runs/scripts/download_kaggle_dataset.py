"""Download the public Malaysian Trash Annotation dataset from Kaggle."""

import argparse
from pathlib import Path

DATASET = "larmkaixian/malaysian-trash-annotation/versions/4"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/kaggle/malaysian-trash-annotation"),
        help="Directory for the downloaded Kaggle files (about 2.7 GB).",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing contents in the output directory.")
    args = parser.parse_args()

    try:
        import kagglehub
    except ImportError as exc:
        raise SystemExit("Install the optional data tools with: python -m pip install -r backend/requirements-data.txt") from exc

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = kagglehub.dataset_download(
        DATASET,
        output_dir=str(output),
        force_download=args.force,
    )
    print(f"Dataset downloaded to: {result}")
    print("Source: https://www.kaggle.com/datasets/larmkaixian/malaysian-trash-annotation")
    print("License listed by Kaggle: CC BY 4.0. Keep attribution with any redistribution.")
    print("Next: python scripts/prepare_kaggle_data.py --source data/raw/kaggle/malaysian-trash-annotation")


if __name__ == "__main__":
    main()
