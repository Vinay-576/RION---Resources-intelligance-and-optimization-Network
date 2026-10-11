import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, engine

client = TestClient(app)


def image_bytes(image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (4, 4), "white")
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def test_health_and_material_catalog_are_available_without_checkpoint():
    health = client.get("/health")
    catalog = client.get("/api/v1/materials")
    assert health.status_code == 200
    assert "model_available" in health.json()
    assert catalog.status_code == 200
    assert catalog.json()["policy_mode"] == "illustrative"


def test_invalid_image_is_rejected_before_inference():
    response = client.post(
        "/api/v1/classifications",
        files={"image": ("not-really.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400


def test_unsupported_image_format_is_rejected():
    response = client.post(
        "/api/v1/classifications",
        files={"image": ("image.bmp", image_bytes("BMP"), "image/bmp")},
    )
    assert response.status_code == 415


def test_missing_checkpoint_returns_clear_service_unavailable():
    original_path = engine.model_path
    engine.model_path = original_path.parent / "missing-test-checkpoint.pt"
    try:
        response = client.post(
            "/api/v1/classifications",
            files={"image": ("item.png", image_bytes(), "image/png")},
        )
    finally:
        engine.model_path = original_path
    assert response.status_code == 503
    assert "No trained material model is configured" in response.json()["detail"]
    assert "missing-test-checkpoint" not in response.json()["detail"]


def test_live_frame_endpoint_uses_the_backend_classification_service():
    original_path = engine.model_path
    engine.model_path = original_path.parent / "missing-live-test-checkpoint.pt"
    try:
        response = client.post(
            "/api/v1/live-frame",
            files={"image": ("webcam-frame.jpg", image_bytes("JPEG"), "image/jpeg")},
            data={"facility_id": "example_facility"},
        )
    finally:
        engine.model_path = original_path
    assert response.status_code == 503
    assert "No trained material model is configured" in response.json()["detail"]


def test_cors_allows_the_vite_loopback_origin():
    response = client.options(
        "/api/v1/live-frame",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

