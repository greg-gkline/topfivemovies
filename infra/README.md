# Infrastructure (Phase 5)

Terraform for the static site: a private S3 bucket behind CloudFront, DNS in Route 53, and
the IAM users GitHub Actions uses to plan and deploy. One environment. To try a change, use a
codespace and plan or apply from there.

```
                     CloudFront ── Origin Access Control ──> S3 bucket "topfivemovies" (private)
 www.topfivemovies.com ──┘  │
 topfivemovies.com ─────────┘  a function redirects the bare domain to www and serves index.html
 Route 53 zone, ACM certificate in us-east-1, security headers (HSTS, CSP, ...), custom 404
```

| File | What |
|---|---|
| `versions.tf` | Terraform and provider versions, and the S3 backend |
| `s3.tf` | The site bucket (imported), public access block, encryption, bucket policy (no versioning or lifecycle rules, on purpose) |
| `cloudfront.tf` | The distribution, origin access control, security headers, the viewer-request function |
| `functions/viewer-request.js.tftpl` | The CloudFront Function: apex redirect and `index.html` |
| `route53.tf`, `acm.tf` | The zone, alias records, and the certificate with its DNS validation |
| `iam.tf` | Two IAM users with their permissions attached directly (the account has no IAM groups): `deploy` (bucket sync and cache invalidation) and `plan` (read-only) |
| `terraform-operator-policy.json` | The permissions whoever runs `terraform apply` needs (see below) |
| `monitoring.tf` | Optional monthly cost budget, off unless `alert_email` is set (see below) |

## State

The state bucket, `infrastructure-832474135782-us-east-2-an`, was made by hand and is not in
this configuration. The state is `topfivemovies/terraform/terraform.tfstate` in it, with
locking by a lockfile beside it (`use_lockfile`), so there is no DynamoDB table. The AWS
provider is pinned by `.terraform.lock.hcl`.

## Who can run Terraform

Terraform is applied by hand, by you, never from CI. The account does not support OIDC, so
there is nothing for CI to assume: CI only plans, with a read-only access key (below). What
you need in AWS to apply:

1. **An IAM identity with access keys** for the person running Terraform (you), in a
   devcontainer or codespace. If you already have an admin user in the account, that works
   and you can skip to the next step. Otherwise create a user, for example `terraform-admin`,
   and give it the permissions in `terraform-operator-policy.json`. It covers the state
   bucket's `topfivemovies/terraform/` prefix, the `topfivemovies` bucket, CloudFront,
   Route 53, ACM, the `topfivemovies-*` IAM users, and the optional budget. It was written from what the configuration uses and has not been run against AWS,
   so if an apply stops with `AccessDenied`, add the action it names:

       aws iam create-policy --policy-name topfivemovies-terraform \
         --policy-document file://terraform-operator-policy.json
       aws iam create-user --user-name terraform-admin
       aws iam attach-user-policy --user-name terraform-admin \
         --policy-arn arn:aws:iam::832474135782:policy/topfivemovies-terraform
       aws iam create-access-key --user-name terraform-admin

   IAM does not update a policy when the file changes. After this file changes, publish the
   new version as an identity that can manage IAM (not `terraform-admin` itself). A policy
   keeps five versions at most, so delete an old one first if the command reports a limit:

       aws iam create-policy-version \
         --policy-arn arn:aws:iam::832474135782:policy/topfivemovies-terraform \
         --policy-document file://terraform-operator-policy.json --set-as-default

