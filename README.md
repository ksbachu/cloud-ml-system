# cloud-ml-system

A cloud-based machine learning system for lead scoring using AWS SageMaker, Lambda, API Gateway, and Terraform.

## Project Structure

```
.
├── inference/                  # Inference client code
│   └── inference.py            # Local inference script for SageMaker endpoint
├── infra/                      # Deployment and S3 upload scripts
│   ├── deploy_model_to_sagemaker.py  # Deploys model to SageMaker
│   └── upload_model_to_s3.py         # Uploads model artifact to S3
├── lambda/                     # Lambda function for inference API
│   ├── inference_lambda.py     # Lambda handler for inference
│   └── requirements.txt        # Lambda dependencies
├── logs/                       # (Empty) Directory for logs
├── model/                      # Model training code
│   └── train_model.py          # Trains XGBoost model and uploads to S3
├── terraform/                  # Infrastructure as code (Terraform)
│   ├── main.tf                 # Main Terraform configuration
│   ├── outputs.tf              # Terraform outputs
│   ├── variables.tf            # Terraform variables
│   └── terrafrom.tfvars        # Terraform variable values
├── test/                       # Test scripts
│   ├── load_test_sagemaker.py  # Load test for API Gateway/SageMaker
│   └── smoke_test_inference.py # Smoke test for SageMaker endpoint
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow for CI/CD
├── requirements.txt            # Project dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

## Key Components

- **Model Training:**  
  [`model/train_model.py`](model/train_model.py) generates synthetic data, trains an XGBoost model, evaluates it, and uploads the model and metrics to S3.

- **Model Deployment:**  
  [`infra/deploy_model_to_sagemaker.py`](infra/deploy_model_to_sagemaker.py) deploys the trained model to SageMaker using the official XGBoost container.

- **S3 Upload:**  
  [`infra/upload_model_to_s3.py`](infra/upload_model_to_s3.py) ensures the S3 bucket exists and uploads the model artifact.

- **Inference Lambda:**  
  [`lambda/inference_lambda.py`](lambda/inference_lambda.py) is an AWS Lambda function that receives HTTP requests, validates input, invokes the SageMaker endpoint, and logs results to S3 and CloudWatch.

- **API Gateway:**  
  Provisioned via Terraform ([`terraform/main.tf`](terraform/main.tf)), exposes the Lambda as a REST API.

- **Testing:**  
  - [`test/smoke_test_inference.py`](test/smoke_test_inference.py): Smoke test for direct SageMaker endpoint invocation.
  - [`test/load_test_sagemaker.py`](test/load_test_sagemaker.py): Load test for the API Gateway endpoint.

- **Infrastructure as Code:**  
  [`terraform/`](terraform/) contains all Terraform files to provision AWS resources: S3, IAM roles, Lambda, SageMaker, and API Gateway.

- **CI/CD:**  
  [`deploy.yml`](.github/workflows/deploy.yml) automates training, deployment, and testing on push or manual trigger.

## Setup & Usage

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

2. **Train and upload model:**
   ```sh
   python model/train_model.py
   ```

3. **Deploy infrastructure:**
   ```sh
   cd terraform
   terraform init
   terraform apply -auto-approve
   ```

4. **Run inference locally:**
   ```sh
   python inference/inference.py
   ```

5. **Test deployed endpoint:**
   ```sh
   python test/smoke_test_inference.py
   python test/load_test_sagemaker.py
   ```

## Notes

- Environment variables such as `AWS_REGION`, `S3_BUCKET`, and `SAGEMAKER_ENDPOINT_NAME` are required for scripts and Lambda.
- Lambda and SageMaker permissions are managed via Terraform IAM roles and policies.
- All logs are sent to AWS CloudWatch for monitoring and debugging.

---

For more details, see comments in each script and the [GitHub Actions workflow](.github/workflows/deploy.yml).