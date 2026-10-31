# Exoplanet CI/CD — Práctica 8

API FastAPI que clasifica objetos de interés de Kepler (KOI) como **CONFIRMED** (planeta confirmado) o **FALSE POSITIVE**, con pruebas automáticas, Docker y un pipeline de GitHub Actions que publica la imagen en GitHub Container Registry (GHCR).

> Modelo con fines didácticos. No debe usarse para decisiones científicas reales.

## Dataset

`data/cumulative.csv` — Kepler Objects of Interest, NASA Exoplanet Archive (9,564 objetos).

- **Objetivo:** `koi_disposition` → CONFIRMED (1) vs FALSE POSITIVE (0). Los CANDIDATE se excluyen porque aún no tienen etiqueta confirmada.
- **Variables:** `koi_period`, `koi_duration`, `koi_depth`, `koi_prad`, `koi_teq`, `koi_model_snr`, `koi_steff`, `koi_srad`.
- Se excluyen `koi_score` y `koi_fpflag_*` porque prácticamente revelan la respuesta (fuga de información).
- **Modelo:** `Pipeline(SimpleImputer(median) → RandomForestClassifier)` guardado en `models/champion.joblib`.

## Estructura

```
app/main.py               API FastAPI (/, /health, /docs, /predict)
templates/index.html      Formulario web
models/champion.joblib    Modelo entrenado (lo genera train.py)
train.py                  Entrenamiento del modelo
tests/                    4 pruebas con pytest
Dockerfile                Imagen de la API
.github/workflows/cicd.yml  CI (pytest) + CD (publicación en GHCR)
```

## Ejecución local (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python train.py            # opcional: regenera el modelo
python -m pytest -v        # 4 pruebas deben pasar
python -m uvicorn app.main:app --reload
```

En Windows (CMD) la activación es `.venv\Scripts\activate.bat`.

- http://127.0.0.1:8000/ — formulario
- http://127.0.0.1:8000/docs — documentación interactiva
- http://127.0.0.1:8000/health — `{"status":"ok"}`

JSON de ejemplo para `POST /predict` (Kepler-227 b):

```json
{
  "koi_period": 9.488,
  "koi_duration": 2.958,
  "koi_depth": 615.8,
  "koi_prad": 2.26,
  "koi_teq": 793,
  "koi_model_snr": 35.8,
  "koi_steff": 5455,
  "koi_srad": 0.927
}
```

La respuesta contiene `prediction`, `planet_probability` y `confidence_level`.

## Docker

```bash
docker build -t exoplanet-api:v1 .
docker images
docker run --rm --name exoplanet-api -p 8000:8000 exoplanet-api:v1
```

## CI/CD

- **test:** instala dependencias y ejecuta `pytest` en cada push y pull request a `main`.
- **docker:** depende de `test` (`needs: test`). Solo en push a `main`, construye la imagen y la publica en `ghcr.io/<usuario>/exoplanet-cicd` con las etiquetas `latest` y el SHA del commit.

Si las pruebas fallan, el job `docker` queda omitido (*skipped*) y no se publica ninguna imagen.

```bash
docker pull ghcr.io/<usuario>/exoplanet-cicd:latest
docker run --rm -p 8000:8000 ghcr.io/<usuario>/exoplanet-cicd:latest
```
