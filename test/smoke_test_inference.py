import boto3
import os

# session = boto3.Session(profile_name='cloud-ml-dev')
# endpoint_name = os.getenv("SAGEMAKER_ENDPOINT_NAME", "xgboostmodel-endpoint3")
# region = os.getenv("AWS_REGION", "us-east-1")
# runtime = session.client("sagemaker-runtime", region_name=region)

endpoint_name = os.getenv("SAGEMAKER_ENDPOINT_NAME", "xgboostmodel-endpoint3")
region = os.getenv("AWS_REGION", "us-east-1")
runtime = boto3.client("sagemaker-runtime", region_name=region)
# Dummy input - 50 features
csv_payload = ",".join(["0.1"] * 50)

print(f"Invoking SageMaker endpoint: {endpoint_name}")
response = runtime.invoke_endpoint(
    EndpointName=endpoint_name,
    ContentType="text/csv",   
    Body=csv_payload
)

# Process the result
result = response["Body"].read().decode().strip()
lead_score = int(result) + 1  # 0-based to 1-based

print("Lead Score:", lead_score)