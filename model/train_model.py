import pandas as pd
import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)
from xgboost import XGBClassifier
import os
import logging
import watchtower
import tarfile
import boto3
from datetime import datetime
import json

# AWS Setup
s3 = boto3.client("s3")
S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION")  # Optional region fallback

# Loggers
train_logger = logging.getLogger("train")
train_logger.setLevel(logging.INFO)
train_logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group="/ml/train", stream_name="trainer", create_log_group=True))

val_logger = logging.getLogger("validation")
val_logger.setLevel(logging.INFO)
val_logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group="/ml/validation", stream_name="validator", create_log_group=True))

impact_logger = logging.getLogger("impact")
impact_logger.setLevel(logging.INFO)
impact_logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group="/ml/impact_analysis", stream_name="impact", create_log_group=True))


def generate_and_train():
    train_logger.info("Generating synthetic dataset...")
    X, y = make_classification(
        n_samples=5000,
        n_features=50,
        n_informative=30,
        n_classes=5,
        random_state=43
    )

    train_logger.info("Splitting dataset into train and validation sets...")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    train_logger.info("Training XGBoost model...")
    model = XGBClassifier(
        objective='multi:softmax',
        num_class=5,
        eval_metric='mlogloss',
        use_label_encoder=False
    )
    model.fit(X_train, y_train)

    # Evaluate model
    val_logger.info("Validating model...")
    y_pred = model.predict(X_val)

    acc = accuracy_score(y_val, y_pred)
    report = classification_report(y_val, y_pred, output_dict=True)
    matrix = confusion_matrix(y_val, y_pred)

    val_logger.info(f"Accuracy: {acc:.4f}")
    val_logger.info("Classification Report:\n" + classification_report(y_val, y_pred))
    val_logger.info(f"Confusion Matrix:\n{matrix}")

    # Save metrics
    metrics = {
        "accuracy": acc,
        "classification_report": report,
        "confusion_matrix": matrix.tolist()
    }

    # Versioned model path
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_dir = f"model/{timestamp}"
    os.makedirs(model_dir, exist_ok=True)

    # Save metrics locally
    metrics_path = f"{model_dir}/metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)
    val_logger.info(f"Saved metrics to {metrics_path}")

    # Save model
    model_file_name = "xgboostmodel"
    model_path = f"{model_dir}/{model_file_name}"
    model.get_booster().save_model(model_path)
    train_logger.info(f"Model saved at {model_path}")

    # Archive
    tar_path = f"{model_dir}/model.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(model_path, arcname=model_file_name)
    train_logger.info(f"Archived model at {tar_path}")

    # Upload to S3
    s3_key = f"models/xgboostmodel_{timestamp}/model.tar.gz"
    metrics_key = f"models/xgboostmodel_{timestamp}/metrics.json"

    s3.upload_file(tar_path, S3_BUCKET, s3_key)
    s3.upload_file(metrics_path, S3_BUCKET, metrics_key)
    train_logger.info(f"Uploaded model: s3://{S3_BUCKET}/{s3_key}")
    val_logger.info(f"Uploaded metrics: s3://{S3_BUCKET}/{metrics_key}")

    # Impact analysis log
    for cls, scores in report.items():
        if cls in ['accuracy', 'macro avg', 'weighted avg']:
            continue
        impact_logger.info(
            f"Class {cls}: Precision={scores['precision']:.2f}, Recall={scores['recall']:.2f}, F1={scores['f1-score']:.2f}"
        )


if __name__ == "__main__":
    if not S3_BUCKET:
        raise EnvironmentError("Missing required environment variable: S3_BUCKET")
    generate_and_train()