2. **The keys where Terraform can find them.** In a codespace, add them as user secrets
   named `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. In the devcontainer, run
   `aws configure`. Check with `aws sts get-caller-identity`.

3. **Nothing else.** The state bucket and the `topfivemovies` bucket already exist, and
   Terraform creates everything else, including the two CI users.

## Applying

The site bucket was made by hand, and the first apply adopted it into the state with an `import`
block, since removed. Both buckets are in `us-east-2` (the `region` variable).

    cd infra
    terraform init
    terraform plan                 # read it before applying
    terraform apply

Terraform creates the CI users but not their access keys, because a key created by Terraform
would have its secret stored in the state file. Create them by hand and hand them to GitHub
as GitHub secrets (the secret never touches your disk). The plan keys are repository secrets,
which the plan workflow reads on pull requests. The deploy keys go in the `AWS 832474135782`
environment, which is limited to `main`, so only a run on `main` can read them:

    aws iam create-access-key --user-name topfivemovies-plan   --query AccessKey --output json \
      | jq -r '.AccessKeyId, .SecretAccessKey' \
      | { read -r id; read -r secret; \
          gh secret set AWS_PLAN_ACCESS_KEY_ID --body "$id"; \
          gh secret set AWS_PLAN_SECRET_ACCESS_KEY --body "$secret"; }
    aws iam create-access-key --user-name topfivemovies-deploy --query AccessKey --output json \
      | jq -r '.AccessKeyId, .SecretAccessKey' \
      | { read -r id; read -r secret; \
          gh secret set AWS_DEPLOY_ACCESS_KEY_ID --env "AWS 832474135782" --body "$id"; \
          gh secret set AWS_DEPLOY_SECRET_ACCESS_KEY --env "AWS 832474135782" --body "$secret"; }

Until the `AWS_PLAN_*` secrets exist, the `terraform-plan` workflow does nothing. The deploy
secrets are for the deploy workflow (Phase 6), which declares `environment: "AWS 832474135782"`: a job
can read an environment's secrets only if it declares the environment. The plan keys can be read by any workflow run in the repository, including a pull request's, so
that user is read-only on purpose. Both users can do only what `iam.tf` gives
their user policy: the plan user reads configuration and no object data, and the deploy user
writes the site bucket and invalidates the cache, so a leaked key cannot change the
infrastructure. Rotate them now and then with `aws iam create-access-key`, update the
secret, then `aws iam delete-access-key` for the old one.

After that, a change to `infra/` goes through a pull request: the `terraform` job in
`validate.yml` runs fmt, validate, tflint and checkov, `terraform-plan` comments the plan, and
you apply it after the merge.

## The alert email

`alert_email` turns on the monthly cost budget and is where it emails. There is no CloudFront
error alarm: it would need an SNS topic, and this account's organization policy denies SNS. It is kept out of git: it is not in `terraform.tfvars`, and the variable is marked
sensitive, so a plan (including the one the workflow comments on a pull request) shows it as
`(sensitive value)`. Terraform reads it from the environment:

- **Codespace:** add a user secret named `TF_VAR_alert_email`. Codespaces secrets become
  environment variables, so every `terraform` command there sees it.
- **Devcontainer:** `export TF_VAR_alert_email=you@example.com` in your shell, not in a file
  that is committed.
- **The plan workflow:** `gh secret set ALERT_EMAIL` (a repository secret, since the plan job
  reads it). To be sure it is exactly the
  address you applied with, copy it from your own environment instead of typing it again:
  `printf %s "$TF_VAR_alert_email" | gh secret set ALERT_EMAIL`. If the plan shows the budget's
  notifications changing, the two values differ. Set it the same as above, or the plan
  will show the alerts as removed.

Use the same address everywhere. It does end up in the Terraform state (in the private state
bucket) and in AWS, where the budget stores it.

## Before the cutover

`enable_custom_domain` is `false`. The distribution uses CloudFront's own certificate and is
reachable at `https://<distribution_domain>/` (see `terraform output distribution_domain`),
which is where the site is checked before the domain moves. The Route 53 zone exists but
answers for nothing until the registrar delegates to it. The certificate and the alias
records are not created yet, because ACM can only validate a certificate once the domain's DNS
is served from Route 53.

## The cutover (Phase 7)

1. Check the site on the `*.cloudfront.net` address.
2. At the registrar, set the domain's name servers to `terraform output name_servers`. The
   site is down from here until step 4, which is acceptable: it has been offline for years.
3. Wait until `dig NS topfivemovies.com` answers with the Route 53 servers.
4. Set `enable_custom_domain = true` in `terraform.tfvars` and apply. Terraform requests the
   certificate, creates its validation records, waits for ACM, and then attaches the domain to
   the distribution. Expect 10 to 20 minutes.
5. To roll back, set the registrar's name servers back.

## The security headers

`cloudfront.tf` sends a strict Content-Security-Policy: scripts and styles only from the site
itself, images from the site and `data:` (two icons in the stylesheet are data URIs), nothing
else. The built site has no inline scripts or styles and loads nothing from other hosts. If a
template ever needs more, widen the policy there on purpose.
