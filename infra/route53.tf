# The zone exists from the first apply so its name servers are known before the cutover.
# Until the registrar delegates to it (Phase 7), nothing on the internet asks it anything.
resource "aws_route53_zone" "site" {
  #checkov:skip=CKV2_AWS_38:DNSSEC would need a DS record at the registrar; a separate decision, off for now
  #checkov:skip=CKV2_AWS_39:Query logging needs a CloudWatch log group in us-east-1 and gains nothing for a public static site
  name    = var.domain
  comment = "${var.domain}, delegated from the registrar"

  lifecycle {
    prevent_destroy = true # a new zone would get new name servers
  }
}

locals {
  alias_names = var.enable_custom_domain ? { www = local.www, apex = var.domain } : {}
  alias_types = var.enable_custom_domain ? toset(["A", "AAAA"]) : toset([])
  alias_records = {
    for pair in setproduct(keys(local.alias_names), local.alias_types) :
    "${pair[0]}-${pair[1]}" => { name = local.alias_names[pair[0]], type = pair[1] }
  }
}

resource "aws_route53_record" "site" {
  for_each = local.alias_records

  zone_id = aws_route53_zone.site.zone_id
  name    = each.value.name
  type    = each.value.type

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}
