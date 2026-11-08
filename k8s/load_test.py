"""Simula tráfico elevado contra POST /predict y mide la respuesta de la API.

Uso:
    python k8s/load_test.py                       # 50 usuarios durante 90 s
    python k8s/load_test.py --users 80 --seconds 120

Cada "usuario" manda peticiones sin parar. Cada 5 segundos se imprime:
peticiones por segundo, latencia mediana (p50), latencia p95 y errores.
"""
import argparse
import json
import statistics
import threading
import time
import urllib.error
import urllib.request

PAYLOAD = json.dumps({
    "koi_period": 9.488, "koi_duration": 2.958, "koi_depth": 615.8,
    "koi_prad": 2.26, "koi_teq": 793, "koi_model_snr": 35.8,
    "koi_steff": 5455, "koi_srad": 0.927,
}).encode()

lock = threading.Lock()
latencies: list[float] = []
errors = 0


def worker(url: str, stop_at: float, timeout: float) -> None:
    global errors
    while time.time() < stop_at:
        request = urllib.request.Request(
            url, data=PAYLOAD, headers={"Content-Type": "application/json"}
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response.read()
            elapsed = time.perf_counter() - start
            with lock:
                latencies.append(elapsed)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            with lock:
                errors += 1
            time.sleep(0.2)


def main() -> None:
    global errors
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080/predict")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    stop_at = time.time() + args.seconds
    for _ in range(args.users):
        threading.Thread(target=worker, args=(args.url, stop_at, args.timeout), daemon=True).start()

    print(f"Carga: {args.users} usuarios simultáneos durante {args.seconds} s -> {args.url}\n")
    print(f"{'Tiempo':>6s} {'Pet/s':>7s} {'p50 (ms)':>9s} {'p95 (ms)':>9s} {'Errores':>8s}")
    started = time.time()
    total_ok = total_err = 0
    while time.time() < stop_at:
        time.sleep(5)
        with lock:
            window, latencies[:] = list(latencies), []
            window_errors, errors = errors, 0
        total_ok += len(window)
        total_err += window_errors
        if window:
            p50 = statistics.median(window) * 1000
            p95 = sorted(window)[int(len(window) * 0.95) - 1] * 1000
        else:
            p50 = p95 = float("nan")
        print(f"{time.time() - started:5.0f}s {len(window) / 5:7.1f} {p50:9.0f} {p95:9.0f} {window_errors:8d}")

    total = total_ok + total_err
    print(f"\nTotal: {total_ok} correctas, {total_err} con error "
          f"({total_err / total:.1%} de error)" if total else "\nSin peticiones")


if __name__ == "__main__":
    main()
