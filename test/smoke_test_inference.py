import boto3
import json
import os

endpoint_name = os.getenv("SAGEMAKER_ENDPOINT_NAME", "lead-scoring-xgb-endpoint")
region = os.getenv("AWS_REGION")

runtime = boto3.client("sagemaker-runtime", region_name=region)

# Dummy input - should match the model's expected input (50 features)
payload = {"inputs": [0.1] * 50}

print(f"Invoking SageMaker endpoint: {endpoint_name}")
response = runtime.invoke_endpoint(
    EndpointName=endpoint_name,
    ContentType="application/json",
    Body=json.dumps(payload)
)

result = response["Body"].read().decode()
print("Inference result:", result)
