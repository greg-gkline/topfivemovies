#!/bin/bash
# Quality gates over a clean Hugo build (Phase 3):
#   html   the Nu HTML Checker on every page, stylesheet and SVG; errors and warnings fail
#   a11y   axe-core on every page at desktop and phone width (a11y.py)
#   links  lychee on every internal link and #fragment, offline; the site's own absolute
#          URLs (canonical, prev/next) are checked against the build too
#   external  lychee on the links to other sites; advisory, since old sites come and go
# Lighthouse CI (lighthouserc.json) needs Node, so it runs in the site workflow only.
#
# Usage: scripts/quality/check.sh [html] [a11y] [links] [external]   (default: html a11y links)
# Set NO_BUILD=1 to check the existing public/ instead of building it first.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
source scripts/quality/tools.sh
PUBLIC=$ROOT/public
SITE=https://www.topfivemovies.com/

if [ -z "${NO_BUILD:-}" ]; then
	hugo --gc --cleanDestinationDir --panicOnWarning --quiet
fi

checks=("$@")
[ ${#checks[@]} -eq 0 ] && checks=(html a11y links)

status=0
for check in "${checks[@]}"; do
	echo "== $check"
	case $check in
		html)
			java -jar "$VNU_JAR" --skip-non-html --also-check-css --also-check-svg "$PUBLIC" || status=1
			;;
		a11y)
			python3 scripts/quality/a11y.py --public "$PUBLIC" || status=1
			;;
		links)
			"$LYCHEE" --offline --include-fragments --no-progress --root-dir "$PUBLIC" \
				--remap "^${SITE//./\\.}(.*)\$ file://$PUBLIC/\$1" "$PUBLIC/**/*.html" || status=1
			;;
		external)
			"$LYCHEE" --no-progress --root-dir "$PUBLIC" --scheme https --scheme http --exclude "^${SITE//./\\.}" \
				--max-retries 2 "$PUBLIC/**/*.html" \
				|| echo "(advisory: external links are not a gate)"
			;;
		*)
			echo "unknown check: $check" >&2
			exit 2
			;;
	esac
done
exit $status
