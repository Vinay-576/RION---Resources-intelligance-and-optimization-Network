"""Two-stage visual inference: YOLO item boxes plus a trained waste classifier."""

from pathlib import Path
import os
import hashlib
import hmac
from threading import Lock
import tempfile

from PIL import Image

from .schemas import Material

MODEL_VERSION = "rion-yolo-material-v3-known-class-fallback"
DETECTOR_MATERIAL_THRESHOLDS: dict[str, float] = {"mixed_plastic": 0.80}
CLASSIFIER_LABELS: dict[str, Material] = {
    "battery": "battery",
    "biological": "organic",
    "cardboard": "paper_cardboard",
    "clothes": "textile",
    "glass": "glass",
    "metal": "metal",
    "paper": "paper_cardboard",
    "plastic": "mixed_plastic",
    "shoes": "composite",
    "trash": "other_waste",
}

_LABELS: dict[str, Material] = {
    "steel": "steel",
    "steel_item": "steel",
    "ferrous_metal": "steel",
    "m_metal": "metal",
    "m_glass": "glass",
    "m_paper": "paper_cardboard",
    "m_plastic_film": "mixed_plastic",
    "m_plastic_rigid": "mixed_plastic",
    "m_composite": "composite",
    "m_organic": "organic",
    "s_organic": "organic",
    "s_textile": "textile",
    "s_hazardous": "battery",
    "rubber": "rubber",
    "pet": "PET",
    "pet_plastic": "PET",
    "hdpe": "HDPE",
    "hdpe_plastic": "HDPE",
    "pvc": "PVC",
    "pvc_plastic": "PVC",
    "ldpe": "LDPE",
    "ldpe_plastic": "LDPE",
    "pp": "PP",
    "pp_plastic": "PP",
    "ps": "PS",
    "ps_plastic": "PS",
    "mixed_plastic": "mixed_plastic",
    "glass": "glass",
    "paper_cardboard": "paper_cardboard",
    "unknown": "unknown",
}


def normalize_material(label: str) -> Material:
    normalized = label.strip().lower().replace(" ", "_").replace("-", "_")
    return _LABELS.get(normalized, CLASSIFIER_LABELS.get(normalized, "unknown"))


def fuse_material_prediction(
    detector_label: str,
    detector_confidence: float,
    classifier_prediction: tuple[str, float] | None,
    *,
    classifier_threshold: float = 0.50,
    detector_threshold: float = 0.55,
) -> tuple[str, Material, float]:
    """Prefer reliable material detections and use the classifier to fill gaps."""
    detector_material = normalize_material(detector_label)
    detector_minimum = max(
        detector_threshold,
        DETECTOR_MATERIAL_THRESHOLDS.get(detector_material, detector_threshold),
    )
    detector_is_trusted = detector_material != "unknown" and detector_confidence >= detector_minimum

    classifier_label = "unknown"
    classifier_material: Material = "unknown"
    classifier_confidence = 0.0
    classifier_is_trusted = False
    if classifier_prediction:
        classifier_label, classifier_confidence = classifier_prediction
        classifier_material = CLASSIFIER_LABELS.get(classifier_label.strip().lower(), "unknown")
        classifier_is_trusted = (
            classifier_material != "unknown" and classifier_confidence >= classifier_threshold
        )

    # A confident metal/glass detection wins over confusing shoe/plastic crop
    # guesses. Conversely, a confident metal/glass crop can correct a plastic
    # or composite detector label (for example, a steel bottle).
    if detector_is_trusted:
        if classifier_is_trusted and detector_material == classifier_material:
            return detector_label, detector_material, min(detector_confidence, classifier_confidence)
        if (
            classifier_is_trusted
            and classifier_material in {"metal", "glass"}
            and detector_material in {"mixed_plastic", "composite"}
        ):
            return classifier_label, classifier_material, classifier_confidence
        if (
            classifier_is_trusted
            and detector_material in {"metal", "glass"}
            and classifier_material in {"mixed_plastic", "composite"}
        ):
            return detector_label, detector_material, detector_confidence
        return detector_label, detector_material, detector_confidence

    if classifier_is_trusted:
        return classifier_label, classifier_material, classifier_confidence

    return "unknown_item", "unknown", detector_confidence


