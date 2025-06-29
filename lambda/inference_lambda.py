import boto3
import json
import time
import os
import logging
import watchtower

# === Logger Setup ===
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/lambda-inference"))

# === AWS Clients ===
sagemaker = boto3.client("sagemaker-runtime", region_name=os.getenv("AWS_REGION"))
s3 = boto3.client("s3")

# === Environment Variables ===
ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME")
S3_BUCKET = os.getenv("S3_BUCKET")

# === Lambda Handler ===
def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    try:
        body = json.loads(event.get("body", "{}"))
        features = body.get("features")

        # Validate features
        if not isinstance(features, list) or len(features) != 50:
            logger.warning("Invalid features input")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Exactly 50 numerical features required."})
            }

        try:
            numeric_features = [float(x) for x in features]
        except ValueError:
            logger.warning("Feature parsing failed")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "All features must be numbers."})
            }

        payload = ",".join(str(x) for x in numeric_features)
        t1 = time.time()

        # Invoke SageMaker
        response = sagemaker.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="text/csv",
            Body=payload
        )
        result = response["Body"].read().decode()
        t2 = time.time()

        # Log and save
        record = {
            "timestamp": int(t1),
            "features": numeric_features,
            "prediction": result,
            "latency": round(t2 - t1, 3)
        }

        logger.info("Inference result: %s", json.dumps(record))

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"inference_logs/{int(t1)}.json",
            Body=json.dumps(record)
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "score": result,
                "latency": record["latency"]
            })
        }

    except Exception as e:
        logger.exception("Error during inference")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
