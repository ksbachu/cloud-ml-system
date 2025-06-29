from sagemaker import image_uris
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
    model_name="xgboostmodel",
    bucket=bucket,
    model_key="model.tar.gz",
    instance_type="ml.t2.medium",
    region=region,
    role_arn=execution_role_arn
):
    sagemaker = boto3.client("sagemaker", region_name=region)
    model_data_url = f"s3://{bucket}/{model_key}"
    endpoint_config_name = model_name + "-config"
    endpoint_name = model_name + "-endpoint"

    # ✅ Get official container image URI
    container_image = image_uris.retrieve(
        framework='xgboost',
        region=region,
        version='1.7-1',
        instance_type=instance_type
    )

    # ✅ Delete existing model if it exists
    try:
        sagemaker.describe_model(ModelName=model_name)
        logger.info(f"Model {model_name} already exists. Deleting...")
        sagemaker.delete_model(ModelName=model_name)
    except sagemaker.exceptions.ClientError as e:
        if "Could not find model" in str(e):
            pass
        else:
            raise

    # ✅ Create model
    logger.info("Creating model...")
    sagemaker.create_model(
        ModelName=model_name,
        ExecutionRoleArn=role_arn,
        PrimaryContainer={
            'Image': container_image,
            'ModelDataUrl': model_data_url
        }
    )

    # ✅ Delete existing endpoint config if exists
    try:
        sagemaker.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
        logger.info(f"Endpoint config {endpoint_config_name} already exists. Deleting...")
        sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
    except sagemaker.exceptions.ClientError as e:
        if "Could not find endpoint configuration" in str(e):
            pass
        else:
            raise

    # ✅ Create new endpoint config
    logger.info("Creating endpoint config...")
    sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[{
            'VariantName': 'AllTraffic',
            'ModelName': model_name,
            'InitialInstanceCount': 1,
            'InstanceType': instance_type,
            'InitialVariantWeight': 1
        }]
    )

    # ✅ Check if endpoint exists — update or create
    try:
        sagemaker.describe_endpoint(EndpointName=endpoint_name)
        logger.info(f"Endpoint {endpoint_name} already exists. Updating with new config...")
        sagemaker.update_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
    except sagemaker.exceptions.ClientError as e:
        if "Could not find endpoint" in str(e):
            logger.info("Creating new endpoint...")
            sagemaker.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=endpoint_config_name
            )
        else:
            raise

    # ✅ Wait until it's ready
    try:
        logger.info("Waiting for endpoint to be InService...")
        waiter = sagemaker.get_waiter('endpoint_in_service')
        waiter.wait(EndpointName=endpoint_name)
        logger.info(f"Endpoint is deployed and InService: {endpoint_name}")
    except Exception as e:
        logger.error("Endpoint creation/update failed.")
        response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
        logger.error(f"Endpoint status: {response['EndpointStatus']}")
        logger.error(f"📄 Failure reason: {response.get('FailureReason', 'No detailed reason provided')}")
        raise

if __name__ == "__main__":
    deploy_model()
