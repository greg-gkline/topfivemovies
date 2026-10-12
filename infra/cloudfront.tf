locals {
  www     = "www.${var.domain}"
  aliases = var.enable_custom_domain ? [local.www, var.domain] : []

  # Everything the site loads comes from itself. There are no inline scripts or styles; the
  # stylesheet has two data: images, hence img-src data:.
  content_security_policy = join("; ", [
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
    "upgrade-insecure-requests",
  ])
}

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${var.site_bucket}-oac"
  description                       = "Signed requests from CloudFront to the private site bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "viewer_request" {
  name    = "${var.site_bucket}-viewer-request"
  runtime = "cloudfront-js-2.0"
  comment = "Redirect ${var.domain} to ${local.www}; serve index.html for directory paths"
  publish = true
  code = templatefile("${path.module}/functions/viewer-request.js.tftpl", {
    apex = var.domain
    www  = local.www
  })
}

resource "aws_cloudfront_response_headers_policy" "site" {
  #checkov:skip=CKV_AWS_259:The check wants the preload flag, which is a promise to the browsers' preload list; HSTS itself is on with a one-year max-age
  name    = "${var.site_bucket}-security-headers"
  comment = "HSTS, CSP and the other security headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = var.hsts_max_age_seconds
      include_subdomains         = true
      preload                    = false
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    content_security_policy {
      content_security_policy = local.content_security_policy
      override                = true
    }
  }

  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "camera=(), microphone=(), geolocation=(), payment=()"
      override = true
    }
  }
}

resource "aws_cloudfront_distribution" "site" {
  #checkov:skip=CKV_AWS_68:A WAF would cost more per month than the whole site, and there is nothing dynamic to attack
  #checkov:skip=CKV_AWS_86:Access logs need a second bucket; add them if traffic analysis is ever wanted
  #checkov:skip=CKV_AWS_310:There is one origin, so no origin failover
  #checkov:skip=CKV_AWS_374:The site is public worldwide, with no geo restriction
  #checkov:skip=CKV2_AWS_47:There is no WAF to attach a Log4j rule to
  #checkov:skip=CKV_AWS_174:Until the domain is delegated the default certificate is used, which allows older TLS; the custom certificate requires TLS 1.2
  #checkov:skip=CKV2_AWS_42:The custom certificate is used once enable_custom_domain is true
  comment             = "${local.www} (static site)"
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2and3"
  price_class         = "PriceClass_100" # North America and Europe edges: the cheapest
  default_root_object = "index.html"
  aliases             = local.aliases

  origin {
    origin_id                = "site-bucket"
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id           = "site-bucket"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.site.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.viewer_request.arn
    }
  }

  # A missing key comes back from a private bucket as 403, not 404, so both get the 404 page.
  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 60
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 60
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Until the domain is delegated, the distribution uses CloudFront's own certificate and
  # its *.cloudfront.net name.
  dynamic "viewer_certificate" {
    for_each = var.enable_custom_domain ? [] : [1]
    content {
      cloudfront_default_certificate = true
    }
  }

  dynamic "viewer_certificate" {
    for_each = var.enable_custom_domain ? [1] : []
    content {
      acm_certificate_arn      = aws_acm_certificate_validation.site[0].certificate_arn
      ssl_support_method       = "sni-only"
      minimum_protocol_version = "TLSv1.2_2021"
    }
  }
}
