from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_OBJECT = {
    "koi_period": 9.488, "koi_duration": 2.958, "koi_depth": 615.8,
    "koi_prad": 2.26, "koi_teq": 793, "koi_model_snr": 35.8,
    "koi_steff": 5455, "koi_srad": 0.927,
}


def test_predict_valid():
    response = client.post("/predict", json=VALID_OBJECT)
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] in {"CONFIRMED", "FALSE POSITIVE"}
    assert 0 <= body["planet_probability"] <= 1
    assert body["confidence_level"] in {"low", "medium", "high"}


def test_predict_invalid():
    invalid = {**VALID_OBJECT, "koi_period": -5}  # Un periodo orbital no puede ser negativo
    response = client.post("/predict", json=invalid)
    assert response.status_code == 422
