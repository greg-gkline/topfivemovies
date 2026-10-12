#!/usr/bin/env bash
# Requires the `validate` check on `main`. The prose checks (spelling, grammar-review) are advisory. Needs the GitHub CLI, signed in
# as a repo admin. Not run by CI: it changes the repo's settings, so run it by hand once the
# workflows have reported at least once, and add the Terraform checks (Phase 5) to CHECKS.
#
# Usage: scripts/github/branch-protection.sh [owner/repo]
set -euo pipefail

REPO=${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}
CHECKS=(validate)

contexts=$(printf '%s\n' "${CHECKS[@]}" | jq -R . | jq -s -c .)
echo "Requiring ${CHECKS[*]} on main in $REPO"
gh api -X PUT "repos/$REPO/branches/main/protection" --input - <<JSON
{
  "required_status_checks": { "strict": true, "contexts": $contexts },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
