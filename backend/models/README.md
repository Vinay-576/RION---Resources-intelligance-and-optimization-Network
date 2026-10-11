# Model checkpoint

RION uses two local model artifacts: `models/material-yolo.pt` for object boxes and `models/rion-classifier.pt` for crop-category refinement. Configure `MODEL_PATH` and `CLASSIFIER_PATH` in `.env` when using non-default file names. In AWS, Terraform uploads both files to a private, versioned S3 bucket and the ECS task role downloads them using the default AWS credential chain; the configured SHA-256 digests are checked after download. The portable ZIP includes these two trained demo checkpoints, but excludes raw Kaggle images and generated split folders.

The class names in the trained model must match the taxonomy in `data/materials.yaml`. Run the training script in the repository root after preparing YOLO-format annotations.

