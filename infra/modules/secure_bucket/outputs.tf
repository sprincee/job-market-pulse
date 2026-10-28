output "id" {
  description = "Bucket name"
  value       = aws_s3_bucket.this.id
}

output "arn" {
  description = "Bucket ARN, for IAM policies"
  value       = aws_s3_bucket.this.arn
}
