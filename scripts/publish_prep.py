"""Prepare the ClubExpress entries for a newly uploaded newsletter.

After the editor uploads an issue to the CE Documents library, this builds
everything needed to publish it, from the PDF itself:
  - the Newsletters page entry (link title, link URL, contents list),
  - the home-page News article (title, cover image, contents list).
Pasting them into CE is done by hand or by the publish-newsletter skill
(.claude/skills/publish-newsletter/SKILL.md).

The contents list is read from the CONTENTS box (page 2 in the current
InDesign template): titles in one column, page numbers beside them. The
script stops rather than guess if that box is missing or the titles and
page numbers do not pair up one to one.

Usage (from the repo root):
    .venv\\Scripts\\python scripts\\publish_prep.py --id 1819919
    .venv\\Scripts\\python scripts\\publish_prep.py --id 999 --pdf tests\\some.pdf   # offline
    .venv\\Scripts\\python scripts\\publish_prep.py --id 1819919 --verify  # after publishing
Output goes to out/publish/<id>/ (not committed).

Works with the template used since April 2026. Earlier layouts (a numbered
"N Title" list, or no CONTENTS heading) are rejected with a message.
"""

import argparse
import html
import json
import re
import sys
from collections import Counter

import pymupdf

from common import CATALOG_PATH, DOC_URL, REPO_ROOT, http_get, new_session
from harvest import parse_date

MONTHS = ("january february march april may june july august "
          "september october november december").split()
MONTH_RE = re.compile(r"(" + "|".join(MONTHS) + r")((?:19|20)\d\d)")
PAGE_NUM_RE = re.compile(r"^\d{1,3}$")
COVER_DPI = 90          # 612 pt wide page -> 765 px, the size of past CE previews
OUT_DIR = REPO_ROOT / "out" / "publish"


def squash(text: str) -> str:
    """Lower-case with all whitespace removed, so letter-spaced headings
    such as 'CO N T E N TS' or 'S E P T E M B E R 2 0 2 6' can be matched."""
    return re.sub(r"\s+", "", text).lower()


def issue_month(doc):
    """(year, month) from the running headers on pages 2 onward.

    Page 1 is not used: the template carries hidden leftover text from an
    earlier issue under the visible date (e.g. 'MAY 2026' under 'SEPTEMBER
    2026'). The most common date across the running headers wins."""
    found = Counter()
    for page in list(doc)[1:]:
        for m, y in MONTH_RE.findall(squash(page.get_text())[:400]):
            found[(int(y), MONTHS.index(m) + 1)] += 1
    return found.most_common(1)[0][0] if found else None


def read_contents(doc):
    """[(title, byline or None, page number)] in page-layout order, from the
    CONTENTS box. Exits with an explanation if the box cannot be read."""
    for page in list(doc)[:4]:
        blocks = [(b[0], b[1], b[2], b[3], b[4].strip()) for b in page.get_text("blocks")]
        heads = [b for b in blocks if squash(b[4]) == "contents"]
        if heads:
            break
    else:
        sys.exit("No CONTENTS heading found on pages 1-4. Has the template changed?")

    hx0, _, _, hy1, _ = heads[0]
    column = [b for b in blocks if b[0] >= hx0 - 20 and b[1] > hy1 and b[4]]
    numbers = [b for b in column if PAGE_NUM_RE.match(b[4])]
    titles = sorted((b for b in column if not PAGE_NUM_RE.match(b[4])), key=lambda b: b[1])

    entries, used = [], set()
    for x0, y0, x1, y1, text in titles:
        # The page number sits level with the first line of its title.
        near = [n for n in numbers if abs(n[1] - y0) < 6 and id(n) not in used]
        if len(near) != 1:
            sys.exit(f"CONTENTS box: no single page number beside '{text}'. "
                     "Check the layout before publishing by hand.")
        used.add(id(near[0]))
        lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
        byline = None
        if len(lines) > 1 and lines[-1].lower().startswith("by "):
            byline = lines.pop()
        entries.append((" ".join(lines), byline, int(near[0][4])))

    if len(used) != len(numbers):
        sys.exit(f"CONTENTS box: {len(numbers)} page numbers but {len(entries)} titles.")
    if not entries:
        sys.exit("CONTENTS box found but empty.")
    return entries


def contents_html(entries) -> str:
    """The bulleted list, in the markup used on gvwg.ca (byline in <em>)."""
    items = []
    for title, byline, _ in entries:
        li = html.escape(title, quote=False)
        if byline:
            li += f" <em>{html.escape(byline, quote=False)}</em>"
        items.append(f"  <li>{li}</li>")
    return "<ul>\n" + "\n".join(items) + "\n</ul>\n"


