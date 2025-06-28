import boto3
import logging
import watchtower
import os
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group="/ml/deploy-model"))

execution_role_arn = os.getenv("SAGEMAKER_EXECUTION_ROLE_ARN")
bucket = os.getenv("S3_BUCKET")
region = os.getenv("AWS_REGION")

def deploy_model(
    model_name="lead-scoring-xgb",
    bucket=bucket,
    model_key="xgb_lead_model.pkl",
    instance_type="ml.m5.large",
    region=region,
    role_arn=execution_role_arn
):
    sagemaker = boto3.client("sagemaker", region_name=region)

    model_data_url = f"s3://{bucket}/{model_key}"
    container = {
        'Image': '683313688378.dkr.ecr.ap-south-1.amazonaws.com/xgboost:1.5-1',
        'ModelDataUrl': model_data_url
    }

    logger.info("Creating SageMaker model...")
    sagemaker.create_model(
        ModelName=model_name,
        ExecutionRoleArn=role_arn,
        PrimaryContainer=container
    )

    logger.info("Creating endpoint config...")
    sagemaker.create_endpoint_config(
        EndpointConfigName=model_name + "-config",
        ProductionVariants=[{
            'VariantName': 'AllTraffic',
            'ModelName': model_name,
            'InitialInstanceCount': 1,
            'InstanceType': instance_type,
            'InitialVariantWeight': 1
        }]
    )

    logger.info("Creating endpoint...")
    sagemaker.create_endpoint(
        EndpointName=model_name + "-endpoint",
        EndpointConfigName=model_name + "-config"
    )
    logger.info("Waiting for endpoint to be InService...")
    waiter = sagemaker.get_waiter('endpoint_in_service')
    waiter.wait(EndpointName=model_name + "-endpoint")
    logger.info(f"Endpoint is deployed and InService: {model_name}-endpoint")

if __name__ == "__main__":
    deploy_model()
