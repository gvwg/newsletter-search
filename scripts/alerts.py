"""Record check.py findings as GitHub issues, once each.

One GitHub issue per flagged newsletter link (doc ID), labelled "link-check"
and carrying a hidden marker with the doc ID. Rules:

  - An ID that already has a link-check issue, open or closed, never gets
    another one. Closing an issue by hand is final; to silence a false
    positive for good, add it to KNOWN_OK in check.py.
  - An open issue whose ID is no longer flagged (link corrected in CE, or
    added to KNOWN_OK) is closed automatically with a comment.
  - A duplicate pair is one issue: an entry flagged only as the twin of an
    entry that has other findings is folded into that entry's issue.

Uses the GitHub CLI (gh), which GitHub-hosted runners provide; in Actions it
authenticates with GH_TOKEN.
"""

import json
import os
import re
import subprocess

LABEL = "link-check"
MARKER = "<!-- link-check-id: {id} -->"
MARKER_RE = re.compile(r"<!-- link-check-id: (\d+) -->")
NEWSLETTERS_PAGE = "https://gvwg.ca/content.aspx?page_id=22&club_id=182740&module_id=717502"
MIN_COVERAGE = 0.9   # close nothing unless this share of catalog entries was checked


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def group(findings: list) -> dict:
    """{doc_id: [(title, check, message), ...]}, with duplicate twins folded in."""
    by_id = {}
    for doc_id, title, name, msg in findings:
        by_id.setdefault(doc_id, []).append((title, name, msg))
    for doc_id, items in list(by_id.items()):
        if all(name == "duplicate" for _, name, _ in items):
            twins = re.findall(r"\((\d+)\)", " ".join(msg for _, _, msg in items))
            if twins and all(t in by_id and any(n != "duplicate" for _, n, _ in by_id[t])
                             for t in twins):
                del by_id[doc_id]
    return by_id


def issue_body(doc_id: str, items: list, catalog_by_id: dict) -> str:
    entry = catalog_by_id.get(doc_id, {})
    run = ""
    if os.environ.get("GITHUB_RUN_ID"):
        run = (f"\nFound by run {os.environ['GITHUB_SERVER_URL']}/"
               f"{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}.\n")
    lines = "\n".join(f"- **{name}**: {msg}" for _, name, msg in items)
    return f"""{MARKER.format(id=doc_id)}
The link **{entry.get('title', doc_id)}** on the [Newsletters page]({NEWSLETTERS_PAGE}) may point at the wrong PDF ({entry.get('url', '')}).

{lines}

**What to do**
- If the link is wrong: fix it on the Newsletters page in ClubExpress. The next daily run picks up the change and closes this issue.
- If the link is right (for example a misprinted date in the PDF): add the doc ID and check to `KNOWN_OK` in `scripts/check.py`. The next run closes this issue.

This issue is created once per link; closing it by hand does not bring it back.
{run}"""


def sync(findings: list, catalog: list, checked: int, dry_run: bool = False) -> None:
    catalog_by_id = {c["id"]: c for c in catalog}
    flagged = group(findings)

    existing = {}   # doc_id -> {"number", "state"}; read-only, so also done on a dry run
    listed = json.loads(gh("issue", "list", "--label", LABEL, "--state", "all",
                           "--limit", "1000", "--json", "number,state,body"))
    for it in listed:
        m = MARKER_RE.search(it["body"] or "")
        if m:
            existing[m.group(1)] = it

    if not dry_run:
        gh("label", "create", LABEL, "--color", "d93f0b", "--force",
           "--description", "Newsletters page link that may point at the wrong PDF")

    for doc_id, items in flagged.items():
        if doc_id in existing:
            continue   # already recorded (open or closed): never repeat
        title = f"Newsletter link check: {items[0][0]} (doc {doc_id})"
        print(f"Opening issue: {title}")
        if not dry_run:
            gh("issue", "create", "--title", title, "--label", LABEL,
               "--body", issue_body(doc_id, items, catalog_by_id))

    coverage = checked / len(catalog) if catalog else 0
    for doc_id, it in existing.items():
        if it["state"] != "OPEN" or doc_id in flagged:
            continue
        if coverage < MIN_COVERAGE:
            print(f"Not closing issue #{it['number']}: only {coverage:.0%} of the catalog was checked")
            continue
        reason = ("no longer linked from the Newsletters page" if doc_id not in catalog_by_id
                  else "no longer flagged by the link check")
        print(f"Closing issue #{it['number']} (doc {doc_id}): {reason}")
        if not dry_run:
            gh("issue", "close", str(it["number"]), "--comment",
               f"Closed automatically: doc {doc_id} is {reason}.")
