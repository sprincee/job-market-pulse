# Raw API responses, written only by the ingest Lambda.
module "raw_bucket" {
  source = "./modules/secure_bucket"

  name       = "jmp-raw-${local.account_id}"
  versioning = true
}

# The warehouse file and Parquet tables. Old versions are kept briefly: the file
# is replaced daily, and it can always be rebuilt from raw.
module "curated_bucket" {
  source = "./modules/secure_bucket"

  name                               = "jmp-curated-${local.account_id}"
  versioning                         = true
  noncurrent_version_expiration_days = 7
}

# The static site. Private: only this CloudFront distribution can read it.
module "site_bucket" {
  source = "./modules/secure_bucket"

  name = "jmp-site-${local.account_id}"

  extra_policy_statements = [{
    Sid       = "AllowCloudFrontRead"
    Effect    = "Allow"
    Principal = { Service = "cloudfront.amazonaws.com" }
    Action    = "s3:GetObject"
    Resource  = "arn:aws:s3:::jmp-site-${local.account_id}/*" # a module can't reference its own output
    Condition = {
      StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.site.arn }
    }
  }]
}
