output "raw_bucket" {
  description = "Raw bucket name; set as RAW_BUCKET for the Lambda and the backfill"
  value       = module.raw_bucket.id
}

output "ingest_function" {
  description = "Lambda name, for manual invokes: aws lambda invoke --function-name <this>"
  value       = aws_lambda_function.ingest.function_name
}

output "site_url" {
  description = "The public site, until the custom domain is added"
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
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
