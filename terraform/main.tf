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

