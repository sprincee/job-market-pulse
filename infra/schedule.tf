# EventBridge Scheduler, not an EventBridge rule: rules only take UTC, so a
# fixed 2pm ET would drift by an hour at each daylight-saving change.
resource "aws_scheduler_schedule" "ingest_daily" {
  name                         = "jmp-ingest-daily"
  schedule_expression          = "cron(0 14 * * ? *)"
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.ingest.arn
    role_arn = aws_iam_role.scheduler.arn

    # Retries delivering the invoke (e.g. throttling), not failed runs.
    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 3600
    }
  }
}
