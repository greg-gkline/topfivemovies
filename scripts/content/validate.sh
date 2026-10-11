#!/usr/bin/env bash
# Validate content/ and data/: YAML lint, JSON Schema per content type, and the
# cross-file references. Run from anywhere; CI runs exactly this.
#
# Needs: python3 with PyYAML, yamllint, check-jsonschema.
set -uo pipefail   # not -e: run every check, then fail if any failed

root=$(cd "$(dirname "$0")/../.." && pwd)
schemas=$root/scripts/content/schemas
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$root" || exit 1

status=0
run() { echo "+ $*"; "$@" || status=1; }

run python3 scripts/content/front_matter.py "$work"

run yamllint --strict -c .yamllint.yaml data/
# From inside $work, so messages name <section>/<page>.yaml
echo "+ yamllint (front matter of content/*/*.md)"
(cd "$work" && yamllint --strict -c "$root/.yamllint.yaml" .) || status=1

for pair in reviews:review chickflicks:chickflick other:other top5:top5 authors:author; do
	section=${pair%%:*} schema=${pair#*:}
	files=("$work/$section"/*.yaml)
	[ -e "${files[0]}" ] || continue
	echo "+ check-jsonschema $schema.json (front matter of content/$section/*.md)"
	check-jsonschema --schemafile "$schemas/$schema.json" "${files[@]}" || status=1
done
for name in responses polls quotes; do
	run check-jsonschema --schemafile "$schemas/$name.json" "data/$name.yaml"
done

run python3 scripts/content/check_refs.py
exit $status
