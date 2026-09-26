"""Record check.py findings as GitHub issues, once each.

Three kinds, each with its own label and a hidden marker with the doc ID
(<!-- kind-id: N -->):

  link-check  a newsletter whose title may not match its PDF (see check.py)
  contents    a newsletter with no contents list (none could be read from the PDF)
  untitled    a folder document left out because its title has no year

Rules, for every kind:

  - A doc ID that already has an issue of that kind, open or closed, never
    gets another one. Closing an issue by hand is final; to silence a
    link-check false positive for good, add it to KNOWN_OK in check.py.
  - An open issue whose ID is no longer flagged is closed automatically
    with a comment.
  - link-check only: a duplicate pair is one issue: an entry flagged only as
    the twin of an entry that has other findings is folded into that entry's
    issue.

Uses the GitHub CLI (gh), which GitHub-hosted runners provide; in Actions it
authenticates with GH_TOKEN.
"""

import json
import os
import re
import subprocess

LABELS = {
    "link-check": ("d93f0b", "Newsletter whose title may not match its PDF"),
    "contents": ("fbca04", "Newsletter with no contents list; add one in data/overrides.json"),
    "untitled": ("fbca04", "Folder document left out: no year in its title"),
}
MIN_COVERAGE = 0.9   # close no link-check issue unless this share of the catalog was checked


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def marker(kind: str, doc_id: str) -> str:
    return f"<!-- {kind}-id: {doc_id} -->"


def run_note() -> str:
    if not os.environ.get("GITHUB_RUN_ID"):
        return ""
    return (f"\nFound by run {os.environ['GITHUB_SERVER_URL']}/"
            f"{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}.\n")


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


def link_check_body(doc_id: str, items: list, catalog_by_id: dict) -> str:
    entry = catalog_by_id.get(doc_id, {})
    lines = "\n".join(f"- **{name}**: {msg}" for _, name, msg in items)
    return f"""The newsletter **{entry.get('title', doc_id)}** may not match its PDF ({entry.get('url', '')}).

{lines}

**What to do**
- If the title is wrong: correct the document's title in the ClubExpress Newsletters folder, or set a title for doc {doc_id} under `titles` in `data/overrides.json`. If the document is not a newsletter issue, add it under `exclude` there. The next run picks up the change and closes this issue.
- If the title is right (for example a misprinted date in the PDF): add the doc ID and check to `KNOWN_OK` in `scripts/check.py`. The next run closes this issue.

This issue is created once per document; closing it by hand does not bring it back.
"""


def contents_body(doc_id: str, title: str, url: str) -> str:
    return f"""No contents list could be read from **{title}** ({url}), so the newsletters list shows it without one. The layout of its table of contents may have changed.

**What to do**
- Add the list for doc {doc_id} under `contents` in `data/overrides.json`, one string per article, as printed in the issue. The next run closes this issue.
- If the layout has changed for good, the reader in `scripts/toc.py` may need updating; `python scripts/toc.py --score` checks that a change does not make the archive worse.

This issue is created once per document; closing it by hand does not bring it back.
"""


def untitled_body(doc_id: str, ce_title: str) -> str:
    return f"""The document **{ce_title}** (https://gvwg.ca/docs.ashx?id={doc_id}) is in the ClubExpress Newsletters folder but is not on the newsletters site: its title has no year, so it cannot be dated.

**What to do**
- If it is a newsletter issue: give it a title with the month and year in ClubExpress (for example "October 2026"), or set one for doc {doc_id} under `titles` in `data/overrides.json`.
- If it is not: move it out of the Newsletters folder, or add it under `exclude` in `data/overrides.json`.

The next run picks up the change and closes this issue. This issue is created once per document; closing it by hand does not bring it back.
"""


def record(kind: str, flagged: dict, can_close: bool = True, dry_run: bool = False) -> None:
    """Open one issue per newly flagged doc ID and close resolved ones.
    flagged = {doc_id: (issue title, body)}. can_close=False keeps open
    issues open (used when too little was checked to be sure)."""
    marker_re = re.compile(rf"<!-- {re.escape(kind)}-id: (\d+) -->")
    existing = {}   # doc_id -> {"number", "state"}; read-only, so also done on a dry run
    listed = json.loads(gh("issue", "list", "--label", kind, "--state", "all",
                           "--limit", "1000", "--json", "number,state,body"))
    for it in listed:
        m = marker_re.search(it["body"] or "")
        if m:
            existing[m.group(1)] = it

    if not dry_run:
        color, description = LABELS[kind]
        gh("label", "create", kind, "--color", color, "--force", "--description", description)

    for doc_id, (title, body) in flagged.items():
        if doc_id in existing:
            continue   # already recorded (open or closed): never repeat
        print(f"Opening issue: {title}")
        if not dry_run:
            gh("issue", "create", "--title", title, "--label", kind,
               "--body", f"{marker(kind, doc_id)}\n{body}{run_note()}")

    for doc_id, it in existing.items():
        if it["state"] != "OPEN" or doc_id in flagged:
            continue
        if not can_close:
            print(f"Not closing issue #{it['number']}: too little of the catalog was checked")
            continue
        print(f"Closing issue #{it['number']} (doc {doc_id}): no longer flagged")
        if not dry_run:
            gh("issue", "close", str(it["number"]), "--comment",
               f"Closed automatically: doc {doc_id} is no longer flagged ({kind}).")


def sync(findings: list, catalog: list, checked: int, dry_run: bool = False) -> None:
    """link-check issues from check.py's findings."""
    catalog_by_id = {c["id"]: c for c in catalog}
    flagged = {doc_id: (f"Newsletter link check: {items[0][0]} (doc {doc_id})",
                        link_check_body(doc_id, items, catalog_by_id))
               for doc_id, items in group(findings).items()}
    coverage = checked / len(catalog) if catalog else 0
    record("link-check", flagged, can_close=coverage >= MIN_COVERAGE, dry_run=dry_run)


def sync_catalog(catalog: list, extracted: set, folder: list, excluded: set,
                 dry_run: bool = False) -> None:
    """contents issues for extracted newsletters with no contents list, and
    untitled issues for folder documents left out of the catalog."""
    missing = {c["id"]: (f"No contents list: {c['title']} (doc {c['id']})",
                         contents_body(c["id"], c["title"], c["url"]))
               for c in catalog if c["id"] in extracted and not c.get("contents")}
    listed = {c["id"] for c in catalog}
    untitled = {d["id"]: (f"Folder document left out: {d['title']} (doc {d['id']})",
                          untitled_body(d["id"], d["title"]))
                for d in folder if d["id"] not in listed and d["id"] not in excluded}
    record("contents", missing, dry_run=dry_run)
    record("untitled", untitled, can_close=bool(folder), dry_run=dry_run)
