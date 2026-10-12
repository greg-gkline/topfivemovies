#!/bin/bash
# Fetches the pinned grammar tools into .cache/prose/ (git-ignored), once, and checks
# each download against its checksum. Sourced by the grammar check; prints nothing when
# the tools are already there.
#   LanguageTool  rule-based checker with confusable-word rules (needs Java 17+)
#   Harper        offline checker, one binary
set -euo pipefail

LT_VERSION=6.6
LT_SHA256=53600506b399bb5ffe1e4c8dec794fd378212f14aaf38ccef9b6f89314d11631
HARPER_VERSION=2.12.0
HARPER_SHA256=b97d2b72e4b6c9b70499b22696c7a21209035497585f72b0ef12967c92e35089

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TOOLS=$ROOT/.cache/prose
mkdir -p "$TOOLS"

if [ ! -f "$TOOLS/LanguageTool-$LT_VERSION/languagetool-server.jar" ]; then
	echo "fetching LanguageTool $LT_VERSION" >&2
	zip=$TOOLS/lt.zip
	curl -fsSL -o "$zip" "https://languagetool.org/download/LanguageTool-$LT_VERSION.zip"
	echo "$LT_SHA256  $zip" | sha256sum -c --quiet
	unzip -q -o "$zip" -d "$TOOLS"
	rm -f "$zip"
fi

if [ ! -x "$TOOLS/harper-cli" ]; then
	echo "fetching Harper $HARPER_VERSION" >&2
	tgz=$TOOLS/harper.tar.gz
	curl -fsSL -o "$tgz" "https://github.com/Automattic/harper/releases/download/v$HARPER_VERSION/harper-cli-x86_64-unknown-linux-gnu.tar.gz"
	echo "$HARPER_SHA256  $tgz" | sha256sum -c --quiet
	tar -xzf "$tgz" -C "$TOOLS" harper-cli
	rm -f "$tgz"
fi

export LT_SERVER_JAR=$TOOLS/LanguageTool-$LT_VERSION/languagetool-server.jar HARPER=$TOOLS/harper-cli
