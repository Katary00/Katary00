"""Rewrite the <!--activity:start--> ... <!--activity:end--> block of README.md
with the user's latest public GitHub activity. No third-party dependencies."""

import json
import os
import re
import sys
import urllib.request

USER = os.environ.get("GH_USER", "Katary00")
MAX_LINES = int(os.environ.get("MAX_LINES", "5"))
README = os.environ.get("README_PATH", "README.md")
START, END = "<!--activity:start-->", "<!--activity:end-->"


def fetch_events():
    req = urllib.request.Request(
        f"https://api.github.com/users/{USER}/events/public?per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def describe(ev):
    repo = ev["repo"]["name"]
    link = f"[{repo}](https://github.com/{repo})"
    p = ev.get("payload", {})
    kind = ev["type"]
    if kind == "PushEvent":
        return f"pushed to {link}", ("push", repo)
    if kind == "PullRequestEvent":
        pr = p.get("pull_request", {})
        action = "merged" if pr.get("merged") else p.get("action")
        if action not in ("opened", "merged"):
            return None, None
        num = pr.get("number")
        return f"{action} PR [#{num}]({pr.get('html_url', '')}) in {link}", ("pr", repo, num)
    if kind == "CreateEvent" and p.get("ref_type") == "repository":
        return f"created {link}", ("create", repo)
    if kind == "ReleaseEvent":
        return f"released {p.get('release', {}).get('tag_name', '')} of {link}", ("rel", repo)
    return None, None


def build_lines(events):
    lines, seen = [], set()
    for ev in events:
        text, key = describe(ev)
        if not text or key in seen:
            continue
        seen.add(key)
        lines.append(f"`{ev['created_at'][:10]}` {text}  ")
        if len(lines) == MAX_LINES:
            break
    return lines or ["Nothing public in the last few weeks — probably heads-down on my thesis."]


def main():
    with open(README, encoding="utf-8") as f:
        readme = f.read()
    if START not in readme or END not in readme:
        sys.exit(f"markers {START} / {END} not found in {README}")
    block = "\n".join(build_lines(fetch_events()))
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _: f"{START}\n{block}\n{END}",
        readme,
        flags=re.S,
    )
    if new != readme:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
