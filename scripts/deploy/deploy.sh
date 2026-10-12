#!/usr/bin/env bash
# Publish public/ to the site bucket, invalidate CloudFront and smoke-test the result.
# Run by .github/workflows/deploy.yml; it can also be run by hand with AWS credentials
# that can write the bucket (see infra/README.md).
#
# Environment:
#   SITE_BUCKET      S3 bucket name (required)
#   DISTRIBUTION_ID  CloudFront distribution id (required)
#   SITE_URL         address to smoke-test, no trailing slash (required)
#   PUBLIC_DIR       built site, default public
#   INVALIDATE_ALL   "true" to invalidate /* instead of the changed paths (the workflow
#                    sets it when templates, styles or the site configuration changed)
#   SKIP_SMOKE       "true" to skip the smoke test
set -euo pipefail

: "${SITE_BUCKET:?}" "${DISTRIBUTION_ID:?}" "${SITE_URL:?}"
dir=${PUBLIC_DIR:-public}
dest="s3://${SITE_BUCKET}"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

[ -f "$dir/index.html" ] || { echo "$dir/index.html is missing: build the site first." >&2; exit 1; }

# Caching by kind of file:
#   fingerprinted (a 64-hex digest in the name, or Hugo's `_hu_<hex>` image suffix): the
#     name changes with the content, so cache for a year
#   HTML, feeds, sitemap, robots.txt: five minutes (and invalidated on change)
#   anything else (original pictures, favicon): a day
hashed_re='(\.[0-9a-f]{64}\.(css|js)$)|(_hu_[0-9a-f]+\.(webp|jpg|jpeg|png|gif)$)'
cache_for() {
  if [[ $1 =~ $hashed_re ]]; then echo "public, max-age=31536000, immutable"
  else
    case $1 in
      *.html|*.xml|*.txt) echo "public, max-age=300" ;;
      *) echo "public, max-age=86400" ;;
    esac
  fi
}

(cd "$dir" && find . -type f | sed 's|^\./||' | LC_ALL=C sort) > "$work/local.txt"

# What the bucket holds now: key and ETag. The ETag of a single-part upload is the MD5 of
# the content, so an unchanged file is skipped and a changed one is known by name.
aws s3api list-objects-v2 --bucket "$SITE_BUCKET" \
  --query 'Contents[].[Key,ETag]' --output text | tr -d '"' | grep -v '^None' | LC_ALL=C sort > "$work/remote.txt" || true
: > "$work/changed.txt"
while IFS= read -r key; do
  sum=$(md5sum "$dir/$key" | cut -d' ' -f1)
  if ! grep -qxF -- "$key"$'\t'"$sum" "$work/remote.txt"; then echo "$key" >> "$work/changed.txt"; fi
done < "$work/local.txt"
cut -f1 "$work/remote.txt" | LC_ALL=C sort | comm -13 "$work/local.txt" - > "$work/removed.txt"

upload() { # <key>
  # The content type comes from the extension (aws s3 cp guesses it), which suits the build.
  aws s3 cp "$dir/$1" "$dest/$1" --only-show-errors --cache-control "$(cache_for "$1")"
}

echo "$(wc -l < "$work/changed.txt") changed, $(wc -l < "$work/removed.txt") removed, $(wc -l < "$work/local.txt") files in the build"

# Fingerprinted files first, then the rest, so a page never names an asset that is not
# there yet. At most 16 uploads run at once.
for pass in hashed other; do
  while IFS= read -r key; do
    if [[ $key =~ $hashed_re ]]; then [ "$pass" = hashed ] || continue; else [ "$pass" = other ] || continue; fi
    upload "$key" &
    while [ "$(jobs -rp | wc -l)" -ge 16 ]; do wait -n; done
  done < "$work/changed.txt"
  wait
done

# Delete what the build no longer has (the equivalent of `aws s3 sync --delete`). Done
# after the uploads, so the site is never missing a page that is still linked.
while IFS= read -r key; do
  [ -n "$key" ] || continue
  aws s3 rm "$dest/$key" --only-show-errors
done < "$work/removed.txt"

# Invalidate. Fingerprinted files never need it (a changed file has a new name). Everything
# else that changed or was removed does, as does the directory address of the home page.
if [ "${INVALIDATE_ALL:-false}" = "true" ] || [ "$(cat "$work/changed.txt" "$work/removed.txt" | grep -Evc "$hashed_re")" -gt 500 ]; then
  paths=("/*")
else
  mapfile -t paths < <(cat "$work/changed.txt" "$work/removed.txt" | grep -Ev "$hashed_re" | grep -v '^$' | sed 's|^|/|')
  [ "${#paths[@]}" -gt 0 ] && paths+=("/")
fi
if [ "${#paths[@]}" -gt 0 ]; then
  echo "Invalidating ${#paths[@]} path(s)"
  id=$(aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" \
    --paths "${paths[@]}" --query Invalidation.Id --output text)
  aws cloudfront wait invalidation-completed --distribution-id "$DISTRIBUTION_ID" --id "$id"
  echo "Invalidation $id completed"
else
  echo "Nothing to invalidate"
fi

if [ "${SKIP_SMOKE:-false}" = "true" ]; then
  echo "Smoke test skipped"
  exit 0
fi
exec "$(dirname "$0")/smoke.sh" "$SITE_URL" "$dir"
