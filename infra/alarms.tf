# Alarm notifications go to this topic, then to email.
# No SSE on the topic: CloudWatch can't publish to a topic encrypted with the
# AWS-managed aws/sns key, and a customer-managed KMS key costs $1/month.
resource "aws_sns_topic" "alerts" {
  name = "jmp-alerts"
}

# AWS emails a confirmation link; the subscription stays "pending" until clicked.
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
