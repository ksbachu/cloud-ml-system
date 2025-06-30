import pandas as pd
import numpy as np
from sklearn.datasets import make_classification
from xgboost import XGBClassifier
import os
import logging
import watchtower
import tarfile
import boto3
from datetime import datetime

# Logger setup with CloudWatch
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/train-model"))

# AWS clients
s3 = boto3.client("s3")
S3_BUCKET = os.environ.get("S3_BUCKET")  # ensure this is set in environment

def generate_and_train():
    logger.info("Generating synthetic dataset...")
    X, y = make_classification(
        n_samples=5000,
        n_features=50,
        n_informative=30,
        n_classes=5,
        random_state=42
    )

    logger.info("Training XGBoost model...")
    model = XGBClassifier(
        objective='multi:softmax',
        num_class=5,
        eval_metric='mlogloss',
        use_label_encoder=False
    )
    model.fit(X, y)


    # Create versioned model directory
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_dir = f"model/{timestamp}"
    os.makedirs(model_dir, exist_ok=True)

    model_file_name = "xgboostmodel"
    model_path = f"{model_dir}/{model_file_name}"

    model.get_booster().save_model(model_path)
    logger.info(f"Model saved in XGBoost binary format at: {model_path}")

    # Create tar.gz archive
    tar_path = f"{model_dir}/model.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(model_path, arcname=model_file_name)
    logger.info(f"Model archive created at {tar_path}")

    # Upload to S3: s3://<bucket>/models/xgboostmodel_<timestamp>/model.tar.gz
    s3_key = f"models/xgboostmodel_{timestamp}/model.tar.gz"
    s3.upload_file(tar_path, S3_BUCKET, s3_key)
    logger.info(f"Uploaded model to s3://{S3_BUCKET}/{s3_key}")

if __name__ == "__main__":
    if not os.environ.get("S3_BUCKET"):
        raise EnvironmentError("Missing required environment variable: S3_BUCKET")
    generate_and_train()
