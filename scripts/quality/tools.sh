#!/bin/bash
# Fetches the pinned quality-gate tools into .cache/quality/ (git-ignored), once, and
# checks each download against its published checksum. Sourced by check.sh; prints
# nothing when the tools are already there.
#   vnu.jar   the Nu HTML Checker, from the vnu-jar npm package (needs Java 11+)
#   axe.min.js axe-core, from its npm package (injected into Chromium by a11y.py)
#   lychee    the link checker, from its GitHub release
set -euo pipefail

VNU_VERSION=26.9.16
VNU_SHA512=hDdy5FbqAD+eOZjUgYNzidSzi54v/VleB/asOyzYGCPcmsA9K4av6+oKS+ZP9DI1N2s/z6bX7k8kc5wWr3lsYg==
AXE_VERSION=4.13.0
AXE_SHA512=UzGt8zg7Ny8djbYMhxl2zuEevVa7r2gJjYY5Lwr1xM7+XU2nd6CkIWFTVcCIbAP63vSz71NaVyyuSk9lHKcy0A==
LYCHEE_VERSION=0.24.2
LYCHEE_SHA256=1f4e0ef7f6554a6ed33dd7ac144fb2e1bbed98598e7af973042fc5cd43951c9a

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TOOLS=$ROOT/.cache/quality
mkdir -p "$TOOLS"

# npm_fetch <package> <version> <sha512, base64> <file in the package> <destination>
npm_fetch() {
	local tgz="$TOOLS/$1-$2.tgz"
	[ -f "$5" ] && return
	echo "fetching $1 $2" >&2
	curl -fsSL -o "$tgz" "https://registry.npmjs.org/$1/-/$1-$2.tgz"
	local actual
	actual=$(openssl dgst -sha512 -binary "$tgz" | base64 -w0)
	if [ "$actual" != "$3" ]; then
		echo "checksum mismatch for $1 $2" >&2
		rm -f "$tgz"
		exit 1
	fi
	tar -xzf "$tgz" -C "$TOOLS" --transform "s|^package/$4\$|$(basename "$5")|" "package/$4"
	rm -f "$tgz"
}

npm_fetch vnu-jar "$VNU_VERSION" "$VNU_SHA512" build/dist/vnu.jar "$TOOLS/vnu.jar"
npm_fetch axe-core "$AXE_VERSION" "$AXE_SHA512" axe.min.js "$TOOLS/axe.min.js"

if [ ! -x "$TOOLS/lychee" ]; then
	echo "fetching lychee $LYCHEE_VERSION" >&2
	tgz=$TOOLS/lychee.tar.gz
	curl -fsSL -o "$tgz" "https://github.com/lycheeverse/lychee/releases/download/lychee-v$LYCHEE_VERSION/lychee-x86_64-unknown-linux-gnu.tar.gz"
	echo "$LYCHEE_SHA256  $tgz" | sha256sum -c --quiet
	tar -xzf "$tgz" -C "$TOOLS" --strip-components=1 lychee-x86_64-unknown-linux-gnu/lychee
	rm -f "$tgz"
fi

export VNU_JAR=$TOOLS/vnu.jar AXE_JS=$TOOLS/axe.min.js LYCHEE=$TOOLS/lychee
