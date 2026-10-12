#!/usr/bin/env python3
"""Create or update one comment on the pull request being checked.

The comment is found by a marker, so each run of a workflow edits its own earlier comment
instead of adding another. Used by the preview and terraform-plan workflows.

Usage: pr_comment.py --marker preview --body-file comment.md
Reads the same environment as scripts/prose/review.py (GITHUB_TOKEN, GITHUB_REPOSITORY,
GITHUB_EVENT_PATH). Where a comment cannot be posted (not a pull request, or a fork, where
the token is read-only) it says so and exits 0: the workflow's job summary has the text.
"""
import argparse
import os
import sys
from pathlib import Path
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prose"))
import review  # noqa: E402

LIMIT = 60000   # GitHub's comment limit is 65536 characters


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marker", required=True, help="identifies this workflow's comment")
    ap.add_argument("--body-file", required=True, type=Path)
    args = ap.parse_args()

    target = review.pull_request()
    if not target:
        print("No pull request comment: not a same-repository pull request run.")
        return
    repo, number, _ = target
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    marker = f"<!-- tfm-comment:{args.marker} -->"
    body = args.body_file.read_text(encoding="utf-8")
    if len(body) > LIMIT:
        body = body[:LIMIT] + "\n\n_(truncated; the job summary has the rest)_"
    body += f"\n{marker}"

    try:
        page, existing = 1, None
        while existing is None:
            batch = review.api("GET", f"{base}/repos/{repo}/issues/{number}/comments?per_page=100&page={page}")
            existing = next((c["id"] for c in batch if marker in c["body"]), None)
            if len(batch) < 100:
                break
            page += 1
        if existing:
            review.api("PATCH", f"{base}/repos/{repo}/issues/comments/{existing}", {"body": body})
            print(f"Updated comment {existing}.")
        else:
            review.api("POST", f"{base}/repos/{repo}/issues/{number}/comments", {"body": body})
            print("Posted a comment.")
    except URLError as e:
        print(f"Could not post the comment ({e}); see the job summary.")


if __name__ == "__main__":
    main()
