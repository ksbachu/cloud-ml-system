variable "bucket_name" {
  default = "cloud-ml-lead-models"
}

variable "region" {
  default = "ap-south-1"
}
variable "aws_access_key" {
  description = "AWS access key"
  type        = string
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS secret key"
  type        = string
  sensitive   = true
}
