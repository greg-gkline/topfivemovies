#!/usr/bin/env bash
# Smoke test a deployed site: <site-url> [<built-dir>]
# Checks the home page, a page of each kind, the feed, the 404 page and the fingerprinted
# assets the home page names, and that the security headers are on.
set -euo pipefail

url=${1:?usage: smoke.sh <site-url> [<built-dir>]}
url=${url%/}
# A bare host would be fetched over http, which CloudFront answers with a 301 to https.
case $url in http://* | https://*) ;; *) url=https://$url ;; esac
dir=${2:-public}
fail=0

check() { # <path> <expected status> [<grep pattern for the body>]
  local path=$1 want=$2 pattern=${3:-} code body
  body=$(mktemp)
  # Retry for a while: the edge may take a moment to settle after an invalidation.
  for _ in 1 2 3 4 5; do
    code=$(curl -s -o "$body" -w '%{http_code}' --max-time 20 "$url$path" || echo 000)
    [ "$code" = "$want" ] && break
    sleep 3
  done
  if [ "$code" != "$want" ]; then
    echo "FAIL $path: status $code, wanted $want"; fail=1
  elif [ -n "$pattern" ] && ! grep -Eqi "$pattern" "$body"; then
    echo "FAIL $path: body does not match /$pattern/"; fail=1
  else
    echo "ok   $path"
  fi
  rm -f "$body"
}

# One page of each section, taken from the build so the test follows the content.
pick() { (cd "$dir/$1" 2>/dev/null && ls *.html 2>/dev/null | head -1) || true; }

check / 200 "Top Five Movies"
check /index.html 200
for section in reviews top5 other chickflicks authors; do
  check "/$section.html" 200
  page=$(pick "$section")
  [ -n "$page" ] && check "/$section/$page" 200
done
check /polls.html 200
check /index.xml 200 "<rss"
check /sitemap.xml 200 "<urlset"
check /robots.txt 200
check /no-such-page.html 404 "not found|404"

# The fingerprinted stylesheet and script the home page names must be served.
home=$(curl -s --max-time 20 "$url/")
for asset in $(printf '%s' "$home" | grep -oE '(href|src)="/(css|js)/[^"]+"' | sed -E 's/^(href|src)="//; s/"$//'); do
  check "$asset" 200
done

# Headers set by the CloudFront response-headers policy.
headers=$(curl -sI --max-time 20 "$url/")
for h in strict-transport-security content-security-policy x-content-type-options; do
  if printf '%s' "$headers" | grep -qi "^$h:"; then echo "ok   header $h"; else echo "FAIL header $h missing"; fail=1; fi
done

[ "$fail" = 0 ] && echo "Smoke test passed" || { echo "Smoke test FAILED" >&2; exit 1; }
