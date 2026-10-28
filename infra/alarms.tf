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

# No ok_actions on the two failure alarms: they'd return to OK an hour later
# just because no new data arrived, which reads as "fixed" when nothing changed.

resource "aws_cloudwatch_metric_alarm" "ingest_errors" {
  alarm_name        = "jmp-ingest-errors"
  alarm_description = "Ingest Lambda run failed: every company failed, the manifest couldn't be written, or a bug. Check /aws/lambda/jmp-ingest logs."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions = {
    FunctionName = aws_lambda_function.ingest.function_name
  }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "companies_failed" {
  alarm_name        = "jmp-companies-failed"
  alarm_description = "At least one company's board failed to fetch or save. See runs/date=<today>/manifest.json in the raw bucket."

  namespace           = "JobMarketPulse"
  metric_name         = "CompaniesFailed"
  statistic           = "Maximum"
  period              = 3600
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# Catches the silent failure: nothing ran, so nothing errored. 26 hourly
# periods with no successful run; missing data counts as breaching.
resource "aws_cloudwatch_metric_alarm" "ingest_stale" {
  alarm_name        = "jmp-ingest-stale"
  alarm_description = "No successful ingest run in 26 hours. Check the jmp-ingest-daily schedule and the Lambda."

  namespace           = "JobMarketPulse"
  metric_name         = "RunSucceeded"
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 26
  datapoints_to_alarm = 26
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn] # OK here genuinely means a run succeeded
}
