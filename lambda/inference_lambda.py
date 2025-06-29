import boto3
import json
import time
import os
import logging
import watchtower
# Logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/lambda-inference"))
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

sagemaker = boto3.client("sagemaker-runtime", region_name=os.getenv("AWS_REGION"))
s3 = boto3.client("s3")

ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME")
S3_BUCKET = os.getenv("S3_BUCKET")

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    try:
        body = json.loads(event["body"])
        features = body.get("features")

        if not features or len(features) != 50:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Exactly 50 features required."})
            }

        payload = ",".join(str(x) for x in features)
        t1 = time.time()

        # Invoke SageMaker endpoint
        response = sagemaker.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="text/csv",
            Body=payload
        )

        result = response["Body"].read().decode()
        t2 = time.time()

        record = {
            "timestamp": int(t1),
            "features": features,
            "prediction": result,
            "latency": round(t2 - t1, 3)
        }

        # Log to S3
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"inference_logs/{int(t1)}.json",
            Body=json.dumps(record)
        )

        logger.info(json.dumps(record))

        return {
            "statusCode": 200,
            "body": json.dumps({
                "score": result,
                "latency": record["latency"]
            })
        }

    except Exception as e:
        logger.error(str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
