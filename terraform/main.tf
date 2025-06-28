terraform {
  backend "s3" {
    bucket = "cloud-ml-terraform-state"        
    key    = "sagemaker/model-deployment.tfstate"
    region = "ap-south-1"
    encrypt = true
  }
}

provider "aws" {
  region                  = var.region
  access_key              = var.aws_access_key
  secret_key              = var.aws_secret_key
}


resource "aws_s3_bucket" "model_bucket" {
  bucket = "cloud-ml-lead-models"
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
