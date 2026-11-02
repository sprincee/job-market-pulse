# HTTPS certificate for the custom domain. Free with ACM, and renewed automatically
# while its validation records stay in DNS. CloudFront only accepts certificates
# from us-east-1, which is this config's region.
#
# DNS lives at Namecheap, so the validation records are added there by hand.
resource "aws_acm_certificate" "site" {
  domain_name               = "worthlearning.dev"
  subject_alternative_names = ["www.worthlearning.dev"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}
