import pandas as pd
import numpy as np
from sklearn.datasets import make_classification
from xgboost import XGBClassifier
import os
import logging
import watchtower
import tarfile

# Logger setup with CloudWatch
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/train-model"))

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

    os.makedirs("model", exist_ok=True)

    # Valid SageMaker model filename (no dots, no underscores)
    model_file_name = "xgboostmodel"  # must match regex ^[a-zA-Z0-9](-*[a-zA-Z0-9])*$

    # Save model using booster.save_model
    model.get_booster().save_model(f"model/{model_file_name}")
    logger.info(f"Model saved in XGBoost binary format at: model/{model_file_name}")

    # Tar it with correct internal file name
    with tarfile.open("model/model.tar.gz", "w:gz") as tar:
        tar.add(f"model/{model_file_name}", arcname=model_file_name)

    logger.info("Model archive created at model/model.tar.gz")

if __name__ == "__main__":
    generate_and_train()