def news_html(doc_url: str, image_name: str, ul: str) -> str:
    """The News article body, matching the September 2026 article's layout:
    cover image (linked to the PDF) on the left, contents on the right.
    IMAGE_URL is replaced once the image has been uploaded to CE."""
    return (
        '<div class="resp-row">\n'
        ' <div class="column forty"><div class="inner-column">\n'
        f'  <a href="{doc_url}" target="_blank"><img alt="Newsletter cover" border="0" '
        f'src="IMAGE_URL" data-file="{image_name}"></a>\n'
        ' </div></div>\n'
        ' <div class="column sixty">\n'
        '  <h3 class="inner-column">Articles Include:</h3>\n'
        + ul +
        ' </div>\n'
        ' <div class="clear"></div>\n'
        '</div>\n'
    )


def verify(doc_id: str):
    """After publishing: re-read the live Newsletters page with harvest.py's
    parser and confirm the entry matches what this script prepared."""
    from common import LISTING_URL
    from harvest import parse_listing

    summary = json.loads((OUT_DIR / doc_id / "summary.json").read_text(encoding="utf-8"))
    live = {i["id"]: i for i in parse_listing(http_get(LISTING_URL, new_session()).text)}
    entry = live.get(doc_id)
    if not entry:
        sys.exit(f"FAIL: no link to docs.ashx?id={doc_id} on the Newsletters page.")
    want = [" ".join(filter(None, (c["title"], c["byline"]))) for c in summary["contents"]]
    problems = []
    if entry["title"] != summary["newsletters_page"]["link_title"]:
        problems.append(f"link title is '{entry['title']}'")
    if entry["contents"] != want:
        problems.append(f"contents differ: live {entry['contents']}")
    if problems:
        sys.exit("FAIL: " + "; ".join(problems))
    print(f"OK: '{entry['title']}' is on the Newsletters page with {len(want)} contents entries.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--id", required=True, help="CE document ID of the new issue")
    ap.add_argument("--pdf", help="use a local PDF instead of downloading (for testing)")
    ap.add_argument("--title", help="override the link title, e.g. 'September 2026 Newsletter'")
    ap.add_argument("--verify", action="store_true",
                    help="after publishing, check the live Newsletters page entry")
    args = ap.parse_args()
    if not args.id.isdigit():
        sys.exit("--id must be the number from docs.ashx?id=N")
    if args.verify:
        return verify(args.id)

    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        listed = [i for i in catalog if i["id"] == args.id]
        if listed:
            print(f"WARNING: ID {args.id} is already on the Newsletters page as "
                  f"'{listed[0]['title']}' (as of the last harvest).", file=sys.stderr)

    if args.pdf:
        pdf_bytes = open(args.pdf, "rb").read()
    else:
        pdf_bytes = http_get(DOC_URL.format(id=args.id), new_session()).content
    if not pdf_bytes.startswith(b"%PDF"):
        sys.exit(f"Document {args.id} is not a PDF. Is the ID right?")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    found = issue_month(doc)
    if args.title:
        year, month = parse_date(args.title)
        if not (year and month):
            sys.exit(f"--title '{args.title}' needs a month and year.")
        if found and found != (year, month):
            print(f"WARNING: --title month differs from the page headers "
                  f"({MONTHS[found[1] - 1].title()} {found[0]}).", file=sys.stderr)
        link_title = args.title
    elif found:
        year, month = found
        link_title = f"{MONTHS[month - 1].title()} {year} Newsletter"
    else:
        sys.exit("Could not find the issue month in the page headers; pass --title.")
    entries = read_contents(doc)
    ul = contents_html(entries)

    out = OUT_DIR / args.id
    out.mkdir(parents=True, exist_ok=True)
    image_name = f"Circular_{year}-{month:02d}_Preview.jpg"
    doc[0].get_pixmap(dpi=COVER_DPI).save(str(out / image_name), jpg_quality=85)
    doc_url = f"/docs.ashx?id={args.id}"   # site-relative, as on the Newsletters page

    (out / "contents.html").write_text(ul, encoding="utf-8")
    (out / "news-body.html").write_text(news_html(doc_url, image_name, ul), encoding="utf-8")
    summary = {
        "doc_id": args.id,
        "pdf_url": DOC_URL.format(id=args.id),
        "year": year,
        "month": month,
        "pages": doc.page_count,
        "newsletters_page": {"link_title": link_title, "link_url": doc_url,
                             "contents_html": "contents.html"},
        "news_article": {"title": f"{link_title} Available", "body_html": "news-body.html",
                         "cover_image": image_name},
        "contents": [{"title": t, "byline": b, "page": p} for t, b, p in entries],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n",
                                      encoding="utf-8")

    print(f"{link_title}: {doc.page_count} pages, {len(entries)} contents entries")
    for t, b, p in entries:
        print(f"  p{p:<3} {t}" + (f"  ({b})" if b else ""))
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
