import pandas as pd
import numpy as np
from sklearn.datasets import make_classification
from xgboost import XGBClassifier
import joblib
import os
import logging
import watchtower

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
        objective='multi:softprob',
        num_class=5,
        eval_metric='mlogloss',
        use_label_encoder=False
    )
    model.fit(X, y)

    os.makedirs("model/output", exist_ok=True)
    joblib.dump(model, "model/output/xgb_lead_model.pkl")
    logger.info("Model saved to model/output/xgb_lead_model.pkl")

if __name__ == "__main__":
    generate_and_train()