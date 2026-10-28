output "raw_bucket" {
  description = "Raw bucket name; set as RAW_BUCKET for the Lambda and the backfill"
  value       = module.raw_bucket.id
}

output "alerts_topic_arn" {
  description = "SNS topic that alarms notify"
  value       = aws_sns_topic.alerts.arn
}
