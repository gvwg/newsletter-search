"""Build data/catalog.json from the ClubExpress Newsletters page.

The Newsletters page is the source of truth: every link to docs.ashx?id=N
is treated as one issue, with the article list shown beside it kept as
"contents" (used by check.py). Nothing else needs to be maintained by hand.

Usage:
    python scripts/harvest.py            # fetch the live page
    python scripts/harvest.py --html f   # parse a saved copy (for testing)
"""

import argparse
import json
import re
import sys
from collections import Counter
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from common import CATALOG_PATH, DOC_URL, LISTING_URL, SITE, http_get, new_session

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
SEASONS = {"spring": 4, "summer": 7, "fall": 10, "autumn": 10, "winter": 1}


def parse_date(title: str):
    """Best-effort (year, month) from titles like 'March 2024',
    'July/August 2020', 'Summer 2015', 'Januar 2008', 'Febuary 2000'.
    Month is the first month named; None if no month or season is found."""
    ym = re.search(r"\b(19|20)\d{2}\b", title)
    year = int(ym.group(0)) if ym else None
    month = None
    for word in re.findall(r"[A-Za-z]+", title.lower()):
        if len(word) >= 3 and word[:3] in MONTHS:
            month = MONTHS[word[:3]]
            break
        if word in SEASONS:
            month = SEASONS[word]
            break
    return year, month


def extract_doc_id(href: str):
    q = parse_qs(urlparse(href).query)
    ids = q.get("id")
    return ids[0] if ids and ids[0].isdigit() else None


def contents_for(a):
    """The bullet list of articles shown beside an issue's link, or [].

    Walks up from the link to the smallest enclosing element that holds a
    list, stopping if that element also holds another issue's link. Works
    for both layouts on the page (newer div rows, older table rows)."""
    node = a
    while node.parent is not None:
        node = node.parent
        ids = {extract_doc_id(x["href"]) for x in node.find_all("a", href=True)
               if "docs.ashx" in x["href"].lower()}
        if len(ids) > 1:
            return []
        ul = node.find("ul")
        if ul:
            return [" ".join(li.get_text(" ", strip=True).split()) for li in ul.find_all("li")]
    return []


def parse_listing(html: str):
    soup = BeautifulSoup(html, "html.parser")
    issues, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(SITE + "/", a["href"])
        if "docs.ashx" not in href.lower():
            continue
        doc_id = extract_doc_id(href)
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        title = " ".join(a.get_text(" ", strip=True).split())
        year, month = parse_date(title)
        if year is None:
            # Every newsletter title carries a year. Links without one are
            # other documents, e.g. site-menu items such as "Gallery Tags".
            print(f"Skipping non-newsletter link '{title}' (id {doc_id})", file=sys.stderr)
            continue
        issues.append({
            "id": doc_id,
            "title": title,
            "year": year,
            "month": month,
            "url": DOC_URL.format(id=doc_id),
            "contents": contents_for(a),
        })
    return issues


def sanity_warnings(issues):
    """Flag things a human should look at: IDs of unusual length (likely a
    typo in the CE page link) and titles with no parseable year."""
    warnings = []
    if not issues:
        return ["No docs.ashx links found. Has the page layout changed?"]
    common_len = Counter(len(i["id"]) for i in issues).most_common(1)[0][0]
    for i in issues:
        if len(i["id"]) != common_len:
            warnings.append(f"Unusual doc ID {i['id']} for '{i['title']}' (possible broken link)")
    return warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="parse a saved HTML file instead of fetching")
    args = ap.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    else:
        html = http_get(LISTING_URL, new_session()).text

    issues = parse_listing(html)
    for w in sanity_warnings(issues):
        print("WARNING:", w, file=sys.stderr)
    if not issues:
        sys.exit(1)

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(issues, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Catalog: {len(issues)} issues written to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
