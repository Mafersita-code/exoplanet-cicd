# Kubernetes: autoescalado de la API de exoplanetas

Demostración de cómo una sola réplica de la API se satura con tráfico elevado y cómo el **Horizontal Pod Autoscaler (HPA)** de Kubernetes crea réplicas automáticamente con la misma imagen Docker.

## Archivos

| Archivo | Qué hace |
|---|---|
| `deployment.yaml` | Corre la imagen `exoplanet-api:v1` con 1 réplica, límites de CPU/memoria y probes de salud |
| `service.yaml` | Expone la API en `http://localhost:8080` y reparte el tráfico entre las réplicas |
| `hpa.yaml` | Escala de 1 a 5 réplicas cuando el CPU promedio supera el 50 % del *request* |
| `load_test.py` | Simula usuarios simultáneos contra `POST /predict` y mide peticiones/s, latencia y errores |

## Requisitos

1. Docker Desktop → Settings → Kubernetes → **Enable Kubernetes** (kubeadm) → Apply.
2. Imagen local construida: `docker build -t exoplanet-api:v1 .` (desde la raíz del proyecto).
3. **metrics-server**, sin el cual el HPA no puede medir el CPU:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl top nodes
```

## Paso 1: una sola réplica

```bash
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
kubectl get pods
curl http://localhost:8080/health
```

En otra terminal, simula el tráfico:

```bash
python k8s/load_test.py --users 50 --seconds 90
```

## Paso 2: activar el autoescalado

```bash
kubectl apply -f k8s/hpa.yaml
```

En una terminal observa las réplicas (Ctrl+C para salir):

```bash
kubectl get hpa exoplanet-api --watch
```

En otra, vuelve a lanzar la misma carga:

```bash
python k8s/load_test.py --users 50 --seconds 170
```

Al terminar la carga, el HPA espera 60 s y vuelve a bajar a 1 réplica.

## Resultados obtenidos (50 usuarios simultáneos)

| | 1 réplica | Con HPA (hasta 5 réplicas) |
|---|---|---|
| Peticiones por segundo | ~24 | ~80–125 |
| Latencia mediana (p50) | ~1,600–2,000 ms | ~300 ms |
| Errores | 0 %* | ~1 % (mientras arrancaban las réplicas) |

El HPA detectó el CPU al 200 % del *request*, subió a 4 réplicas a los ~60 s de carga y después a 5.

\* **Lección aprendida: la readiness probe.** En la primera prueba la *readiness probe* usaba el tiempo de espera por defecto (1 s). Bajo carga, `/health` tardaba más que eso, Kubernetes marcó el pod como "no listo" y lo sacó del Service: la API **dejó de responder** (36 % de errores). Además, el HPA **ignora las métricas de los pods no listos**, así que tampoco escalaba. Con `timeoutSeconds: 5` el pod sigue recibiendo tráfico (aunque lento) y el HPA puede escalar.

## Limpieza

```bash
kubectl delete -f k8s/
```
