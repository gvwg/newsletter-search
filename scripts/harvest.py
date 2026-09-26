"""Build data/catalog.json from the ClubExpress Newsletters folder.

The Newsletters folder of the public Document Library is the source of
truth: every document in it is one issue, except those excluded in
data/overrides.json. data/catalog.json is the committed record: each run
adds new documents, drops removed ones and updates titles, and keeps each
issue's contents list.

Titles: the CE document title is used if it has a month and a year and is
not a bare filename ("2004.01.January.pdf"); otherwise an existing issue
keeps its catalog title, and a new one gets a title made from the filename
("January 2004"). data/overrides.json can set any title by hand.

Contents lists: the issues linked from the old CE Newsletters page keep the
lists typed on that page (contents_source "ce"; see --bootstrap). New issues
start with none; extract.py reads them from the PDF ("pdf"). A list in
data/overrides.json always wins ("override").

The raw folder listing is also written to data/folder.json, so changes in
the folder show up in the commit history.

Usage:
    python scripts/harvest.py                # read the live folder
    python scripts/harvest.py --html f       # parse a saved folder listing (testing)
    python scripts/harvest.py --bootstrap    # also copy the contents lists from the
                                             # old CE Newsletters page (one-time)
"""

import argparse
import html as htmllib
import json
import re
import sys
from collections import Counter
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from common import (CATALOG_PATH, DOC_URL, FOLDER_LIST_URL, FOLDER_PATH, LIBRARY_URL,
                    LISTING_URL, OVERRIDES_PATH, SITE, http_get, new_session)

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
SEASONS = {"spring": 4, "summer": 7, "fall": 10, "autumn": 10, "winter": 1}
MAX_REMOVE = 10   # more removals than this in one run suggests a bad folder read
FOLDER_DOC_RE = re.compile(r"""loadDetails\(this,"(\d+)"\)'>(.*?)</div>""", re.S)


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


# ---- the Newsletters folder (source of truth) ----

def parse_folder(html: str):
    """[(doc_id, CE title)] from the folder list handler, newest first."""
    return [(doc_id, " ".join(htmllib.unescape(title).split()))
            for doc_id, title in FOLDER_DOC_RE.findall(html)]


def fetch_folder() -> str:
    session = new_session()
    http_get(LIBRARY_URL, session)   # sets the cookie the list handler needs
    return http_get(FOLDER_LIST_URL, session).text


def is_bare_filename(title: str) -> bool:
    return title.lower().endswith(".pdf")


def title_from_filename(name: str):
    """'2004.01.January.pdf' -> 'January 2004', '2015.07.Summer.pdf' ->
    'Summer 2015'; None without a year."""
    year, _ = parse_date(name)
    if year is None:
        return None
    words = " ".join(re.sub(r"[\d._]+", " ", re.sub(r"\.pdf$", "", name, flags=re.I)).split())
    return f"{words} {year}" if words else str(year)


def issue_title(ce_title: str, old_title):
    """The title rule (see the module docstring). None if no title with a
    year can be found; such a document is left out and reported."""
    year, month = parse_date(ce_title)
    if year and month and not is_bare_filename(ce_title):
        return ce_title
    if old_title:
        return old_title
    if is_bare_filename(ce_title):
        return title_from_filename(ce_title)
    return ce_title if year else None


def load_overrides():
    """(exclude, titles, contents), each keyed by doc ID."""
    data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    return data.get("exclude", {}), data.get("titles", {}), data.get("contents", {})


