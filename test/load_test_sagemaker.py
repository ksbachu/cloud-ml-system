import requests
import concurrent.futures
import time
import logging
import json
import random
import os
import uuid
import boto3
import watchtower
from datetime import datetime

# === Config ===
# API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL")
API_GATEWAY_URL = 'https://3p45j4ezz4.execute-api.us-east-1.amazonaws.com/predict'
S3_BUCKET = os.environ.get("S3_BUCKET")
N_REQUESTS = 300
CONCURRENCY = 300
LATENCY_THRESHOLD = 1.0  # seconds

# === Logging Setup ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
# logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/test-load-api"))

# === S3 Client ===
s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))

# === Generate Valid Payload ===
def generate_payload():
    features = [round(random.uniform(0.1, 5.0), 2) for _ in range(50)]
    return {"features": features}

# === Invoke API Gateway ===
def invoke_api(i):
    payload = generate_payload()
    t1 = time.time()
    try:
        response = requests.post(API_GATEWAY_URL, json=payload)
        latency = time.time() - t1
        status = response.status_code
        response_body = response.text

        predicted_class = "N/A"
        try:
            data = response.json()
            predicted_class = data.get("predicted_class", "N/A")
        except json.JSONDecodeError:
            logger.warning(f"Request {i+1}: Response not valid JSON")

        logger.info(f"Request {i+1}: status={status}, latency={latency:.3f}s, class={predicted_class}")
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

summary = {
    "Test ID": str(uuid.uuid4()),
    "Timestamp": datetime.utcnow().isoformat(),
    "Total Requests": N_REQUESTS,
    "Completed": len(latencies),
    "Failed": N_REQUESTS - len(latencies),
    "Avg Latency (s)": round(sum(latencies)/len(latencies), 3) if latencies else None,
    "Max Latency (s)": round(max(latencies), 3) if latencies else None,
    "P90 Latency (s)": round(p90, 3) if p90 else None,
    "P95 Latency (s)": round(p95, 3) if p95 else None,
    "P99 Latency (s)": round(p99, 3) if p99 else None,
    "Over 1s": over_threshold,
    "Test Duration (s)": round(end - start, 2)
}

# === Print Summary ===
print("\n=== Load Test Summary ===")
for k, v in summary.items():
    print(f"{k}: {v}")

# === Write Summary to S3 ===
report_key = f"test/load_test_report_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
try:
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=report_key,
        Body=json.dumps(summary, indent=2).encode("utf-8"),
        ContentType="application/json"
    )
    logger.info(f"Load test report successfully uploaded to s3://{S3_BUCKET}/{report_key}")
except Exception as e:
    logger.error(f"Failed to upload report to S3: {str(e)}")
