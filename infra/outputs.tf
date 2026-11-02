output "raw_bucket" {
  description = "Raw bucket name; set as RAW_BUCKET for the Lambda and the backfill"
  value       = module.raw_bucket.id
}

output "ingest_function" {
  description = "Lambda name, for manual invokes: aws lambda invoke --function-name <this>"
  value       = aws_lambda_function.ingest.function_name
}

output "certificate_validation_records" {
  description = "CNAME records to add at Namecheap so ACM can issue the certificate"
  value = {
    for option in aws_acm_certificate.site.domain_validation_options : option.domain_name => {
      type  = option.resource_record_type
      name  = option.resource_record_name
      value = option.resource_record_value
    }
  }
}

output "cloudfront_domain_name" {
  description = "Where the domain's DNS records point"
  value       = aws_cloudfront_distribution.site.domain_name
}

output "cloudfront_distribution_id" {
  description = "Set as DISTRIBUTION_ID in .github/workflows/daily-build.yml"
  value       = aws_cloudfront_distribution.site.id
}

output "github_role_arn" {
  description = "Role assumed by .github/workflows/daily-build.yml"
  value       = aws_iam_role.github_daily_build.arn
}

output "alerts_topic_arn" {
  description = "SNS topic that alarms notify"
  value       = aws_sns_topic.alerts.arn
}
