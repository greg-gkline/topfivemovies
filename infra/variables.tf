variable "region" {
  description = "Region of the site bucket (and the state bucket)."
  type        = string
  default     = "us-east-2"
}

variable "domain" {
  description = "The apex domain. The site is served at www.<domain>, and <domain> redirects to it."
  type        = string
  default     = "topfivemovies.com"
}

variable "site_bucket" {
  description = "The existing, hand-made bucket that holds the built site. It is imported, not created."
  type        = string
  default     = "topfivemovies"
}

variable "enable_custom_domain" {
  description = <<-EOT
    Serve the site at the real domain. Leave false until the registrar delegates the domain to
    this zone (Phase 7): ACM can only validate the certificate once Route 53 answers for the
    domain. While false, the site is reachable at the distribution's *.cloudfront.net address.
  EOT
  type        = bool
  default     = false
}

variable "hsts_max_age_seconds" {
  description = "Strict-Transport-Security max-age."
  type        = number
  default     = 31536000
}

variable "alert_email" {
  description = <<-EOT
    Where the monthly cost budget emails its alerts. Empty turns the budget off. Keep it out
    of git: set the environment variable TF_VAR_alert_email (README.md). Sensitive, so a plan
    does not print it, and the plan comment on a pull request cannot leak it.
  EOT
  type        = string
  default     = ""
  sensitive   = true
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget, when alert_email is set."
  type        = number
  default     = 10
}
