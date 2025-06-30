variable "project" {
  default = "cloud-ml-lead-scoring"
}

variable "environment" {
  default = "dev"
}

variable "model_version_suffix" {
  description = "Version or timestamp suffix for model and endpoint naming"
  type        = string
}

variable "bucket_name" {
  default = "cloud-ml-lead-scoring-models"
}

variable "region" {
  default = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS access key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_secret_key" {
  description = "AWS secret key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sagemaker_endpoint" {
  description = "Name of the deployed SageMaker endpoint"
  default     = "xgboostmodel-endpoint3"
}

variable "model_data_url" {
  description = "The S3 path to the model artifact"
  type        = string
}
