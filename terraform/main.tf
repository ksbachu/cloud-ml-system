terraform {
  backend "s3" {
    bucket = "cloud-ml-tf-state"
    key    = "sagemaker/model-deployment.tfstate"
    region = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region     = var.region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

resource "aws_s3_bucket" "model_bucket" {
  bucket = var.bucket_name

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_iam_role" "sagemaker_execution_role" {
  name               = "cloud-ml-sagemaker-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "sagemaker.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "attach_s3_policy" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "attach_logs_policy" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_iam_role" "lambda_role" {
  name               = "lambda-sagemaker-inference-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_custom" {
  name = "lambda-sagemaker-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = ["sagemaker:InvokeEndpoint"],
        Effect   = "Allow",
        Resource = "*"
      },
      {
        Action   = ["s3:PutObject"],
        Effect   = "Allow",
        Resource = "arn:aws:s3:::${var.bucket_name}/*"
      }
    ]
  })

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_custom_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_custom.arn
}


resource "aws_lambda_function" "inference" {
  function_name         = "inference-handler"
  filename              = "${path.module}/lambda_package.zip"
  source_code_hash      = filebase64sha256("${path.module}/lambda_package.zip")
  handler               = "inference_lambda.lambda_handler"
  runtime               = "python3.10"
  role                  = aws_iam_role.lambda_role.arn
  code_signing_config_arn = null

  environment {
    variables = {
      SAGEMAKER_ENDPOINT_NAME = aws_sagemaker_endpoint.xgboost_endpoint.name
      S3_BUCKET               = aws_s3_bucket.model_bucket.bucket
    }
  }

  tags = {
    project        = var.project
    environment    = var.environment
    managed_by     = "terraform"
    model_version  = var.model_version_suffix
  }
}

resource "aws_apigatewayv2_api" "api" {
  name          = "inference-api"
  protocol_type = "HTTP"

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                = aws_apigatewayv2_api.api.id
  integration_type      = "AWS_PROXY"
  integration_uri       = aws_lambda_function.inference.invoke_arn
  integration_method    = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "predict_route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /predict"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inference.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_sagemaker_model" "xgboost_model" {
  name               = "xgboostmodel-${var.model_version_suffix}"
  execution_role_arn = aws_iam_role.sagemaker_execution_role.arn

  primary_container {
    image          = "683313688378.dkr.ecr.${var.region}.amazonaws.com/sagemaker-xgboost:1.7-1"
    model_data_url = var.model_data_url
  }

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
    version     = var.model_version_suffix
  }
}

resource "aws_sagemaker_endpoint_configuration" "xgboost_endpoint_config" {
  name = "xgboostmodel-config-${var.model_version_suffix}"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.xgboost_model.name
    initial_instance_count = 1
    instance_type          = "ml.t2.medium"
    initial_variant_weight = 1
  }

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
    version     = var.model_version_suffix
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint" "xgboost_endpoint" {
  name                 = "xgboostmodel-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.xgboost_endpoint_config.name

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }

}
