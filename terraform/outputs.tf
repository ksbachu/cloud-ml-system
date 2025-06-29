output "s3_bucket_name" {
  description = "S3 bucket name for storing model artifacts"
  value       = aws_s3_bucket.model_bucket.bucket
}

output "sagemaker_execution_role_arn" {
  description = "IAM role ARN to be assumed by SageMaker"
  value       = aws_iam_role.sagemaker_execution_role.arn
}

output "region" {
  description = "AWS region"
  value       = var.region
}
