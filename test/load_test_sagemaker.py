import requests
import concurrent.futures
import time
import logging
import json
import random
import os
import watchtower
# === Config ===
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL")
N_REQUESTS = 1
CONCURRENCY = 1
LATENCY_THRESHOLD = 1.0  # seconds

# === Logging Setup ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/test-load-api"))

# === Generate Valid Payload ===
def generate_payload():
    # Generate 50 valid float features
    features = [round(random.uniform(0.1, 5.0), 2) for _ in range(50)]
    return {"features": features}

# === Invoke API Gateway ===
def invoke_api(i):
    payload = generate_payload()
    t1 = time.time()
    try:
        response = requests.post(API_GATEWAY_URL, json=payload)
        latency = time.time() - t1
        logger.info(f"Request {i+1}: {response.status_code}, latency={latency:.3f}s, body={response.text}")
        return latency
    except Exception as e:
        logger.error(f"Request {i+1} failed: {str(e)}")
        return None

# === Run Load Test ===
start = time.time()
latencies = []

with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = [executor.submit(invoke_api, i) for i in range(N_REQUESTS)]
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        if result is not None:
            latencies.append(result)

end = time.time()

# === Summary ===
over_threshold = sum(1 for l in latencies if l > LATENCY_THRESHOLD)
p90 = sorted(latencies)[int(0.9 * len(latencies))] if latencies else None
p95 = sorted(latencies)[int(0.95 * len(latencies))] if latencies else None
p99 = sorted(latencies)[int(0.99 * len(latencies))] if latencies else None

print("\n=== Load Test Summary ===")
summary = {
    "Total Requests": N_REQUESTS,
    "Completed": len(latencies),
    "Failed": N_REQUESTS - len(latencies),
    "Avg Latency (s)": round(sum(latencies)/len(latencies), 3) if latencies else None,
    "Max Latency (s)": round(max(latencies), 3) if latencies else None,
    "P90 Latency (s)": round(p90, 3) if p90 else None,
    "P95 Latency (s)": round(p95, 3) if p95 else None,
    "P99 Latency (s)": round(p99, 3) if p99 else None,
    "Over 1s": over_threshold
}
for k, v in summary.items():
    print(f"{k}: {v}")
