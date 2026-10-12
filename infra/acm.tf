# The certificate is requested only once the domain is delegated to Route 53: ACM validates
# by looking up the DNS records below, so before the cutover it could not finish and would
# time out after three days.
resource "aws_acm_certificate" "site" {
  count    = var.enable_custom_domain ? 1 : 0
  provider = aws.us_east_1

  domain_name               = local.www
  subject_alternative_names = [var.domain]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate_validation" {
  for_each = var.enable_custom_domain ? {
    for option in aws_acm_certificate.site[0].domain_validation_options :
    option.domain_name => option
  } : {}

  zone_id         = aws_route53_zone.site.zone_id
  name            = each.value.resource_record_name
  type            = each.value.resource_record_type
  records         = [each.value.resource_record_value]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "site" {
  count    = var.enable_custom_domain ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]
}