def merge(folder, catalog, overrides):
    """New catalog from the folder listing and the previous catalog.
    Returns (catalog, skipped); skipped lists folder documents left out
    because no dated title could be found."""
    exclude, titles, contents = overrides
    old = {c["id"]: c for c in catalog}
    new, skipped = [], []
    for doc_id, ce_title in folder:
        if doc_id in exclude:
            continue
        prev = old.get(doc_id, {})
        title = titles.get(doc_id) or issue_title(ce_title, prev.get("title"))
        year, month = parse_date(title) if title else (None, None)
        if year is None:
            skipped.append((doc_id, ce_title))
            continue
        entry = {"id": doc_id, "title": title, "year": year, "month": month,
                 "url": DOC_URL.format(id=doc_id)}
        if doc_id in contents:
            entry.update(contents=contents[doc_id], contents_source="override")
        elif prev.get("contents") and prev.get("contents_source") != "override":
            entry.update(contents=prev["contents"],
                         contents_source=prev.get("contents_source", "ce"))
        else:
            entry.update(contents=[], contents_source=None)
        new.append(entry)
    return new, skipped


def sanity_warnings(issues):
    """Flag doc IDs of unusual length (possibly not a newsletter)."""
    warnings = []
    common_len = Counter(len(i["id"]) for i in issues).most_common(1)[0][0]
    for i in issues:
        if len(i["id"]) != common_len:
            warnings.append(f"Unusual doc ID {i['id']} for '{i['title']}'")
    return warnings


# ---- the old CE Newsletters page (bootstrap, and publish_prep.py --verify) ----

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
    """Issues linked from the CE Newsletters page, with their contents lists."""
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


def bootstrap(catalog, page_html) -> int:
    """Copy the contents lists typed on the old CE Newsletters page into the
    catalog (contents_source "ce"), except where an override is set. Issues
    the page does not list, or lists without contents, are left alone, so
    running this once the page is just the search banner changes nothing."""
    page = {i["id"]: i["contents"] for i in parse_listing(page_html)}
    changed = 0
    for c in catalog:
        listed = page.get(c["id"])
        if listed and c["contents_source"] != "override" and \
                (c["contents"] != listed or c["contents_source"] != "ce"):
            c.update(contents=listed, contents_source="ce")
            changed += 1
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="parse a saved folder listing instead of fetching")
    ap.add_argument("--bootstrap", action="store_true",
                    help="copy contents lists from the old CE Newsletters page")
    ap.add_argument("--page-html", help="with --bootstrap: a saved copy of that page")
    args = ap.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as f:
            folder_html = f.read()
    else:
        folder_html = fetch_folder()
    folder = parse_folder(folder_html)
    if not folder:
        sys.exit("No documents found in the Newsletters folder listing. "
                 "Has the Document Library changed? Catalog left unchanged.")

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.exists() else []
    new, skipped = merge(folder, catalog, load_overrides())

    old_titles = {c["id"]: c["title"] for c in catalog}
    removed = sorted(set(old_titles) - {c["id"] for c in new})
    if len(removed) > MAX_REMOVE:
        sys.exit(f"{len(removed)} catalog issues would be removed (limit {MAX_REMOVE}). "
                 "Check the folder listing; catalog left unchanged.")
    for c in new:
        if c["id"] not in old_titles:
            print(f"New issue: {c['title']} (id {c['id']})")
        elif old_titles[c["id"]] != c["title"]:
            print(f"Title changed: '{old_titles[c['id']]}' -> '{c['title']}' (id {c['id']})")
    for doc_id in removed:
        print(f"Removed: '{old_titles[doc_id]}' (id {doc_id}) is no longer in the folder")
    for doc_id, ce_title in skipped:
        print(f"WARNING: left out '{ce_title}' (id {doc_id}): no year in its title. "
              "Set a title in data/overrides.json, or exclude it there.", file=sys.stderr)
    for w in sanity_warnings(new):
        print("WARNING:", w, file=sys.stderr)

    if args.bootstrap:
        if args.page_html:
            with open(args.page_html, encoding="utf-8") as f:
                page_html = f.read()
        else:
            page_html = http_get(LISTING_URL, new_session()).text
        print(f"Bootstrap: {bootstrap(new, page_html)} contents lists copied from the CE page")

    FOLDER_PATH.write_text(json.dumps([{"id": i, "title": t} for i, t in folder],
                                      indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    CATALOG_PATH.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Catalog: {len(new)} issues from {len(folder)} folder documents")


if __name__ == "__main__":
    main()
