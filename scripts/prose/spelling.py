#!/usr/bin/env python3
"""Advisory spelling check on the prose a pull request changes.

Runs typos (config: _typos.toml at the repo root) on the changed content and data files
and reports findings on added or changed lines only. They are posted as a pull request
review with suggestions (review.py) where that is possible, otherwise as warning
annotations; they are always in the job summary. The check never fails because of a
misspelling. Fields that only name another file (item, image, author) are skipped.

Usage: scripts/prose/spelling.py --base origin/main
       scripts/prose/spelling.py --all
Needs typos on the PATH (pip install typos).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prose  # noqa: E402
import review  # noqa: E402

ROOT = prose.ROOT
REFERENCE_KEY = re.compile(r"^\s*(?:- )?(item|image|image_full|author|layout|type|url|aliases):")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--base", help="check lines changed since this commit (merge base)")
    group.add_argument("--all", action="store_true", help="check every line")
    args = ap.parse_args()

    wanted = prose.all_lines() if args.all else prose.changed_lines(args.base)
    if not wanted:
        print("No changed content to check.")
        write_summary(["No changed content to check."])
        return 0

    proc = subprocess.run(
        ["typos", "--format", "json", "--force-exclude", "--", *sorted(wanted)],
        cwd=ROOT, capture_output=True, text=True)
    if proc.returncode not in (0, 2):   # 2 means "typos found"
        print(proc.stderr, file=sys.stderr)
        return proc.returncode or 1

    source = {}
    findings = []
    for raw in proc.stdout.splitlines():
        d = json.loads(raw)
        # A typo in a filename has no line: report it on line 1, which only a new file changes.
        line = d.get("line_num", 1)
        if d.get("type") != "typo" or line not in wanted.get(d["path"], ()):
            continue
        lines = source.setdefault(d["path"], (ROOT / d["path"]).read_text(encoding="utf-8").split("\n"))
        if "line_num" in d and REFERENCE_KEY.match(lines[line - 1]):
            continue
        findings.append((d["path"], line, d["typo"], d["corrections"]))

    notes = [{"path": p, "line": l, "bad": t, "fix": f[0],
              "text": f"**Spelling:** `{t}` should be {' or '.join(f'`{x}`' for x in f)}. "
                      "If it is a name or slang, add it to `_typos.toml`."}
             for p, l, t, f in findings]
    posted = review.post_review("spelling", "Spelling", notes) if notes else False
    if not posted:
        for n in notes:
            print(prose.annotation("warning", n["path"], n["line"], "Spelling", n["text"].replace("`", "")))
    print(f"{len(findings)} misspelling(s) in {len(wanted)} file(s). Advisory: these do not fail the check.")
    summary = [f"**{len(findings)} misspelling(s)** in {len(wanted)} changed file(s). Advisory, so none of this fails the check.\n"]
    if findings:
        summary += ["| File | Line | Found | Did you mean |\n|---|---|---|---|"]
        summary += [f"| `{p}` | {l} | {t} | {', '.join(f)} |" for p, l, t, f in findings]
        summary.append("\nNames and deliberate slang go in `_typos.toml`.")
    write_summary(summary)
    return 0


def write_summary(parts):
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as f:
            f.write("### Spelling\n\n" + "\n".join(parts) + "\n")


if __name__ == "__main__":
    sys.exit(main())
