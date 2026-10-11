# RION — Resource Intelligence & Optimization Network

RION is an AI-assisted waste and material guidance prototype. A React and Tailwind web app captures webcam frames or accepts a photo, sends it to a Python FastAPI backend, and displays detected item regions with illustrative reuse, recycling, refusal, or human-review guidance.

> **Prototype status:** RION is not deployed to AWS and its example facility rules are not local disposal instructions. The included detector and classifier are experimental models. Verify uncertain, hazardous, contaminated, composite, and locally regulated items with a qualified person.

## What RION does

- Uses browser `getUserMedia` for live camera preview and posts a compressed frame about once per second to FastAPI. The upload screen uses the same backend inference path.
- Uses a two-stage vision pipeline: YOLO detects object regions; a separately trained YOLO image classifier refines each detected crop to one of 10 broad waste categories. If YOLO finds no region, the classifier can return a whole-frame guess for a single, centered item.
- Returns normalized boxes, item label, material estimate, confidence, route explanation, possible recycling outputs, and reuse examples.
- Keeps material inference separate from route policy. Without an RDS policy row for a selected facility, the app uses marked illustrative fixtures.
- Processes images in memory. The starter does not persist webcam frames or uploaded images.

## Expanded categories and limits

The classifier categories are `battery`, `biological`, `cardboard`, `clothes`, `glass`, `metal`, `paper`, `plastic`, `shoes`, and `trash`. The app maps them to broad material or handling categories: batteries to review, biological waste to organics, cardboard/paper to paper-cardboard, clothes to textiles, shoes to composite, plastic to mixed plastic, and trash to general waste for review. The detector additionally locates broad plastic film/rigid plastic, glass, metal, paper, composites, and special waste classes.

The source data does **not** provide rubber-specific labels, steel-versus-aluminum labels, or exact plastic resin labels such as PET, HDPE, PVC, LDPE, PP, or PS. `Metal` means generic metal; `Plastic` means mixed/unknown-resin plastic. Shoes are multi-material composites, not a rubber label. Adding these exact categories requires more suitable licensed examples, reviewed annotations, retraining, and class-specific held-out evaluation.

RION identifies known dataset categories with the trained classifier even when YOLO does not find a usable box. The classifier confidence threshold is 0.50; weak predictions or unsupported labels display as **Unknown item**. The dataset's `trash` class displays as **General waste** for review, not Unknown item. When both models disagree and YOLO has a confident metal or glass detection, that detection takes precedence over a shoe or plastic crop guess. A confident metal/glass crop can also correct a plastic/composite detector guess. On a stratified sample of 300 validation images (30 per Kaggle class), the 0.50 threshold retained 95% of predictions with 92.3% accuracy among retained predictions. This is a small validation check, not a guarantee for real webcams or out-of-dataset items.

Both included models have limits. The detector is trained on a small object-detection dataset and the added Kaggle classifier uses folder-level image labels, not bounding boxes. The classifier reached 89.3% top-1 and 99.3% top-5 accuracy on its balanced 1,350-image held-out test split after two CPU fine-tuning epochs. This score does not guarantee camera performance: the classifier is most appropriate for one visible object per crop and can confuse real-world clutter, poor lighting, tiny objects, or unusual packaging. See [MODEL_CARD.md](MODEL_CARD.md), [reports/model-evaluation.json](reports/model-evaluation.json), and [reports/classifier-evaluation.json](reports/classifier-evaluation.json) for metrics and limitations.

## Team responsibilities

| Role | Owns |
|---|---|
| AI/ML Expert | YOLO detection and classifier training, taxonomy, tuning, confidence/abstention, error analysis, and model releases. |
| Security Expert | Upload validation, SQL injection prevention, IAM least privilege, Secrets Manager, TLS/WAF/firewalls, dependency review, and AWS deployment controls. |
| Data Scientist | Kaggle provenance/license, class mapping, deduplication, balanced splits, data-quality and class-count reports, and local policy evidence. |
| Tester | API/frontend acceptance, webcam permissions and stop/resume, uploads, model uncertainty, bad-input cases, security checks, and release feedback. |
| Web Developer | React/Tailwind interface, webcam/upload integration, API contract, Vite/CORS setup, accessible result cards, and dependencies. |

