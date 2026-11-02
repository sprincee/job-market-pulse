# Public HTTPS front for the private site bucket.

# Lets CloudFront sign its requests to S3, which the bucket policy then allows.
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "jmp-site"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# S3 has no folders, so /roles/swe/ has to be rewritten to /roles/swe/index.html.
resource "aws_cloudfront_function" "index_rewrite" {
  name    = "jmp-index-rewrite"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-JS
    function handler(event) {
      var request = event.request;
      if (request.uri.endsWith('/')) {
        request.uri += 'index.html';
      } else if (!request.uri.includes('.')) {
        request.uri += '/index.html';
      }
      return request;
    }
  JS
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  comment             = "Job Market Pulse"
  default_root_object = "index.html"
  is_ipv6_enabled     = true
  price_class         = "PriceClass_100" # North America and Europe edges only; the cheapest class

  origin {
    origin_id                = "site"
    domain_name              = module.site_bucket.regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id       = "site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # AWS managed: CachingOptimized

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.index_rewrite.arn
    }
  }

  # A private bucket answers 403 for a missing key, which should read as a 404.
  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 60
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # The default *.cloudfront.net certificate; replaced when the custom domain is added.
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
