#!/usr/bin/env python3
"""Advisory wrong-word and grammar check on the prose a pull request changes.

Runs LanguageTool and Harper over the prose of the changed content and data files
(prose.py) and reports only findings on added or changed lines. Which rules count is in
rules.json. Findings are posted as a pull request review with suggestions (review.py)
where that is possible, otherwise as warning annotations; they are always in the job
summary. They never fail the check. Use --all to scan everything, as a baseline.

Usage: scripts/prose/grammar.py --base origin/main [--max-files 50]
       scripts/prose/grammar.py --all
Needs Java 17+. The tools are fetched and checksummed by tools.sh.
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prose  # noqa: E402
import review  # noqa: E402

ROOT = prose.ROOT
RULES = json.loads((Path(__file__).parent / "rules.json").read_text())
ANNOTATIONS_PER_TOOL = 10   # GitHub shows at most 10 warnings per step; only used without a review
REPLACE = re.compile(r"^Replace with: [“\"](.*)[”\"]$")


def fetch_tools():
    out = subprocess.run(
        ["bash", "-c", f'source "{ROOT}/scripts/prose/tools.sh" && echo "$LT_SERVER_JAR" && echo "$HARPER"'],
        check=True, capture_output=True, text=True)
    jar, harper = out.stdout.split("\n")[:2]
    return jar, harper


def languagetool(jar, texts):
    """{path: [(line, rule id, message, suggestion)]} from a throwaway local server."""
    cfg = RULES["languagetool"]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = subprocess.Popen(
        ["java", "-Xmx1g", "-cp", jar, "org.languagetool.server.HTTPServer", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/v2/check"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/v2/languages", timeout=2)
                break
            except OSError:
                if server.poll() is not None:
                    sys.exit("LanguageTool server exited at startup")
                time.sleep(1)
        else:
            sys.exit("LanguageTool server did not start")
        found = {}
        for path, text in texts.items():
            body = urllib.parse.urlencode({
                "language": "en-US", "text": text,
                "disabledCategories": ",".join(cfg["disabled_categories"]),
                "disabledRules": ",".join(cfg["disabled_rules"]),
            }).encode()
            matches = json.load(urllib.request.urlopen(url, body, timeout=120))["matches"]
            rows = []
            for m in matches:
                rule = m["rule"]["id"]
                if rule.startswith(tuple(cfg["disabled_rule_prefixes"])):
                    continue
                line = text.count("\n", 0, m["offset"]) + 1
                bad = text[m["offset"]:m["offset"] + m["length"]]
                fix = m["replacements"][0]["value"] if m["replacements"] else None
                rows.append((line, rule, m["message"], bad, fix))
            found[path] = rows
        return found
    finally:
        server.terminate()
        server.wait()


def harper(binary, texts):
    cfg = RULES["harper"]
    found = {p: [] for p in texts}
    with tempfile.TemporaryDirectory() as tmp:
        names = {}
        for i, (path, text) in enumerate(texts.items()):
            name = f"{i}.md"
            (Path(tmp) / name).write_text(text, encoding="utf-8")
            names[name] = path
        proc = subprocess.run(
            [binary, "lint", "--no-color", "--format", "json", "--quiet",
             *[str(Path(tmp) / n) for n in names]],
            capture_output=True, text=True)
        # Exit status 1 only means "lints were found".
        if not proc.stdout.strip():
            if proc.returncode not in (0, 1):
                sys.exit(f"harper failed: {proc.stderr}")
            return found
        for entry in json.loads(proc.stdout):
            path = names[Path(entry["file"]).name]
            for l in entry["lints"]:
                if l["kind"] not in cfg["kinds"] or l["rule"] in cfg["disabled_rules"]:
                    continue
                raw = l["suggestions"][0] if l["suggestions"] else None
                m = REPLACE.match(raw) if raw else None
                message = l["message"] + (f" ({raw})" if raw and not m else "")
                found[path].append((l["line"], l["rule"], message, l["matched_text"], m.group(1) if m else None))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--base", help="check lines changed since this commit (merge base)")
    group.add_argument("--all", action="store_true", help="check every line")
    ap.add_argument("--max-files", type=int, default=50, help="cap on files per run")
    args = ap.parse_args()

    wanted = prose.all_lines() if args.all else prose.changed_lines(args.base)
    texts, lines = {}, {}
    for path, changed in sorted(wanted.items()):
        masked = prose.prose_lines(path)
        if any(masked[n - 1].strip() for n in changed if n <= len(masked)):
            texts[path], lines[path] = "\n".join(masked), changed
    summary = []
    if not args.all and len(texts) > args.max_files:
        skipped = sorted(texts)[args.max_files:]
        texts = {p: texts[p] for p in sorted(texts)[:args.max_files]}
        summary.append(f"Only the first {args.max_files} changed files were checked; skipped: "
                       + ", ".join(f"`{p}`" for p in skipped) + "\n")
    if not texts:
        print("No changed prose to check.")
        write_summary(["No changed prose to check."])
        return

    jar, binary = fetch_tools()
    results = {"LanguageTool": languagetool(jar, texts), "Harper": harper(binary, texts)}

    rows = []
    for tool, per_file in results.items():
        for path in sorted(per_file):
            for line, rule, message, bad, fix in sorted(per_file[path], key=lambda r: r[:2]):
                if line in lines[path]:
                    rows.append((path, line, tool, rule, bad, fix, message))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    notes = [{"path": path, "line": line, "bad": bad, "fix": fix,
              "text": f"**{tool}** ({rule}): {message}" + (f" Suggestion: `{fix}`" if fix else "")}
             for path, line, tool, rule, bad, fix, message in rows]
    if not (notes and review.post_review("grammar", "Grammar review", notes)):
        emitted = {}
        for (path, line, tool, rule, bad, fix, message), n in zip(rows, notes):
            if emitted.get(tool, 0) < ANNOTATIONS_PER_TOOL:
                emitted[tool] = emitted.get(tool, 0) + 1
                print(prose.annotation("warning", path, line, f"{tool}: {rule}", n["text"].replace("`", "")))
    print(f"{len(rows)} finding(s) in {len(texts)} file(s). Advisory: these do not fail the check.")
    summary.append(f"**{len(rows)} finding(s)** in {len(texts)} file(s). Advisory, so none of this fails the check.\n")
    if rows:
        summary.append("| File | Line | Tool | Rule | Text | Suggestion |\n|---|---|---|---|---|---|")
        for path, line, tool, rule, bad, fix, message in rows:
            cell = lambda s: (s or "").replace("|", "\\|").replace("\n", " ")
            summary.append(f"| `{path}` | {line} | {tool} | {rule} | {cell(bad)} | {cell(fix)} |")
    write_summary(summary)


def write_summary(parts):
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as f:
            f.write("### Grammar review\n\n" + "\n".join(parts) + "\n")


if __name__ == "__main__":
    main()