The detailed architecture and project roadmap are in [PROJECT_PLAN.md](PROJECT_PLAN.md). Proposed AWS services and deployment steps are in [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md).

## Repository layout

```text
RION/
├── backend/app/              # FastAPI routes, validation, models, policy lookup, AWS runtime config
├── backend/requirements.txt  # API, YOLO, boto3, SQLAlchemy, PostgreSQL driver
├── frontend/                 # React + TypeScript + Vite + Tailwind CSS
├── models/                   # trained YOLO detector and 10-class classifier checkpoints
├── data/                     # taxonomy/configuration only; raw and split images are excluded
├── scripts/                  # Kaggle download, data preparation, training, evaluation, packaging
├── infra/aws/                # Terraform, RDS schema, private S3/ECS/ALB/CloudFront/WAF setup
├── reports/                  # dataset, detector, and classifier metrics/checksums
├── tests/                    # backend/API behavior checks
├── AWS_ARCHITECTURE.md
├── MODEL_CARD.md
└── PROJECT_PLAN.md
```

## Requirements

- Windows 10/11, macOS, or Linux.
- Python 3.12 recommended. Install PyTorch/Ultralytics CPU wheels locally; CUDA can be used for training on supported NVIDIA hardware.
- Node.js 22 or newer and npm.
- Visual Studio Code with the Python and Pylance extensions; ESLint is recommended.
- Git is recommended for source control. Raw data and model split folders are not included in the ZIP.

Python dependencies are pinned by ranges in `backend/requirements.txt`; data download helpers are in `backend/requirements-data.txt`; tests use `backend/requirements-dev.txt`. Frontend dependencies are declared in `frontend/package.json` and locked in `frontend/package-lock.json`.

## Run locally in Visual Studio Code

1. Extract `RION.zip`. In VS Code, choose **File → Open Folder…** and select the extracted `RION` folder.
2. Open a VS Code terminal in the project root and create the environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
   ```

   If PyTorch installation fails for your hardware, install a supported CPU or CUDA build using the official [PyTorch install selector](https://pytorch.org/get-started/locally/), then rerun the requirements command.

3. Copy `.env.example` to `.env`. Default checkpoint paths are `models/material-yolo.pt` and `models/rion-classifier.pt`. Leave `MODEL_S3_BUCKET` and `RION_RUNTIME_SECRET_ARN` blank for local use.
4. Install frontend packages:

   ```powershell
   cd frontend
   npm ci
   cd ..
   ```

5. In VS Code, use **Python: Select Interpreter** and select `.venv`.
6. Start FastAPI in one terminal:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```

7. Start the React development server in a second terminal:

   ```powershell
   cd frontend
   npm run dev
   ```

8. Open the Vite URL shown in the terminal (normally `http://127.0.0.1:5173`), allow camera permission, and choose **Live webcam** or **Upload photo**. The local Vite proxy forwards `/health` and `/api/*` to FastAPI. Camera access requires `localhost`/`127.0.0.1` or HTTPS.

Stop each process with `Ctrl+C`. For API checks, open `http://127.0.0.1:8000/health` or the local-only docs at `http://127.0.0.1:8000/docs`.

### Tests and production frontend build

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

## Dataset sources and retraining

RION uses two Kaggle datasets. Attribution and scope notes are in [DATASET_ATTRIBUTION.md](DATASET_ATTRIBUTION.md).

### YOLO object detector

