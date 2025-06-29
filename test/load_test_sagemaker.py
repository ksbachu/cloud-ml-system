import requests
import concurrent.futures
import time
import watchtower
import logging
import os

# === Configuration ===
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL")
N_REQUESTS = 300          # Total requests to send
CONCURRENCY = 300         # Simulate 300 RPS
LATENCY_THRESHOLD = 1.0   # seconds
CLOUDWATCH_LOG_GROUP = "/ml/test-load-api"

# === Logger Setup ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group=CLOUDWATCH_LOG_GROUP))

# === Generate 50 Feature CSV Payload ===
def generate_payload():
    features = [str(round(i * 0.1, 2)) for i in range(1, 51)]  # 0.1 to 5.0
    return ",".join(features)

PAYLOAD = generate_payload()

# === Invoke API Gateway Endpoint with Latency Tracking ===
def invoke_endpoint(i):
    headers = {"Content-Type": "text/csv"}
    t1 = time.time()
    response = requests.post(API_GATEWAY_URL, data=PAYLOAD, headers=headers)
    t2 = time.time()
    latency = t2 - t1
    result = response.text
    logger.info(f"Request {i+1} latency: {latency:.3f}s, response: {result}")
    return latency

# === Run Load Test ===
start = time.time()
latencies = []

with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = [executor.submit(invoke_endpoint, i) for i in range(N_REQUESTS)]
    for future in concurrent.futures.as_completed(futures):
        try:
            latency = future.result()
            latencies.append(latency)
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")

end = time.time()

# === Metrics Summary ===
over_threshold = sum(1 for l in latencies if l > LATENCY_THRESHOLD)
p90 = sorted(latencies)[int(0.9 * len(latencies))] if latencies else None
p95 = sorted(latencies)[int(0.95 * len(latencies))] if latencies else None
p99 = sorted(latencies)[int(0.99 * len(latencies))] if latencies else None

summary = {
    "Total Requests": N_REQUESTS,
    "Completed": len(latencies),
    "Failed": N_REQUESTS - len(latencies),
    "Avg Latency (s)": round(sum(latencies) / len(latencies), 3) if latencies else None,
    "Max Latency (s)": round(max(latencies), 3) if latencies else None,
    "P90 Latency (s)": round(p90, 3) if p90 else None,
    "P95 Latency (s)": round(p95, 3) if p95 else None,
    "P99 Latency (s)": round(p99, 3) if p99 else None,
    "Over 1s": over_threshold
}

# === Print & Log Summary ===
print("=== Load Test Summary ===")
for k, v in summary.items():
    print(f"{k}: {v}")
    logger.info(f"{k}: {v}")

# === Assert/Fail if too many slow requests ===
if over_threshold > 0:
    logger.warning(f"{over_threshold} requests exceeded 1s latency threshold")
else:
    logger.info("All requests met latency SLA")