def whole_image_prediction(
    classifier_prediction: tuple[str, float] | None,
    *,
    classifier_threshold: float = 0.50,
    fallback_threshold: float = 0.50,
) -> dict[str, object]:
    """Return a single-item classification or an explicit Unknown item result."""
    label = "unknown"
    confidence = 0.0
    material: Material = "unknown"
    if classifier_prediction:
        label, confidence = classifier_prediction
        material = CLASSIFIER_LABELS.get(label.strip().lower(), "unknown")
        required = max(classifier_threshold, fallback_threshold)
        if material != "unknown" and confidence >= required:
            return {
                "box": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
                "object_label": label,
                "material": material,
                "confidence": confidence,
            }
    return {
        "box": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
        "object_label": "unknown_item",
        "material": "unknown",
        "confidence": confidence,
    }


class ModelUnavailableError(RuntimeError):
    pass


class YoloInference:
    """Lazy-loading YOLO detector with an optional Kaggle-trained crop classifier.

    When S3 settings are supplied, weights are fetched using the AWS SDK default
    credential chain (an ECS task role in production); credentials are never
    embedded in code or environment files.
    """

    def __init__(
        self,
        model_path: Path,
        classifier_path: Path | None = None,
        *,
        s3_bucket: str | None = None,
        model_s3_key: str | None = None,
        classifier_s3_key: str | None = None,
        model_sha256: str = "",
        classifier_sha256: str = "",
        classifier_threshold: float = 0.50,
        detector_threshold: float = 0.55,
        classifier_fallback_threshold: float = 0.50,
    ) -> None:
        self.model_path = model_path
        self.classifier_path = classifier_path
        self.s3_bucket = s3_bucket
        self.model_s3_key = model_s3_key
        self.classifier_s3_key = classifier_s3_key
        self.model_sha256 = model_sha256
        self.classifier_sha256 = classifier_sha256
        self.classifier_threshold = classifier_threshold
        self.detector_threshold = detector_threshold
        self.classifier_fallback_threshold = classifier_fallback_threshold
        self._model = None
        self._classifier = None
        self._lock = Lock()

    @property
    def available(self) -> bool:
        local = self.model_path.is_file()
        remote = bool(self.s3_bucket and self.model_s3_key)
        return local or remote

    @property
    def classifier_available(self) -> bool:
        local = bool(self.classifier_path and self.classifier_path.is_file())
        remote = bool(self.s3_bucket and self.classifier_s3_key)
        return local or remote

    @property
    def version(self) -> str:
        if self.model_path.is_file():
            stat = self.model_path.stat()
            detector = f"{stat.st_size:x}-{stat.st_mtime_ns:x}"
        else:
            detector = self.model_sha256[:16] or self.model_s3_key or "unavailable"
        if self.classifier_path and self.classifier_path.is_file():
            stat = self.classifier_path.stat()
            classifier = f"{stat.st_size:x}-{stat.st_mtime_ns:x}"
        else:
            classifier = self.classifier_sha256[:16] or self.classifier_s3_key or "detector-only"
        return f"{MODEL_VERSION}-{detector}-cls-{classifier}"

    def _resolve_weights(self, local_path: Path | None, s3_key: str | None, expected_sha256: str = "") -> Path | None:
        if local_path and local_path.is_file():
            return local_path
        if not self.s3_bucket or not s3_key:
            return None
        target = Path(tempfile.gettempdir()) / "rion-models" / Path(s3_key).name
        if target.is_file():
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        import boto3

        boto3.client("s3").download_file(self.s3_bucket, s3_key, str(target))
        if expected_sha256:
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if not hmac.compare_digest(expected_sha256.lower(), digest):
                target.unlink(missing_ok=True)
                raise RuntimeError("Downloaded RION model checksum did not match the configured SHA-256.")
        return target

    @staticmethod
    def _configure_ultralytics() -> None:
        project_root = Path(__file__).resolve().parents[2]
        config_dir = Path(os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics")))
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(project_root / ".matplotlib"))
        Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    def _load_models(self) -> None:
        self._configure_ultralytics()
        from ultralytics import YOLO

        detector_path = self._resolve_weights(self.model_path, self.model_s3_key, self.model_sha256)
        if detector_path is None:
            raise ModelUnavailableError(f"No trained RION detector checkpoint found at {self.model_path}.")
        self._model = YOLO(str(detector_path))

        classifier_path = self._resolve_weights(self.classifier_path, self.classifier_s3_key, self.classifier_sha256)
        self._classifier = YOLO(str(classifier_path)) if classifier_path else None

    def _classify_crop(self, classifier, crop: Image.Image) -> tuple[str, float] | None:
        with self._lock:
            results = classifier.predict(source=crop, imgsz=224, verbose=False)
        if not results or results[0].probs is None:
            return None
        prediction = results[0]
        class_id = int(prediction.probs.top1)
        label = str(prediction.names.get(class_id, "unknown")).strip().lower()
        confidence = float(prediction.probs.top1conf.item())
        return label, confidence

    def predict(self, image: Image.Image) -> list[dict[str, object]]:
        if not self.available:
            raise ModelUnavailableError(
                f"No trained RION detector checkpoint found at {self.model_path}; configure local weights or an S3 model key."
            )

        with self._lock:
            if self._model is None:
                self._load_models()
            predictions = self._model.predict(source=image, conf=0.35, imgsz=640, verbose=False)
            classifier = self._classifier

        results: list[dict[str, object]] = []
        for prediction in predictions:
            if prediction.boxes is None:
                continue
            width, height = prediction.orig_shape[1], prediction.orig_shape[0]
            for box in prediction.boxes:
                x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
                class_id = int(box.cls[0].item())
                raw_label = str(prediction.names.get(class_id, "unknown"))
                detection_confidence = float(box.conf[0].item())
                classified = None
                # Unmapped detector boxes often cover clutter/background. Their
                # crop can look like a shoe or plastic; defer to full-frame
                # classification when every detector result is unsupported.
                detector_material = normalize_material(raw_label)
                if classifier and detector_material != "unknown":
                    bounds = (
                        max(0, int(x1)),
                        max(0, int(y1)),
                        min(width, max(int(x2), int(x1) + 1)),
                        min(height, max(int(y2), int(y1) + 1)),
                    )
                    crop = image.crop(bounds)
                    classified = self._classify_crop(classifier, crop)
                label, material, confidence = fuse_material_prediction(
                    raw_label,
                    detection_confidence,
                    classified,
                    classifier_threshold=self.classifier_threshold,
                    detector_threshold=self.detector_threshold,
                )
                results.append(
                    {
                        "box": {
                            "x1": max(0.0, min(1.0, x1 / width)),
                            "y1": max(0.0, min(1.0, y1 / height)),
                            "x2": max(0.0, min(1.0, x2 / width)),
                            "y2": max(0.0, min(1.0, y2 / height)),
                        },
                        "object_label": label,
                        "material": material,
                        "confidence": confidence,
                    }
                )

        # Drop low-confidence/unsupported boxes. If the detector found nothing
        # classifiable, classify the whole frame so known Kaggle classes are not
        # turned into Unknown item just because detector recall is limited.
        results = [item for item in results if item["material"] != "unknown"]
        if not results:
            classified = self._classify_crop(classifier, image) if classifier else None
            results.append(
                whole_image_prediction(
                    classified,
                    classifier_threshold=self.classifier_threshold,
                    fallback_threshold=self.classifier_fallback_threshold,
                )
            )
        return results
