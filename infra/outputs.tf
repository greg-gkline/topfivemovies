output "name_servers" {
  description = "Set these as the domain's name servers at the registrar (Phase 7)."
  value       = aws_route53_zone.site.name_servers
}

output "distribution_id" {
  description = "CloudFront distribution id, for cache invalidations."
  value       = aws_cloudfront_distribution.site.id
}

output "distribution_domain" {
  description = "The site before the custom domain is on: https://<this>/"
  value       = aws_cloudfront_distribution.site.domain_name
}

output "site_bucket" {
  value = aws_s3_bucket.site.id
}

output "deploy_user" {
  description = "IAM user for the deploy workflow. Create its access key by hand (README.md)."
  value       = aws_iam_user.ci["deploy"].name
}

output "plan_user" {
  description = "IAM user for the terraform-plan workflow. Create its access key by hand (README.md)."
  value       = aws_iam_user.ci["plan"].name
}
