# RION — Project Description

## About the project

RION (Resource Intelligence & Optimization Network) is a computer-vision prototype for helping people sort common waste and recyclable materials. A user can point a webcam at an item or upload a photo. RION detects visible regions, predicts a broad category from its trained dataset, and presents an illustrative route such as recyclable, reusable, refuse processing, or needs review. It also gives examples of possible recycled outputs and reuse ideas.

The current classifier recognizes ten broad dataset categories: battery, biological, cardboard, clothes, glass, metal, paper, plastic, shoes, and trash. These map to handling categories such as battery review, organics, paper/cardboard, textile, glass, generic metal, mixed plastic, composite, and general waste. Unsupported or low-confidence predictions are shown as **Unknown item**. The project does not claim to identify steel versus aluminum, plastic resin codes, or rubber specifically because the bundled training data does not contain validated labels for those distinctions.

RION is decision support, not an autonomous sorting or safety system. Its policy catalogue is illustrative, and local facilities may accept different materials. Uncertain, contaminated, composite, hazardous, and locally regulated items should be reviewed by a person.

## Tech stack and architecture

| Layer | Technology | Responsibility |
|---|---|---|
| Web frontend | React 19, TypeScript, Vite, Tailwind CSS 4 | Webcam preview, image upload, result overlays, material guidance, and responsive UI. |
| Camera and transport | Browser `getUserMedia`, JPEG frames, Fetch API | Sends a still image or periodic webcam frame to the backend over HTTP during local development and HTTPS when hosted. |
| API backend | Python 3.12, FastAPI, Pydantic, Uvicorn | Validates image requests, invokes inference, returns detections and route guidance. |
| AI inference | Ultralytics YOLO, PyTorch, Pillow | YOLO detects candidate regions; a separately trained YOLO image classifier predicts one of the Kaggle categories for each crop or the full frame when detection has no usable result. |
| Policy data | SQLAlchemy, PostgreSQL (optional) | Looks up facility-specific material rules with bound SQL parameters; illustrative in-app rules are used when no database rule is configured. |
| Model and data artifacts | Local `.pt` checkpoints; S3 model storage in the proposed AWS setup | Stores the detector/classifier weights. S3 downloads are checked against configured SHA-256 hashes. |

The request path is:

```text
Webcam or uploaded image
        ↓
React frontend → FastAPI image validation
        ↓
YOLO object detector → classifier for detected crops
        ↓
Whole-frame classifier fallback if no usable detection exists
        ↓
Material normalization → facility policy lookup
        ↓
Result cards: category, confidence, route, possible outputs, reuse ideas
```

Images are processed in memory and are not saved by the starter application. Model predictions and local disposal rules are kept separate so a facility can update its policy without retraining the vision model.

## How AWS is used

AWS is **planned and represented in Terraform, but it has not been deployed**. The local project runs with the Vite frontend, FastAPI backend, local model checkpoints, and optional local database configuration. No AWS resources are currently required for local use.

The prepared AWS architecture maps the application to these services:

| Purpose | Proposed AWS service | RION use |
|---|---|---|
| Public HTTPS and edge protection | CloudFront, AWS WAF, AWS Certificate Manager, Route 53 | Serves the frontend, routes API requests, applies WAF rules, and provides TLS certificates and DNS. |
| Frontend hosting | Private Amazon S3 bucket | Stores the built React assets; CloudFront accesses the bucket privately. |
| API hosting | Amazon ECS on Fargate behind an Application Load Balancer | Runs the FastAPI container in private subnets; the load balancer accepts requests through the CloudFront origin path. |
| Model artifacts | Private, versioned Amazon S3 bucket | Stores YOLO checkpoints; the API task role can read the required model files and the backend verifies their SHA-256 hashes. |
| Facility rules | Amazon RDS for PostgreSQL | Stores reviewed facility/material routing rules. It is not used to store uploaded or webcam images. |
| Credentials and permissions | AWS IAM roles and AWS Secrets Manager | Gives the ECS task scoped access to models and runtime secrets without embedding AWS keys in source code. |
| Logs and monitoring | Amazon CloudWatch | Collects API logs, service metrics, and deployment alarms. |

Terraform files, container configuration, and deployment steps are in [`infra/aws/`](infra/aws/) and [`AWS_ARCHITECTURE.md`](AWS_ARCHITECTURE.md). Applying them would create billable resources and requires an AWS account, domain and Route 53 control, credentials, protected Terraform state, and a reviewed plan. The architecture is prepared; it should not be described as a live AWS deployment until those resources have actually been provisioned and verified.
