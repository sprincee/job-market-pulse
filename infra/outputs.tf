output "raw_bucket" {
  description = "Raw bucket name; set as RAW_BUCKET for the Lambda and the backfill"
  value       = module.raw_bucket.id
}

output "ingest_function" {
  description = "Lambda name, for manual invokes: aws lambda invoke --function-name <this>"
  value       = aws_lambda_function.ingest.function_name
}

output "alerts_topic_arn" {
  description = "SNS topic that alarms notify"
  value       = aws_sns_topic.alerts.arn
}
