# Optional: a cost budget and a CloudFront error-rate alarm, both off unless alert_email is set.
locals {
  # Only whether there is an address, not the address itself, so it is safe to use in count.
  alerts_enabled = nonsensitive(var.alert_email != "")
}

resource "aws_budgets_budget" "monthly" {
  count = local.alerts_enabled ? 1 : 0

  name         = "topfivemovies-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:Project$topfivemovies"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}

# CloudFront publishes its metrics in us-east-1 only.
resource "aws_sns_topic" "alerts" {
  count    = local.alerts_enabled ? 1 : 0
  provider = aws.us_east_1

  name              = "topfivemovies-alerts"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count    = local.alerts_enabled ? 1 : 0
  provider = aws.us_east_1

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email # the address has to confirm the subscription by email
}

resource "aws_cloudwatch_metric_alarm" "error_rate" {
  count    = local.alerts_enabled ? 1 : 0
  provider = aws.us_east_1

  alarm_name          = "topfivemovies-5xx-error-rate"
  alarm_description   = "More than 5% of requests to the site failed with a 5xx error"
  namespace           = "AWS/CloudFront"
  metric_name         = "5xxErrorRate"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    DistributionId = aws_cloudfront_distribution.site.id
    Region         = "Global"
  }
}
