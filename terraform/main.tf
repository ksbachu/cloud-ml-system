terraform {
  backend "s3" {
    bucket = "cloud-ml-tf-state"        
    key    = "sagemaker/model-deployment.tfstate"
    region = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region                  = var.region
  access_key              = var.aws_access_key
  secret_key              = var.aws_secret_key
}


resource "aws_s3_bucket" "model_bucket" {
  bucket = "cloud-ml-lead-scoring-models"
}

resource "aws_iam_role" "sagemaker_execution_role" {
  name = "cloud-ml-sagemaker-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "sagemaker.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_s3_policy" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "attach_logs_policy" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda-sagemaker-inference-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# Attach basic Lambda permissions
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom IAM Policy: S3 + SageMaker Invoke
resource "aws_iam_policy" "lambda_custom" {
  name = "lambda-sagemaker-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action: ["sagemaker:InvokeEndpoint"],
        Effect: "Allow",
        Resource: "*"
      },
      {
        Action: ["s3:PutObject"],
        Effect: "Allow",
        Resource: "arn:aws:s3:::${var.bucket_name}/*"
      }
    ]
  })
}


# Attach custom policy
resource "aws_iam_role_policy_attachment" "lambda_custom_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_custom.arn
}

# Lambda function
resource "aws_lambda_function" "inference" {
  function_name = "inference-handler"
  filename         = "${path.module}/lambda_package.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_package.zip")
  handler          = "inference_lambda.lambda_handler"
  runtime          = "python3.10"
  role             = aws_iam_role.lambda_role.arn
  code_signing_config_arn = null
  environment {
    variables = {
      SAGEMAKER_ENDPOINT_NAME = var.sagemaker_endpoint
      S3_BUCKET               = var.bucket_name
    }
  }
}


# API Gateway (HTTP API)
resource "aws_apigatewayv2_api" "api" {
  name          = "inference-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.inference.invoke_arn
  integration_method = "POST"
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
}

resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inference.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}