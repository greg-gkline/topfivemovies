"""Post the prose checks' findings as a pull request review (used by spelling.py and
grammar.py).

One review per run, "comment" only, so it never blocks a merge. Each finding is an
inline comment on its line, with a GitHub suggestion block when the fix is a plain
replacement inside that line. A comment already posted on an earlier run is not posted
again, so a push does not repeat it.

post_review() returns False, and the caller falls back to workflow annotations and the
job summary, when it cannot post: outside a pull request, with no token, or on a fork,
where the token is read-only.
"""
import json
import os
import re
import urllib.error
import urllib.request

import prose

MAX_COMMENTS = 40


def pull_request():
    """(repo, number, head sha) of the pull request being checked, or None where a review
    cannot be posted."""
    path, token = os.environ.get("GITHUB_EVENT_PATH"), os.environ.get("GITHUB_TOKEN")
    if not (path and token and os.environ.get("GITHUB_REPOSITORY")):
        return None
    pr = json.load(open(path, encoding="utf-8")).get("pull_request")
    if not pr or pr["head"]["repo"]["full_name"] != pr["base"]["repo"]["full_name"]:
        return None
    return os.environ["GITHUB_REPOSITORY"], pr["number"], pr["head"]["sha"]


def suggestion(path, line, bad, fix):
    """The line with `bad` replaced by `fix`, if that is one unambiguous edit; else None."""
    if not bad or fix is None:
        return None
    original = (prose.ROOT / path).read_text(encoding="utf-8").split("\n")[line - 1]
    edited, n = re.subn(rf"(?<!\w){re.escape(bad)}(?!\w)", lambda _: fix, original)
    return edited if n == 1 and edited != original else None


def api(method, url, payload=None):
    req = urllib.request.Request(
        url, method=method, data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def existing(base, repo, number, marker):
    """(path, line, body) of this check's comments already on the pull request."""
    seen, page = set(), 1
    while True:
        batch = api("GET", f"{base}/repos/{repo}/pulls/{number}/comments?per_page=100&page={page}")
        for c in batch:
            if marker in c["body"]:
                seen.add((c["path"], c.get("line") or c.get("original_line"), c["body"]))
        if len(batch) < 100:
            return seen
        page += 1


def post_review(kind, title, findings):
    """findings: dicts with path, line, text and, optionally, bad and fix (for a
    suggestion block). Returns True if the review was posted, or there was nothing new."""
    target = pull_request()
    if not target:
        return False
    repo, number, head = target
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    marker = f"<!-- tfm-prose:{kind} -->"
    try:
        seen = existing(base, repo, number, marker)
        comments = []
        for f in findings:
            body = f["text"]
            fixed = suggestion(f["path"], f["line"], f.get("bad"), f.get("fix"))
            if fixed is not None:
                body += f"\n\n```suggestion\n{fixed}\n```"
            body += f"\n{marker}"
            if (f["path"], f["line"], body) not in seen:
                comments.append({"path": f["path"], "line": f["line"], "side": "RIGHT", "body": body})
        if not comments:
            print(f"Review: nothing new to post ({len(findings)} finding(s) already commented).")
            return True
        extra = max(0, len(comments) - MAX_COMMENTS)
        text = f"**{title}**: {len(comments)} new finding(s). Advisory: this review never blocks the merge."
        if extra:
            text += f" Only the first {MAX_COMMENTS} are commented here; the rest are in the job summary."
        api("POST", f"{base}/repos/{repo}/pulls/{number}/reviews",
            {"commit_id": head, "event": "COMMENT", "body": f"{text}\n{marker}",
             "comments": comments[:MAX_COMMENTS]})
        print(f"Review posted with {min(len(comments), MAX_COMMENTS)} comment(s).")
        return True
    except urllib.error.URLError as e:   # includes HTTPError: no write access, a line not in the diff
        detail = e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else e
        print(f"Could not post the review ({e}): {detail}")
        return False
