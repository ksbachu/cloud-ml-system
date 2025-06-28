import boto3
import logging
import os
import watchtower

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/upload-model"))

def ensure_bucket(bucket_name, region="ap-south-1"):
    s3 = boto3.client("s3", region_name=region)
    buckets = s3.list_buckets()
    if not any(b["Name"] == bucket_name for b in buckets["Buckets"]):
        logger.info(f"Bucket {bucket_name} does not exist. Creating...")
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
    else:
        logger.info(f"Bucket {bucket_name} already exists.")

def upload_model(bucket_name="cloud-ml-lead-models", key="xgb_lead_model.pkl"):
    ensure_bucket(bucket_name)
    s3 = boto3.client("s3")
    local_path = "model/output/xgb_lead_model.pkl"
    if os.path.exists(local_path):
        s3.upload_file(local_path, bucket_name, key)
        logger.info(f"Model uploaded to s3://{bucket_name}/{key}")
    else:
        logger.error(f"Model file not found at {local_path}")

if __name__ == "__main__":
    upload_model()