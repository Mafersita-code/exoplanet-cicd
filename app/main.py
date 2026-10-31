"""API de clasificación de exoplanetas Kepler (FastAPI)."""
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "champion.joblib"

FEATURES = [
    "koi_period", "koi_duration", "koi_depth", "koi_prad",
    "koi_teq", "koi_model_snr", "koi_steff", "koi_srad",
]

app = FastAPI(
    title="Exoplanet Classifier API",
    description="Clasifica objetos Kepler como CONFIRMED o FALSE POSITIVE. Uso didáctico.",
    version="1.0.0",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
model = joblib.load(MODEL_PATH)


class KeplerObject(BaseModel):
    koi_period: float = Field(..., gt=0, description="Periodo orbital (días)")
    koi_duration: float = Field(..., gt=0, description="Duración del tránsito (horas)")
    koi_depth: float = Field(..., ge=0, description="Profundidad del tránsito (ppm)")
    koi_prad: float = Field(..., gt=0, description="Radio del planeta (radios terrestres)")
    koi_teq: float = Field(..., gt=0, description="Temperatura de equilibrio (K)")
    koi_model_snr: float = Field(..., ge=0, description="Relación señal/ruido")
    koi_steff: float = Field(..., gt=0, description="Temperatura de la estrella (K)")
    koi_srad: float = Field(..., gt=0, description="Radio de la estrella (radios solares)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "koi_period": 9.488, "koi_duration": 2.958, "koi_depth": 615.8,
                "koi_prad": 2.26, "koi_teq": 793, "koi_model_snr": 35.8,
                "koi_steff": 5455, "koi_srad": 0.927,
            }
        }
    }


def confidence_level(probability: float) -> str:
    distance = abs(probability - 0.5)
    if distance >= 0.4:
        return "high"
    if distance >= 0.2:
        return "medium"
    return "low"


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(obj: KeplerObject):
    row = pd.DataFrame([obj.model_dump()])[FEATURES]
    probability = float(model.predict_proba(row)[0, 1])
    return {
        "prediction": "CONFIRMED" if probability >= 0.5 else "FALSE POSITIVE",
        "planet_probability": round(probability, 4),
        "confidence_level": confidence_level(probability),
    }
