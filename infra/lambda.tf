# Zips build/lambda (made by scripts/build_lambda.ps1). The hash means
# apply only redeploys when the code or deps actually changed.
data "archive_file" "ingest" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda"
  output_path = "${path.module}/../build/lambda.zip"
}

# Created here (not by Lambda on first run) so retention is set; Lambda's
# default is to keep logs forever.
resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/jmp-ingest"
  retention_in_days = 30
}

resource "aws_lambda_function" "ingest" {
  function_name    = "jmp-ingest"
  role             = aws_iam_role.ingest.arn
  runtime          = "python3.13"
  architectures    = ["x86_64"] # matches the manylinux2014_x86_64 wheels
  handler          = "ingest.lambda_handler.handler"
  filename         = data.archive_file.ingest.output_path
  source_code_hash = data.archive_file.ingest.output_base64sha256

  memory_size = 512 # largest boards (Anduril) are held in memory as JSON
  timeout     = 300 # ~60s typical; 5x headroom

  environment {
    variables = {
      RAW_BUCKET = module.raw_bucket.id
    }
  }

  # No vpc_config on purpose: a VPC would need a NAT gateway (~$32/mo) for internet access.

  depends_on = [aws_cloudwatch_log_group.ingest, aws_iam_role_policy.ingest]
}

# The scheduler invokes asynchronously. A failed run means everything failed
# (decision C), so one retry is enough; the default is two.
resource "aws_lambda_function_event_invoke_config" "ingest" {
  function_name                = aws_lambda_function.ingest.function_name
  maximum_retry_attempts       = 1
  maximum_event_age_in_seconds = 3600
}
