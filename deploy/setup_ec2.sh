#!/bin/bash
# Instala y deja corriendo MLflow + Airflow en una instancia EC2 (Ubuntu 24.04).
# Uso (dentro de la instancia):  bash deploy/setup_ec2.sh
# - MLflow:  http://127.0.0.1:5001  (artefactos en S3)
# - Airflow: http://127.0.0.1:8080
# Ambos se abren desde tu Mac con un túnel SSH (no quedan expuestos a internet).
set -euo pipefail

BUCKET="mafer-exoplanetas-mlops-426143721250"
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
USUARIO="$(whoami)"
AIRFLOW_VENV="$HOME/airflow-venv"
AIRFLOW_VERSION="3.1.0"
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

echo "==> Paquetes del sistema"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git

echo "==> Memoria swap de 2 GB (Airflow + MLflow en 4 GB de RAM van justos)"
if [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> Entorno del proyecto (API, entrenamiento, DVC y MLflow)"
cd "$PROJ"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt "dvc[s3]" mlflow
# Versiones de boto3/botocore compatibles con dvc-s3 (aiobotocore)
.venv/bin/pip install "boto3==1.43.117" "botocore==1.43.117"

echo "==> Airflow ${AIRFLOW_VERSION} en su propio entorno"
python3 -m venv "$AIRFLOW_VENV"
"$AIRFLOW_VENV/bin/pip" install --upgrade pip
"$AIRFLOW_VENV/bin/pip" install "apache-airflow==${AIRFLOW_VERSION}" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PY_VER}.txt"

echo "==> Servicio de MLflow (systemd)"
sudo tee /etc/systemd/system/mlflow.service > /dev/null <<UNIT
[Unit]
Description=Servidor de MLflow
After=network-online.target

[Service]
User=${USUARIO}
WorkingDirectory=${PROJ}
ExecStart=${PROJ}/.venv/bin/mlflow server --backend-store-uri sqlite:///${PROJ}/mlflow.db --artifacts-destination s3://${BUCKET}/mlflow --host 127.0.0.1 --port 5001
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

echo "==> Servicio de Airflow (systemd)"
sudo tee /etc/systemd/system/airflow.service > /dev/null <<UNIT
[Unit]
Description=Apache Airflow (standalone)
After=network-online.target mlflow.service

[Service]
User=${USUARIO}
WorkingDirectory=${HOME}
Environment=AIRFLOW_HOME=${HOME}/airflow
Environment=AIRFLOW__CORE__DAGS_FOLDER=${PROJ}/dags
Environment=AIRFLOW__CORE__LOAD_EXAMPLES=False
Environment=EXOPLANET_PYTHON=${PROJ}/.venv/bin/python
Environment=PATH=${AIRFLOW_VENV}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${AIRFLOW_VENV}/bin/airflow standalone
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now mlflow airflow

echo
echo "Listo. Espera 1-2 minutos a que Airflow arranque."
echo "Contraseña de Airflow (usuario admin):"
echo "  cat ~/airflow/simple_auth_manager_passwords.json.generated"
echo "Ver estado:  sudo systemctl status mlflow airflow"
echo "Ver logs:    journalctl -u airflow -f"
