# Non-secret settings for this deployment. Flip enable_custom_domain at the DNS cutover
# (Phase 7); see README.md. The alert email is not here: it comes from the environment
# variable TF_VAR_alert_email, so it stays out of git.
enable_custom_domain = false
