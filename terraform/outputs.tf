output "sagemaker_execution_role_arn" {
  value = aws_iam_role.sagemaker_execution_role.arn
}

output "bucket_name" {
  value = aws_s3_bucket.model_bucket.bucket
}
