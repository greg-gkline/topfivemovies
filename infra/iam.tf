# GitHub Actions signs in with access keys, since the account does not support OIDC. Two
# IAM users, each in a group that carries its permissions:
#   deploy  writes the bucket and invalidates the cache (the deploy workflow, Phase 6)
#   plan    reads, never changes (the terraform-plan workflow on pull requests)
# Terraform creates the users and groups but NOT their access keys: a key created here would
# have its secret stored in the state file. Create them by hand and put them in GitHub
# secrets (README.md). Rotate them from time to time.

locals {
  state_bucket = "infrastructure-832474135782-us-east-2-an"
  state_prefix = "topfivemovies/terraform"
  ci_users     = toset(["deploy", "plan"])
}

resource "aws_iam_group" "ci" {
  for_each = local.ci_users

  name = "topfivemovies-${each.key}"
}

resource "aws_iam_user" "ci" {
  #checkov:skip=CKV_AWS_273:The account does not support OIDC or SSO, so CI uses access keys; the permissions are the narrowest the jobs need
  for_each = local.ci_users

  name = "topfivemovies-${each.key}"
}

resource "aws_iam_group_membership" "ci" {
  for_each = local.ci_users

  name  = "topfivemovies-${each.key}"
  group = aws_iam_group.ci[each.key].name
  users = [aws_iam_user.ci[each.key].name]
}

data "aws_iam_policy_document" "deploy" {
  statement {
    sid       = "ListSiteBucket"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.site.arn]
  }

  statement {
    sid       = "WriteSiteObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]
  }

  statement {
    sid       = "InvalidateCache"
    actions   = ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"]
    resources = [aws_cloudfront_distribution.site.arn]
  }
}

resource "aws_iam_group_policy" "deploy" {
  name   = "deploy"
  group  = aws_iam_group.ci["deploy"].name
  policy = data.aws_iam_policy_document.deploy.json
}

# Read access to what the configuration describes, and no object data: a pull request can
# change the workflow that uses these keys, so they must not read the buckets' contents.
data "aws_iam_policy_document" "plan" {
  #checkov:skip=CKV_AWS_356:Describe, Get and List calls do not support resource-level scoping; the user is read-only and cannot read object data
  statement {
    sid = "ReadConfiguredServices"
    actions = [
      "s3:GetBucket*",
      "s3:GetEncryptionConfiguration",
      "s3:GetLifecycleConfiguration",
      "s3:GetAccelerateConfiguration",
      "s3:GetReplicationConfiguration",
      "s3:ListBucket",
      "cloudfront:Get*",
      "cloudfront:List*",
      "route53:Get*",
      "route53:List*",
      "acm:Describe*",
      "acm:Get*",
      "acm:List*",
      "iam:Get*",
      "iam:List*",
      "budgets:ViewBudget",
      "cloudwatch:Describe*",
      "cloudwatch:List*",
      "sns:Get*",
      "sns:List*",
    ]
    resources = ["*"]
  }

  # Terraform reads the state. -lock=false in the workflow, so it never writes the lockfile.
  statement {
    sid       = "ReadState"
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::${local.state_bucket}/${local.state_prefix}/*"]
  }
}

resource "aws_iam_group_policy" "plan" {
  name   = "plan"
  group  = aws_iam_group.ci["plan"].name
  policy = data.aws_iam_policy_document.plan.json
}
