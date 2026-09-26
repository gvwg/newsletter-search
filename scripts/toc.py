"""Read an issue's table of contents from the PDF, whatever the layout.

Two readers, tried in order; the first result that passes the sanity checks
(at least MIN_ENTRIES entries, page numbers ascending and within the issue)
is used:

  layout  The CONTENTS box of the template used since April 2026: titles in
          one column, page numbers beside them in separate text blocks, so
          they are paired by position. Needs the PDF itself.
  text    Layout-independent: on pages 1-3, the longest run of title and
          page-number pairs in the extracted text. Handles "3 Title" (2022 to
          early 2026), "Title 3", title and number on separate lines, dot
          leaders, and author lines between entries (older issues). Works on
          the cached text in data/issues, so it can be rerun without
          downloading.

Nothing here guesses: if neither reader passes, the result is None and the
caller asks for a hand-written list (data/overrides.json).

Regression check against the hand-typed CE lists for the whole archive
(run from scripts/, no network):
    python toc.py --score
Share of CE entries found, text reader only, 2026-09-26: 0.74 overall;
0.74 to 0.98 for every year 2011-2025; weakest before 2009 and for the
April 2026 template (which the layout reader handles; --score has no PDFs). The CE lists are edited by
hand (Tech Talk topics added, recurring items often dropped), so 1.0 is not
reachable; a change to either reader should not lower these figures.
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher

from common import CATALOG_PATH, ISSUES_DIR

MIN_ENTRIES = 3

# layout reader
PAGE_NUM_RE = re.compile(r"^\d{1,3}$")

# text reader
NUM = re.compile(r"^\d{1,2}$")
LEAD = re.compile(r"^(\d{1,2})\s+(\S.*)$")                 # "3 Presidential Ramblings"
TRAIL = re.compile(r"^(\S.*?)[\s.…]*\s(\d{1,2})$")    # "Title 13", "Title . . . 4"
NOT_TRAIL = re.compile(r"\b(19|20)\d\d$|\bat$|\bst$", re.I)  # dates, addresses
HEAD = re.compile(r"^(table of )?contents:?|^inside( this issue)?:?|^in this issue:?", re.I)
NAME = re.compile(r"^([A-Z][\w'’.-]+)(\s+(and|&)?\s*[A-Z][\w'’.-]+){1,3}$")  # "Ed Pretty"
STOP = re.compile(r"special points|next meeting|gvwg\.ca|follow us", re.I)


def squash(text: str) -> str:
    """Lower-case with all whitespace removed, so letter-spaced headings
    such as 'CO N T E N TS' can be matched."""
    return re.sub(r"\s+", "", text).lower()


def read_layout(doc):
    """[(title, byline or None, page)] from the CONTENTS box, or None."""
    for page in list(doc)[:4]:
        blocks = [(b[0], b[1], b[2], b[3], b[4].strip()) for b in page.get_text("blocks")]
        heads = [b for b in blocks if squash(b[4]) == "contents"]
        if heads:
            break
    else:
        return None

    hx0, _, _, hy1, _ = heads[0]
    column = [b for b in blocks if b[0] >= hx0 - 20 and b[1] > hy1 and b[4]]
    numbers = [b for b in column if PAGE_NUM_RE.match(b[4])]
    titles = sorted((b for b in column if not PAGE_NUM_RE.match(b[4])), key=lambda b: b[1])

    entries, used = [], set()
    for x0, y0, x1, y1, text in titles:
        # The page number sits level with the first line of its title.
        near = [n for n in numbers if abs(n[1] - y0) < 6 and id(n) not in used]
        if len(near) != 1:
            return None
        used.add(id(near[0]))
        lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
        byline = None
        if len(lines) > 1 and lines[-1].lower().startswith("by "):
            byline = lines.pop()
        entries.append((" ".join(lines), byline, int(near[0][4])))
    if len(used) != len(numbers):
        return None
    return entries


def _lines(text):
    return [s for s in (" ".join(raw.split()) for raw in text.splitlines()) if s]


def _run_number_first(lines, maxpage):
    """Longest run of '3 Title' lines. An unnumbered line joins the previous
    title only if the list resumes on the next line (a wrapped title)."""
    best, cur, last = [], [], 0
    for i, s in enumerate(lines):
        m = LEAD.match(s)
        nxt = LEAD.match(lines[i + 1]) if i + 1 < len(lines) else None
        if m and last <= int(m[1]) <= maxpage:
            cur.append([m[2], int(m[1]), None])
            last = int(m[1])
        elif cur and not NUM.match(s) and not STOP.search(s) and len(s) < 60 \
                and nxt and last <= int(nxt[1]) <= maxpage:
            cur[-1][0] += " " + s
        else:
            if len(cur) > len(best):
                best = cur
            cur, last = ([[m[2], int(m[1]), None]], int(m[1])) if m and int(m[1]) <= maxpage else ([], 0)
    return max(best, cur, key=len)


def _run_number_last(lines, maxpage):
    """Longest run where title text accumulates until a page number, on the
    same line or the next. A name-like line straight after an entry is its
    author, unless a page number follows it (then it is a title)."""
    best, cur, pending, last = [], [], [], 0

    def end_run():
        nonlocal best, cur, pending, last
        if len(cur) > len(best):
            best = cur
        cur, pending, last = [], [], 0

    for i, s in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if STOP.search(s) or HEAD.match(s):
            end_run()
            continue
        n, title = None, None
        if NUM.match(s):
            n, title = int(s), " ".join(pending)
        else:
            m = TRAIL.match(s)
            if m and not NOT_TRAIL.search(s):
                n, title = int(m[2]), " ".join(pending + [m[1].rstrip(" .")])
        if n is not None:
            if title and last <= n <= maxpage and n >= 1:
                cur.append([title, n, None])
                last, pending = n, []
            else:
                end_run()
            continue
        if cur and not pending and NAME.match(s) and len(s) < 40 \
                and not NUM.match(nxt) and not TRAIL.match(nxt):
            cur[-1][2] = s
            continue
        pending.append(s)
        if len(pending) > 3:   # too much text without a number: the run is over
            keep = pending[-1:]
            end_run()
            pending = keep
    return max(best, cur, key=len)


def read_text(texts):
    """[(title, author or None, page)] from per-page text, or None."""
    best = []
    for text in texts[:3]:
        lines = _lines(text)
        for reader in (_run_number_first, _run_number_last):
            run = reader(lines, len(texts))
            if len(run) > len(best):
                best = run
    return [(t, a, p) for t, p, a in best] or None


def valid(entries, page_count) -> bool:
    if not entries or len(entries) < MIN_ENTRIES:
        return False
    pages = [p for _, _, p in entries]
    return pages == sorted(pages) and 1 <= pages[0] and pages[-1] <= page_count


def read_contents(doc, texts):
    """(entries, reader name) or (None, None). doc may be None (cached text only)."""
    page_count = len(texts)
    if doc is not None:
        entries = read_layout(doc)
        if valid(entries, page_count):
            return entries, "layout"
    entries = read_text(texts)
    if valid(entries, page_count):
        return entries, "text"
    return None, None


def as_strings(entries):
    """Catalog form: one string per entry, author appended as on the CE page."""
    out = []
    for title, author, _ in entries:
        if not author:
            out.append(title)
        elif author.lower().startswith("by "):
            out.append(f"{title} {author}")
        else:
            out.append(f"{title} - {author}")
    return out


# ---- regression score against the hand-typed CE lists ----

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("’", "'"))


def _recall(ce, got):
    """Share of CE entries matched by some extracted entry (fuzzy)."""
    g = [_norm(x) for x in got]
    hit = 0
    for c in ce:
        c0 = _norm(c.split(":")[0])   # CE Tech Talk entries append ': topics'
        if any(SequenceMatcher(None, c0, x).ratio() > 0.7
               or (len(c0) > 8 and c0 in x)
               or (len(x) > 8 and x.split(" - ")[0] in c0) for x in g):
            hit += 1
    return hit / len(ce)


def score():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    by_year = {}
    for c in catalog:
        path = ISSUES_DIR / f"{c['id']}.json"
        if c.get("contents_source", "ce") != "ce" or not c["contents"] or not path.exists():
            continue
        texts = [p["text"] for p in json.loads(path.read_text(encoding="utf-8"))["pages"]]
        entries, _ = read_contents(None, texts)
        r = _recall(c["contents"], as_strings(entries)) if entries else 0.0
        y = by_year.setdefault(c["year"], [0, 0, 0.0])
        y[0] += 1
        y[1] += entries is not None
        y[2] += r
    print("year  issues  read  share of CE entries found")
    for year, (n, found, total) in sorted(by_year.items()):
        print(f"{year}  {n:6}  {found:4}  {total / n:.2f}")
    n = sum(v[0] for v in by_year.values())
    print(f"all   {n:6}  {sum(v[1] for v in by_year.values()):4}  "
          f"{sum(v[2] for v in by_year.values()) / n:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--score", action="store_true", help="score the text reader on the archive")
    ap.add_argument("--id", help="show what the text reader finds for one cached issue")
    args = ap.parse_args()
    if args.score:
        score()
    elif args.id:
        texts = [p["text"] for p in json.loads(
            (ISSUES_DIR / f"{args.id}.json").read_text(encoding="utf-8"))["pages"]]
        entries, how = read_contents(None, texts)
        if not entries:
            sys.exit("No contents list found.")
        for s, (_, _, p) in zip(as_strings(entries), entries):
            print(f"  p{p:<3} {s}")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
