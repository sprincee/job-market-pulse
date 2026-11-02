# Lets GitHub Actions use AWS with short-lived credentials, so no keys are stored.

# One per AWS account. Other projects in this account can reuse it, but it's managed here.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Only this repo's master branch: forks and pull requests can't assume the role.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:sprincee/job-market-pulse:ref:refs/heads/master"]
    }
  }
}

resource "aws_iam_role" "github_daily_build" {
  name               = "jmp-github-daily-build"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

data "aws_iam_policy_document" "github_daily_build" {
  # Read-only on raw: the build can't change collected data.
  statement {
    sid       = "ReadRaw"
    actions   = ["s3:GetObject"]
    resources = ["${module.raw_bucket.arn}/raw/*"]
  }
  statement {
    sid       = "ListRaw"
    actions   = ["s3:ListBucket"]
    resources = [module.raw_bucket.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["raw/*"]
    }
  }

  statement {
    sid       = "ReadWriteCurated"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${module.curated_bucket.arn}/*"]
  }
  statement {
    sid       = "ListCurated"
    actions   = ["s3:ListBucket"]
    resources = [module.curated_bucket.arn]
  }

  # s3 sync --delete needs to list, write and remove.
  statement {
    sid       = "WriteSite"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${module.site_bucket.arn}/*"]
  }
  statement {
    sid       = "ListSite"
    actions   = ["s3:ListBucket"]
    resources = [module.site_bucket.arn]
  }

  statement {
    sid       = "RefreshCdn"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [aws_cloudfront_distribution.site.arn]
  }
}

resource "aws_iam_role_policy" "github_daily_build" {
  name   = "daily-build"
  role   = aws_iam_role.github_daily_build.id
  policy = data.aws_iam_policy_document.github_daily_build.json
}