[Malaysian Trash Annotation](https://www.kaggle.com/datasets/larmkaixian/malaysian-trash-annotation), pinned to version 4 and listed by Kaggle as CC BY 4.0, contains 1,532 images and 3,793 COCO bounding boxes. It supplies train, validation, and test splits and broad categories such as metal, plastic film/rigid plastic, glass, paper, composite, organic, and special waste. It does not label rubber, steel versus aluminum, or plastic resin codes.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-data.txt
.\.venv\Scripts\python.exe scripts/download_kaggle_dataset.py
.\.venv\Scripts\python.exe scripts/prepare_kaggle_data.py --source data/raw/kaggle/malaysian-trash-annotation
.\.venv\Scripts\python.exe scripts/train_yolo.py --data data/kaggle_malaysian.yaml --model yolo26n.pt --epochs 30 --imgsz 640 --batch 4 --device cpu
```

The included detector was trained for only 5 epochs at 320 pixels on CPU as an end-to-end baseline. Use a GPU and longer training for serious experiments. Run `scripts/evaluate_yolo.py` on the frozen test split and review per-class results before replacing the checkpoint.

### 10-class item/category classifier

[Garbage Classification V2](https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2), pinned to version 8 and listed by Kaggle as MIT, contains 19,762 folder-labeled images across 10 categories. These are image-level class labels rather than object boxes, so the classifier refines YOLO crops; it does not replace the detector. The pipeline removes exact duplicate images, balances the sampled classes, and keeps independent splits.

```powershell
.\.venv\Scripts\python.exe scripts/download_kaggle_classifier_dataset.py
.\.venv\Scripts\python.exe scripts/prepare_classifier_data.py --max-per-class 900 --seed 42
.\.venv\Scripts\python.exe scripts/train_classifier.py --data data/rion_classifier_training --model yolo26n-cls.pt --epochs 5 --imgsz 224 --batch 32 --device cpu
```

Training writes `models/rion-classifier.pt`, `reports/classifier-dataset-summary.json`, and held-out accuracy in `reports/classifier-evaluation.json`. Raw Kaggle images and generated splits are intentionally excluded from the project ZIP; the two trained checkpoints and reports are included.

## API overview

| Endpoint | Purpose |
|---|---|
| `GET /health` | Readiness and detector/classifier availability. |
| `GET /api/v1/materials` | Supported categories and marked policy guidance. |
| `POST /api/v1/classifications` | Analyze one uploaded image. |
| `POST /api/v1/live-frame` | Analyze one webcam frame; the browser calls this repeatedly while scanning. |

Image requests are limited by configured bytes and pixel count. The server checks the decoded image format, ignores user filenames, and does not persist input images. Low-confidence or unsupported outputs route to human review. Reuse/recycling outputs are examples and not guarantees for a municipality or facility.

## AWS deployment

See [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md) for the complete service map and Terraform deploy outline. The proposed stack uses CloudFront, WAF, ACM, ECS/Fargate, ALB, private versioned S3 model artifacts, RDS PostgreSQL, IAM roles, Secrets Manager, and CloudWatch. It is not deployed by the local setup. It creates billable resources and requires an AWS account, a Route 53 zone, domain control, and review of the Terraform plan.

## Security notes

- Local development binds FastAPI to loopback. Do not expose the development server publicly.
- AWS config limits ALB ingress to CloudFront origin-facing addresses and checks a random origin token. ECS uses task roles and VPC endpoints; no static AWS keys are in the app.
- The optional RDS lookup uses SQLAlchemy and bound parameters. There are no interpolated SQL queries. PostgreSQL stores reviewed facility rules, not images.
- The included rule table is illustrative. Do not treat `refuse_processing`, recyclability, or hazardous-item routes as authoritative until reviewed by each target facility.
- Before production, define account authentication/authorization needs, incident response, retention, backup/restore, WAF thresholds, dependency scanning, and facility acceptance tests.

## License and references

See [DATASET_ATTRIBUTION.md](DATASET_ATTRIBUTION.md) for Kaggle attribution. The detector dataset is CC BY 4.0 and Garbage Classification V2 is listed as MIT by Kaggle. Verify each dataset's current terms before redistribution or commercial use. Also check the applicable Ultralytics code and pretrained-weight terms for your use case.

- [Kaggle dataset guide](https://www.kaggle.com/docs/datasets)
- [KaggleHub Python API](https://github.com/Kaggle/kagglehub)
- [Ultralytics Python usage](https://docs.ultralytics.com/usage/python)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Vite guide](https://vite.dev/guide/)
- [Tailwind CSS with Vite](https://tailwindcss.com/docs/installation/using-vite)
- [AWS ECS/Fargate load balancing](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-load-balancing.html)
- [AWS ECS IAM role guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-iam-roles.html)
