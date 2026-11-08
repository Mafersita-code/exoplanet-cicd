"""DAG de Airflow: pipeline de entrenamiento del modelo de exoplanetas.

Flujo:
    descargar_datos (DVC desde S3)
        -> entrenar (train.py, registra en MLflow)
        -> pruebas (pytest)
        -> subir_modelo (champion.joblib a S3)

Funciona igual en la Mac y en el servidor EC2:
- La carpeta del proyecto se calcula a partir de este archivo.
- El Python del proyecto se toma de la variable EXOPLANET_PYTHON
  (por defecto <proyecto>/.venv/bin/python).
- Requiere el servidor de MLflow en http://127.0.0.1:5001 y credenciales
  de AWS (en EC2 las da el rol de la instancia).
"""
import os
from datetime import datetime
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROYECTO = str(Path(__file__).resolve().parents[1])
PYTHON = os.getenv("EXOPLANET_PYTHON", f"{PROYECTO}/.venv/bin/python")
BUCKET = "mafer-exoplanetas-mlops-426143721250"

SUBIR_MODELO = (
    "import boto3; "
    f"boto3.client('s3', region_name='us-east-2').upload_file("
    f"'models/champion.joblib', '{BUCKET}', 'models/champion.joblib'); "
    "print('Modelo subido a S3')"
)

with DAG(
    dag_id="exoplanet_pipeline",
    description="Datos desde S3 -> entrenamiento con MLflow -> pruebas -> modelo a S3",
    start_date=datetime(2026, 11, 1),
    schedule=None,          # Se ejecuta a mano desde la interfaz
    catchup=False,
    tags=["mlops", "exoplanetas", "aws"],
) as dag:

    descargar_datos = BashOperator(
        task_id="descargar_datos",
        bash_command=f"{PYTHON} -m dvc pull data/cumulative.csv.dvc",
        cwd=PROYECTO,
    )

    entrenar = BashOperator(
        task_id="entrenar",
        bash_command=f"{PYTHON} train.py",
        cwd=PROYECTO,
        env={"MLFLOW_TRACKING_URI": "http://127.0.0.1:5001"},
        append_env=True,
    )

    pruebas = BashOperator(
        task_id="pruebas",
        bash_command=f"{PYTHON} -m pytest -q",
        cwd=PROYECTO,
    )

    subir_modelo = BashOperator(
        task_id="subir_modelo",
        bash_command=f'{PYTHON} -c "{SUBIR_MODELO}"',
        cwd=PROYECTO,
    )

    descargar_datos >> entrenar >> pruebas >> subir_modelo
