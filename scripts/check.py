"""Check that each link on the Newsletters page points at the right PDF.

Compares every catalog entry (title, contents list from the CE page) with the
text extracted from the PDF it links to, and reports likely link errors:

  duplicate  the PDF text is identical to another issue's PDF
  contents   the PDF matches the listed contents poorly, or another issue's
             PDF matches them clearly better
  year       dates on the PDF's first two pages never mention the title's year
  header     the dated header at the top of page 1 names a different month
             than the title (catches links off by one issue)

The contents match weights each word by how rare it is across the archive,
so names and specific topics count and words like "president" barely do.
Month mismatches are only checked in the page-1 header: body text routinely
mentions the previous or next month's meeting.

Findings are warnings for a human; the data is still published. Confirmed
false positives (e.g. misprinted headers) go in KNOWN_OK. Exit status is 0
unless --strict is given.

Usage:
    python scripts/check.py            # report
    python scripts/check.py --strict   # exit 1 if anything is reported
"""

import argparse
import json
import math
import os
import re
from collections import Counter

from common import CATALOG_PATH, ISSUES_DIR

MIN_CONTENTS_SCORE = 0.4   # weighted share of listed-contents words found in the PDF
BETTER_MATCH_MARGIN = 0.15  # another PDF scoring this much higher is suspicious
HEADER_CHARS = 200          # how much of page 1 counts as the header

# (doc ID, check) pairs examined by hand and found correct, with the reason.
KNOWN_OK = {
    ("1517820", "year"): "May 2016: header misprinted as April 2015; content is May 2016",
    ("1517820", "header"): "May 2016: header misprinted as April 2015; content is May 2016",
    ("1517815", "header"): "November 2015: header says October 2015; next meeting Nov 25",
    ("1517691", "header"): "May 2006: header says April 2006; Vol 8 Issue 8 follows April's Issue 7",
}

MONTHS = ("january february march april may june july august "
          "september october november december").split()
DATE_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")[\s,]+((?:19|20)\d\d)\b")


def words(text: str) -> set:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def pdf_years(pages: list) -> set:
    text = " ".join(p["text"] for p in pages[:2]).lower()
    return {int(y) for _, y in DATE_RE.findall(text)}


def header_dates(pages: list) -> set:
    head = pages[0]["text"][:HEADER_CHARS].lower() if pages else ""
    return {(MONTHS.index(m) + 1, int(y)) for m, y in DATE_RE.findall(head)}


def title_months(title: str) -> set:
    """All months named in a title, e.g. {7, 8} for 'July/August 2020'."""
    t = title.lower()
    return {n for n, m in enumerate(MONTHS, 1) if m[:3] in t}


def check(catalog: list, issues: dict) -> list:
    """Return [(doc_id, title, check_name, message)]."""
    titles = {c["id"]: c["title"] for c in catalog}
    ids = [c["id"] for c in catalog if c["id"] in issues]
    texts = {i: "\n".join(p["text"] for p in issues[i]["pages"]) for i in ids}
    vocab = {i: words(texts[i]) for i in ids}
    df = Counter(w for i in ids for w in vocab[i])

    def weight(w):   # words in no PDF carry no evidence either way
        return math.log(len(ids) / (1 + df[w])) if df[w] else 0.0

    by_text = {}
    for i in ids:
        by_text.setdefault(texts[i], []).append(i)

    findings = []
    for c in catalog:
        i = c["id"]
        if i not in issues:
            continue
        dupes = [d for d in by_text[texts[i]] if d != i]
        if dupes:
            findings.append((i, c["title"], "duplicate",
                             "PDF text is identical to " + ", ".join(
                                 f"'{titles[d]}' ({d})" for d in dupes)))

        query = set().union(*(words(item) for item in c.get("contents") or []))
        total = sum(weight(w) for w in query)
        if total:
            score = {j: sum(weight(w) for w in query if w in vocab[j]) / total for j in ids}
            best = max((j for j in ids if j != i), key=score.get)
            if score[i] < MIN_CONTENTS_SCORE or score[best] >= score[i] + BETTER_MATCH_MARGIN:
                findings.append((i, c["title"], "contents",
                                 f"listed contents match this PDF {score[i]:.0%}; best other "
                                 f"match is '{titles[best]}' ({best}) at {score[best]:.0%}"))

        years = pdf_years(issues[i]["pages"])
        if c.get("year") and years and c["year"] not in years:
            findings.append((i, c["title"], "year",
                             f"PDF pages 1-2 mention {', '.join(map(str, sorted(years)))}, "
                             f"not {c['year']}"))

        head = header_dates(issues[i]["pages"])
        months = title_months(c["title"])
        if head and months and not any(m in months and y == c.get("year") for m, y in head):
            shown = ", ".join(f"{MONTHS[m - 1].title()} {y}" for m, y in sorted(head, key=lambda d: (d[1], d[0])))
            findings.append((i, c["title"], "header", f"page 1 header is dated {shown}"))
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 if anything is reported")
    args = ap.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    issues = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in ISSUES_DIR.glob("*.json")}
    findings = [f for f in check(catalog, issues) if (f[0], f[2]) not in KNOWN_OK]

    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for doc_id, title, name, msg in findings:
        line = f"{title} (id {doc_id}) [{name}]: {msg}"
        print(f"::warning title=Newsletter link check::{line}" if in_actions else "WARNING: " + line)
    flagged = len({f[0] for f in findings})
    print(f"Checked {len(catalog)} catalog entries: {flagged} flagged, "
          f"{len(KNOWN_OK)} known exceptions in KNOWN_OK")
    if args.strict and findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
