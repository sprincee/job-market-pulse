output "id" {
  description = "Bucket name"
  value       = aws_s3_bucket.this.id
}

output "regional_domain_name" {
  description = "Bucket hostname, for CloudFront origins"
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "arn" {
  description = "Bucket ARN, for IAM policies"
  value       = aws_s3_bucket.this.arn
}
