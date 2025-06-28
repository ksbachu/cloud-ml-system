# Directory: inference/inference.py
import boto3
import json
import logging
import watchtower
import numpy as np

# Setup logger with CloudWatch
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/inference"))

# Set your endpoint name here
ENDPOINT_NAME = "lead-scoring-xgb-endpoint"
REGION = "ap-south-1"

# Create SageMaker runtime client
runtime = boto3.client("sagemaker-runtime", region_name=REGION)

def invoke_endpoint(payload):
    try:
        response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(payload)
        )
        result = json.loads(response["Body"].read().decode())
        logger.info(f"Inference success: {result}")
        return result
    except Exception as e:
        logger.error(f"Error invoking endpoint: {str(e)}")
        raise

def generate_test_payload(num_samples=1, num_features=50):
    X = np.random.rand(num_samples, num_features)
    return {"instances": X.tolist()}

if __name__ == "__main__":
    logger.info("Starting inference test")
    test_payload = generate_test_payload(num_samples=3)
    result = invoke_endpoint(test_payload)
    logger.info(f"Predicted class probabilities: {result}")
