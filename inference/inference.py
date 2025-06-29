import boto3
import json
import logging
import watchtower
import numpy as np
import os
# Setup logger with CloudWatch
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/inference"))

# Set your endpoint name here
ENDPOINT_NAME = "xgboostmodel-endpoint3"
REGION = os.getenv("AWS_REGION")

# Create SageMaker runtime client
runtime = boto3.client("sagemaker-runtime", region_name=REGION)

def invoke_endpoint(payload):
    logger.info(f"Invoking endpoint: {ENDPOINT_NAME} with payload: {payload}")
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
    test_payload = generate_test_payload(num_samples=5)
    result = invoke_endpoint(test_payload)
    # Convert 0-based class label to 1-based lead score
    lead_scores = [int(pred) + 1 for pred in result]
    logger.info(f"Lead Scores (1-5): {lead_scores}")
