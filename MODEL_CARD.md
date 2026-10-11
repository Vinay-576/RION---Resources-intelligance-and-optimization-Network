# RION model card

## Status and intended use

RION is an educational, experimental decision-support prototype. The bundled models are not production-grade and must not autonomously control sorting machinery or determine safety, hazardous-waste, or local disposal decisions. The UI presents results from a webcam or uploaded image as estimates; low-confidence and unsupported cases need human review. The example policy catalogue is not verified guidance for any municipality or facility.

The inference pipeline combines two different model types:

1. A YOLO object detector finds candidate item regions and broad visual categories.
2. A separately trained YOLO image classifier refines each detected crop into one of 10 broad waste categories. When no object box is found, it can classify the whole frame as a single-item fallback.

The second model was trained from folder labels, not bounding boxes. It can label the content of a crop, but it does not locate multiple objects by itself.

## Training data and provenance

### Detector

- Source: [Malaysian Trash Annotation on Kaggle](https://www.kaggle.com/datasets/larmkaixian/malaysian-trash-annotation), pinned to version 4 / Build 20260418.
- License: CC BY 4.0, as listed by Kaggle and the dataset README; attribution details are in [DATASET_ATTRIBUTION.md](DATASET_ATTRIBUTION.md).
- Converted split: 1,532 images and 3,793 bounding boxes (1,072 train, 306 validation, 154 held-out test).
- The detector categories with annotations include broad metal, glass, paper, rigid/flexible plastic, composite, organic, textile, and special-waste/litter labels. It does not supply rubber, metal alloy, or plastic resin labels.

### Image classifier

- Source: [Garbage Classification V2 on Kaggle](https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2), pinned to version 8.
- License: MIT as listed by Kaggle; attribution details are in [DATASET_ATTRIBUTION.md](DATASET_ATTRIBUTION.md).
- The source has 19,762 images across battery, biological, cardboard, clothes, glass, metal, paper, plastic, shoes, and trash folders. Images are exact-hash deduplicated, a deterministic balanced sample is split by class, and raw data is excluded from the ZIP.
- The prepared split has 6,300 train, 1,350 validation, and 1,350 test images (900 per category before splitting). See [reports/classifier-dataset-summary.json](reports/classifier-dataset-summary.json).

## Label mapping and coverage

| Classifier label | API material result | Limitation |
|---|---|---|
| battery | battery | Chemistry/charge/condition cannot be inferred. |
| biological | organic | Does not identify contamination or accepted compost stream. |
| cardboard, paper | paper_cardboard | Coatings and contamination are not determined. |
| clothes | textile | Condition and fiber composition are not determined. |
| glass | glass | Cannot distinguish container glass from mirrors/ceramics reliably. |
| metal | metal | Does not distinguish steel, aluminum, or alloys. |
| plastic | mixed_plastic | Does not identify PET, HDPE, PVC, LDPE, PP, PS, or resin marks. |
| shoes | composite | Shoes contain multiple materials that are not separated by this model. |
| trash | other_waste | The dataset's general-waste class; contents still need review. |

The API schema and illustrative guidance catalogue also include `rubber`, `steel`, and resin-specific plastic labels for future/specialized models or reviewed human corrections. **The bundled model has not been trained or validated to recognize rubber, distinguish steel from other metal, or identify plastic resin types.** A separate close-up/OCR or specialized training dataset would be needed for resin marks; the image alone may not provide enough evidence.

If YOLO has no usable material detection, RION falls back to the trained whole-image classifier instead of returning unknown just because detection missed the object. Known Kaggle categories are accepted at classifier confidence 0.50 or higher; the dataset's `trash` class maps to `other_waste`, while weaker or unsupported predictions map to `unknown`. A confident metal/glass detection takes precedence over a conflicting shoe/plastic crop guess, while a confident metal/glass crop can correct a plastic/composite detection. On a stratified sample of 300 validation images (30 per Kaggle class), this threshold retained 95% of predictions with 92.3% accuracy among retained predictions. This small validation sample is not an out-of-distribution guarantee: a new item can still receive a confident known-class label, and a known item can still be wrong. Field examples and a separately labeled unknown-item set are needed to tune that behavior.

## Evaluation

The short bundled runs are baselines on held-out Kaggle splits, not evidence of generalization to a facility, a live camera, or arbitrary photos. Detector and classifier metrics are reported separately because object localization and image classification measure different tasks.

- Detector: five CPU epochs at 320-pixel input size. On the 154-image/343-box held-out test split: precision 0.446, recall 0.201, mAP50 0.177, and mAP50-95 0.140. Per-class results are in [reports/model-evaluation.json](reports/model-evaluation.json).
- Classifier: a two-epoch CPU fine-tune at 224-pixel input size was selected from the best saved validation checkpoint. On the separate 1,350-image held-out test split, it reached top-1 accuracy 0.893 and top-5 accuracy 0.993. Full configuration, software versions, and checkpoint SHA-256 are in [reports/classifier-evaluation.json](reports/classifier-evaluation.json).

These limited results mean the detector can miss items or return weak boxes. Classifier accuracy on a curated folder split does not imply accuracy on camera crops. Review false positives, missed items, per-class metrics, and field images before any pilot.

## Known limits and risks

- Only broad waste categories are covered by the trained classifier; exact polymers, alloys, rubber, object condition, cleanliness, and hidden materials are not visually verified.
- The detector dataset is small and strongly imbalanced. Some special classes have very few annotations; their predictions are especially unreliable.
- Training and test images come from the same source collection. Lighting, camera distance, backgrounds, regional packaging, and image quality can shift in real use.
- A frame can contain multiple or overlapping objects, but the crop classifier assigns one top class to each detected crop. A full-frame fallback assumes a single centered item.
- Model confidence is not a measure of safety, recyclability, material purity, or facility acceptance.
- `recyclable`, `reusable`, and `refuse_processing` routes are generated by a policy layer, not learned by the visual model. The bundled policy is explicitly illustrative and local rules may differ.

## Release and monitoring

Every model release should preserve the dataset version/license, split definition, training command, environment versions, per-class evaluation, checkpoint hash, and a human-reviewed sample of failure cases. Keep held-out test data out of tuning. Replace or extend the models only with rights-cleared, class-balanced, representative data and a documented acceptance threshold. For a pilot, log aggregate latency/error metrics without storing image bytes, and provide a human correction workflow.
