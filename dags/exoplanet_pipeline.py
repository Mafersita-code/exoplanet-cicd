"""DAG de Airflow: pipeline de entrenamiento del modelo de exoplanetas.

Flujo:
    descargar_datos (DVC desde S3)
        -> entrenar (train.py, registra en MLflow)
        -> pruebas (pytest)
        -> subir_modelo (champion.joblib a S3)

Requisitos: el servidor de MLflow corriendo en http://127.0.0.1:5001
y las credenciales de AWS configuradas (aws configure).
"""
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROYECTO = "/Users/kipandisita_8/Documents/MINERIA_DE_DATOS/exoplanet-cicd"
PYTHON = f"{PROYECTO}/.venv.nosync/bin/python"
BUCKET = "mafer-exoplanetas-mlops-426143721250"

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
        bash_command=(
            f"aws s3 cp models/champion.joblib s3://{BUCKET}/models/champion.joblib "
            "--region us-east-2"
        ),
        cwd=PROYECTO,
    )

    descargar_datos >> entrenar >> pruebas >> subir_modelo
