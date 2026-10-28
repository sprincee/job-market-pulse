# Two roles, each limited to one job.

# --- Ingest Lambda: write raw files, write its own logs, send its metrics ---

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest" {
  name               = "jmp-ingest-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingest" {
  # Write-only, two prefixes. No read/list/delete, so a bug can't wipe history.
  statement {
    sid     = "WriteRawAndManifests"
    actions = ["s3:PutObject"]
    resources = [
      "${module.raw_bucket.arn}/raw/*",
      "${module.raw_bucket.arn}/runs/*",
    ]
  }

  # Only its own log group (created by Terraform, so no CreateLogGroup).
  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.ingest.arn}:*"]
  }

  # PutMetricData has no resource ARNs; scope it by namespace instead.
  statement {
    sid       = "PublishOwnMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["JobMarketPulse"]
    }
  }
}

resource "aws_iam_role_policy" "ingest" {
  name   = "ingest"
  role   = aws_iam_role.ingest.id
  policy = data.aws_iam_policy_document.ingest.json
}

# --- Scheduler: invoke the ingest Lambda, nothing else ---

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    # Only schedules in this account may use the role (confused-deputy guard).
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "jmp-ingest-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.ingest.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "invoke-ingest"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}
