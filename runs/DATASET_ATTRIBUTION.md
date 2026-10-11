# Dataset attribution and scope

RION uses two public Kaggle datasets for different learning tasks. The model checkpoints are included; raw images are excluded from the project ZIP.

## YOLO object detection — Malaysian Trash Annotation

- Kaggle: [Malaysian Trash Annotation](https://www.kaggle.com/datasets/larmkaixian/malaysian-trash-annotation)
- Repository/citation: [MTA repository](https://github.com/lkaixian/malaysian-trash-annotation)
- Dataset DOI: [10.5281/zenodo.17862878](https://doi.org/10.5281/zenodo.17862878)
- License listed by Kaggle and the dataset README: **CC BY 4.0**.
- Pinned version used for the detector: version 4 / Build 20260418.
- Used for: COCO bounding boxes converted to YOLO object-detection labels. The converted split in the training report has 1,532 images and 3,793 boxes.
- Citation from the dataset README:

  ```bibtex
  @dataset{mta2026,
    author = {Larm, K. X.},
    title = {Malaysian Trash Annotation (MTA)},
    year = {2026},
    doi = {10.5281/zenodo.17862878},
    url = {https://github.com/lkaixian/malaysian-trash-annotation}
  }
  ```

## Image-category refinement — Garbage Classification V2

- Kaggle: [Garbage Classification V2](https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2)
- Pinned version used for the classifier: version 8.
- License listed by Kaggle: **MIT**. Review the Kaggle dataset card and current terms before redistribution or commercial use.
- The source contains 19,762 folder-labeled images across `battery`, `biological`, `cardboard`, `clothes`, `glass`, `metal`, `paper`, `plastic`, `shoes`, and `trash`.
- Used for: 10-way image classification on YOLO-detected crops (and a single-item full-frame fallback when no detector box is found). These are image-level labels, not bounding boxes. The training prep balances the source by capping selected images at 900 per class, removes exact duplicates, and makes fixed train/validation/test splits. See `reports/classifier-dataset-summary.json`.

Retain the relevant source attribution, license link, and change notes when redistributing trained artifacts. RION's mapped labels do not add unsupported rubber, alloy, or plastic-resin distinctions. Do not treat model output as evidence of facility acceptance.
