# RION training data

RION uses two Kaggle datasets with different label types. Preserve their attributions in [DATASET_ATTRIBUTION.md](../DATASET_ATTRIBUTION.md). Raw images and generated image splits are excluded from the project ZIP.

## Object detection

[Malaysian Trash Annotation v4](https://www.kaggle.com/datasets/larmkaixian/malaysian-trash-annotation) is listed under CC BY 4.0. The project converts COCO bounding boxes into YOLO labels and retains the train/validation/test split. The converted run recorded 1,532 images and 3,793 boxes. It provides broad metal and plastic classes plus paper, glass, composite, and special waste categories; it has no rubber-specific, steel/alloy, or resin-code labels.

```powershell
python scripts/download_kaggle_dataset.py
python scripts/prepare_kaggle_data.py --source data/raw/kaggle/malaysian-trash-annotation
```

Converted detections are placed in `data/material_dataset_kaggle/` and configured by `data/kaggle_malaysian.yaml`.

## Image classification

[Garbage Classification V2 v8](https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2) is listed under MIT. Its 19,762 images are folder-labeled as battery, biological, cardboard, clothes, glass, metal, paper, plastic, shoes, or trash. The labels describe whole images and do not provide bounding boxes. RION uses this as a second-stage classifier for crops proposed by the detector.

```powershell
python scripts/download_kaggle_classifier_dataset.py
python scripts/prepare_classifier_data.py --max-per-class 900 --seed 42
python scripts/train_classifier.py --data data/rion_classifier_training --epochs 5 --imgsz 224 --batch 32 --device cpu
```

Preparation removes exact duplicates, takes a balanced sample per class, and writes independent train, validation, and test folders plus `reports/classifier-dataset-summary.json`. Keep the held-out test split separate from training and choose representative field images for additional evaluation.

## Data limits

Neither source supports reliable rubber identification, steel-versus-aluminum distinction, PET/HDPE/PVC/LDPE/PP/PS recognition, contamination detection, or facility acceptance rules. New labels need licensed and reviewed examples; use the unknown/review route until the category has adequate data and evaluation.
