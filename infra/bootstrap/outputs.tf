output "tfstate_bucket" {
  description = "State bucket name; used in the backend block of infra/"
  value       = aws_s3_bucket.tfstate.bucket
}
