"""Entrena el modelo Champion de exoplanetas y lo guarda en models/champion.joblib.

Dataset: Kepler Objects of Interest (cumulative.csv, NASA Exoplanet Archive).
Objetivo: clasificar un objeto como CONFIRMED (1) o FALSE POSITIVE (0).
Los CANDIDATE se excluyen porque aún no tienen una etiqueta confirmada.

Cada entrenamiento se registra en MLflow (parámetros, métricas y modelo).
Los artefactos se guardan en S3 a través del servidor de MLflow.
"""
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA_PATH = Path("data/cumulative.csv")
MODEL_PATH = Path("models/champion.joblib")

# Variables físicas del tránsito y de la estrella (sin koi_score ni koi_fpflag_*,
# que prácticamente revelan la respuesta y harían trampa al modelo).
FEATURES = [
    "koi_period",     # Periodo orbital (días)
    "koi_duration",   # Duración del tránsito (horas)
    "koi_depth",      # Profundidad del tránsito (ppm)
    "koi_prad",       # Radio del planeta (radios terrestres)
    "koi_teq",        # Temperatura de equilibrio (K)
    "koi_model_snr",  # Relación señal/ruido del tránsito
    "koi_steff",      # Temperatura efectiva de la estrella (K)
    "koi_srad",       # Radio de la estrella (radios solares)
]
TARGET = "koi_disposition"

PARAMS = {"n_estimators": 200, "max_depth": 12, "class_weight": "balanced"}

# Servidor de MLflow (se levanta en local; los artefactos van a S3)
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))
mlflow.set_experiment("exoplanetas-kepler")


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df = df[df[TARGET].isin(["CONFIRMED", "FALSE POSITIVE"])]

    X = df[FEATURES]
    y = (df[TARGET] == "CONFIRMED").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),  # 363 filas con vacíos
            ("model", RandomForestClassifier(**PARAMS, random_state=42, n_jobs=-1)),
        ]
    )
    with mlflow.start_run(run_name="random-forest"):
        pipeline.fit(X_train, y_train)

        proba = pipeline.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = {
            "accuracy": accuracy_score(y_test, pred),
            "f1": f1_score(y_test, pred),
            "roc_auc": roc_auc_score(y_test, proba),
        }
        for name, value in metrics.items():
            print(f"{name}: {value:.3f}")

        # Registro en MLflow
        mlflow.log_params(PARAMS)
        mlflow.log_param("features", ",".join(FEATURES))
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_metrics(metrics)
        # MLflow 3 guarda modelos sklearn con skops (formato seguro); hay que
        # declarar como confiables los tipos internos del RandomForest.
        mlflow.sklearn.log_model(
            pipeline,
            name="model",
            registered_model_name="exoplanet-champion",
            skops_trusted_types=["numpy.dtype", "sklearn.tree._tree.Tree"],
        )

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH, compress=3)
    print(f"Modelo guardado en {MODEL_PATH}")


if __name__ == "__main__":
    main()
